/* oef2wims-v2.exe : assistant de correction OEF autour de oef2wims.exe (WIMS 4.31b).
   Ne modifie pas le compilateur. Lance oef2wims.exe (ou oef2wims-trace.exe avec --trace),
   relaie stdout/stderr/code retour, puis écrit nom.log avec en tête une section « À CORRIGER ».
   Build : x86_64-w64-mingw32-gcc -municode -O2 -static -I../common -o oef2wims-v2.exe oef2wims_v2.c -lbcrypt
   E2 : chemins Unicode/longs (common/corerun.inc, common/longpath.inc) */
#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
#include "longpath.inc"
#include <bcrypt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <stdarg.h>
#include <ctype.h>
#include "helpers.inc"
#include "msgs.inc"
#include "corerun.inc"

static int g_trace=0, g_json=0, g_diff=0, g_quiet=0;
static wchar_t *g_validator=0, *g_python=L"python";
static wchar_t g_tcomp[MAX_PATH*2];


/* écriture console : UTF-16 si console (accents corrects dans PowerShell/cmd), UTF-8 sinon */
static void econs(const char *u,size_t n){ HANDLE h=GetStdHandle(STD_ERROR_HANDLE); DWORD md,w;
  if(GetConsoleMode(h,&md)){ int k=MultiByteToWideChar(CP_UTF8,0,u,(int)n,0,0); wchar_t *t=malloc((k+1)*sizeof(wchar_t)); MultiByteToWideChar(CP_UTF8,0,u,(int)n,t,k); WriteConsoleW(h,t,k,&w,0); free(t); }
  else WriteFile(h,u,(DWORD)n,&w,0); }
static void ewprint(const wchar_t *fmt,...){ wchar_t t[4096]; va_list a; va_start(a,fmt); vswprintf(t,4096,fmt,a); va_end(a); char *u=u8(t); econs(u,strlen(u)); free(u); }
static char *xs(const char *fmt,...){ va_list a; va_start(a,fmt); int n=vsnprintf(0,0,fmt,a); va_end(a); char *s=malloc(n+1); va_start(a,fmt); vsnprintf(s,n+1,fmt,a); va_end(a); return s; }
static char *xd(const char *s){ return s?strdup(s):0; }

/* ---------- modèle du source ---------- */
typedef struct { const unsigned char *p; int n; int *ls; int nl; int utf8ok; } src_t;
static int utf8_bad(const unsigned char *p,int n){ for(int i=0;i<n;){ unsigned c=p[i]; int k= c<0x80?0: (c>>5)==6?1: (c>>4)==14?2: (c>>3)==30?3:-1;
  if(k<0||i+k>=n) return i; for(int j=1;j<=k;j++) if((p[i+j]&0xC0)!=0x80) return i; i+=k+1; } return -1; }
static void src_init(src_t *s,const char *p,int n){ s->p=(const unsigned char*)p; s->n=n; s->ls=malloc(sizeof(int)*(n+2)); s->nl=0; s->ls[s->nl++]=0;
  for(int i=0;i<n;i++) if(p[i]=='\n') s->ls[s->nl++]=i+1; s->utf8ok=utf8_bad(s->p,n)<0; }
static void off2lc(const src_t *s,int off,int *l,int *c){ int lo=0,hi=s->nl-1,b=0; while(lo<=hi){int m=(lo+hi)/2; if(s->ls[m]<=off){b=m;lo=m+1;} else hi=m-1;} *l=b+1; *c=off-s->ls[b]+1; }
static int lineend(const src_t *s,int l){ int e= l<s->nl? s->ls[l]-1 : s->n; if(e>s->ls[l-1]&&s->p[e-1]=='\r') e--; return e; }
static void put_disp(buf_t *L,const unsigned char *p,int n,int utf8ok){ for(int i=0;i<n;i++){ unsigned char c=p[i]; if(c=='\t'||c=='\r'||c<32){ bput(L," ",1); continue; }
  if(c<0x80||utf8ok) bput(L,(const char*)&c,1); else { char t[2]={(char)(0xC0|(c>>6)),(char)(0x80|(c&0x3F))}; bput(L,t,2);} } }
static int dispcol(const src_t *s,int l,int col){ int st=s->ls[l-1],k=0; for(int i=0;i<col-1&&st+i<s->n;i++){ unsigned c=s->p[st+i]; if(!s->utf8ok||(c&0xC0)!=0x80) k++; } return k; }
static void excerpt(buf_t *L,const src_t *s,int line,int col,const char *ind){
  if(line<1||line>s->nl) return;
  for(int l=line-1;l<=line+1;l++){ if(l<1||l>s->nl) continue; int st=s->ls[l-1],e=lineend(s,l); if(l==s->nl&&st>=s->n&&l!=line) continue;
    int bom= l==1&&s->n>=3&&s->p[0]==0xEF&&s->p[1]==0xBB&&s->p[2]==0xBF ? 3:0; st+=bom;
    bprintf(L,"%s%s%5d | ",ind,l==line?">>":"  ",l); int n=e-st; if(n>160) n=160; put_disp(L,s->p+st,n,s->utf8ok); bput(L,"\n",1);
    if(l==line&&col>0){ bprintf(L,"%s          ",ind); for(int i=0,k=dispcol(s,l,col)-(l==1&&s->n>=3&&s->p[0]==0xEF&&s->p[1]==0xBB&&s->p[2]==0xBF&&col>3?(s->utf8ok?1:3):0);i<k;i++) bput(L," ",1); bput(L,"^\n",2);} } }

/* ---------- problèmes ---------- */
enum { INFO=0, AVERT=1, ERR=2 };
typedef struct { int sev; const char *orig; char code[24]; int line,col,line2,col2; char *msg,*expl,*fix,*av,*ap; } issue_t;
typedef struct { issue_t *v; int n,cap; } issues_t;
static issue_t *add(issues_t *I,int sev,const char *orig,const char *code,int line,int col,char *msg,const char *expl,const char *fix,const char *av,const char *ap){
  if(I->n==I->cap) I->v=realloc(I->v,(I->cap=I->cap*2+16)*sizeof*I->v); issue_t *x=&I->v[I->n++]; memset(x,0,sizeof*x);
  x->sev=sev; x->orig=orig; snprintf(x->code,sizeof x->code,"%s",code); x->line=line; x->col=col; x->msg=msg; x->expl=xd(expl); x->fix=xd(fix); x->av=xd(av); x->ap=xd(ap); return x; }
static const emsg_t *emsg(const char *code){ for(int i=0;i<NEMSG;i++) if(!strcmp(EMSG[i].code,code)) return &EMSG[i]; return 0; }

/* ---------- analyse des directives (même logique de balayage que process() du compilateur) ---------- */
typedef struct { int idx; char name[48]; int off; int np; int po[5],pl[5]; } dir_t;
typedef struct { dir_t *v; int n,cap; } dirs_t;
static int dir_lookup(const char *n){ for(int i=0;i<NDIRS;i++) if(!strcmp(DIRS[i],n)) return i; return -1; }
static int skipws(const src_t *s,int i){ while(i<s->n&&(s->p[i]==' '||s->p[i]=='\t'||s->p[i]=='\n'||s->p[i]=='\r')) i++; return i; }
static int match_brace(const src_t *s,int i){ int d=0; for(;i<s->n;i++){ if(s->p[i]=='{') d++; else if(s->p[i]=='}'){ if(--d==0) return i; } } return -1; }
static void parse_dirs(const src_t *s,dirs_t *D){
  int enter[4096], ne=0;
  for(int p=0;p<s->n;){
    unsigned char c=s->p[p];
    if(c=='{'){ int k; for(k=0;k<ne&&enter[k]!=p;k++); if(k<ne){p++;continue;} int q=match_brace(s,p); if(q<0) return; p=q+1; continue; }
    if(c!='\\'){ p++; continue; }
    int e=p+1; while(e<s->n&&(isalnum(s->p[e])||s->p[e]=='_')) e++;
    int w=skipws(s,e); if(w>=s->n||s->p[w]!='{'){ p= w>p+1? w : p+1; continue; }
    if(D->n==D->cap) D->v=realloc(D->v,(D->cap=D->cap*2+32)*sizeof*D->v); dir_t *d=&D->v[D->n++]; memset(d,0,sizeof*d);
    int nl=e-p-1; if(nl>47) nl=47; memcpy(d->name,s->p+p+1,nl); d->name[nl]=0; d->off=p; d->idx=dir_lookup(d->name);
    int pc= d->idx<0?1:DIRPC[d->idx]; if(pc>5) pc=5; int pp=w,q=-1;
    for(int j=0;j<pc;j++){ if(j>0&&(pp>=s->n||s->p[pp]!='{')) break; q=match_brace(s,pp); if(q<0) return; d->po[j]=pp+1; d->pl[j]=q-pp-1; d->np=j+1; pp=skipws(s,q+1); }
    if(pc==0){ d->np=0; p=w; continue; } /* else/endif/... : rare sous cette forme */
    p=q+1;
    if(d->idx>=0&&pc==1&&(!strcmp(d->name,"if")||!strcmp(d->name,"ifval")||!strcmp(d->name,"for")||!strcmp(d->name,"while"))){
      int b=skipws(s,q+1); if(b<s->n&&s->p[b]=='{'){ int be=match_brace(s,b); if(ne<4096) enter[ne++]=b;
        if(be>0&&d->name[0]=='i'){ int b2=skipws(s,be+1); if(b2<s->n&&s->p[b2]=='{'&&ne<4096) enter[ne++]=b2; } } }
  }
}
static int lev(const char *a,const char *b){ int n=strlen(a),m=strlen(b); if(n>40||m>40) return 99; int d[41][41];
  for(int i=0;i<=n;i++) d[i][0]=i; for(int j=0;j<=m;j++) d[0][j]=j;
  for(int i=1;i<=n;i++) for(int j=1;j<=m;j++){ int c=tolower((unsigned char)a[i-1])!=tolower((unsigned char)b[j-1]); int x=d[i-1][j]+1,y=d[i][j-1]+1,z=d[i-1][j-1]+c; d[i][j]=x<y?(x<z?x:z):(y<z?y:z);} return d[n][m]; }
static const char *nearest(const char *n,int *dist){ int bd=99; const char *b=0; for(int i=0;i<NDIRS;i++){ int x=lev(n,DIRS[i]); if(x<bd){bd=x;b=DIRS[i];} } *dist=bd; return b; }

/* ---------- variables ---------- */
static int is_vardef(const char *n){ static const char *T[]={"complex","function","int","integer","matrix","parameter","rational","real","text","variable","mdef","for",0}; for(int i=0;T[i];i++) if(!strcmp(T[i],n)) return 1; return 0; }
static int builtin_var(const char *n){ static const char *P[]={"reply","choice","sc_reply","step","stepcnt","imagedir","confparm","help_subject","oef_","m_","special","answer","nextstep",0};
  for(int i=0;P[i];i++) if(!strncmp(n,P[i],strlen(P[i]))) return 1; return 0; }
typedef struct { char (*v)[48]; int n,cap; } names_t;
static int has_name(names_t *N,const char *n){ for(int i=0;i<N->n;i++) if(!strcmp(N->v[i],n)) return 1; return 0; }
static void add_name(names_t *N,const char *n){ if(!*n||has_name(N,n)) return; if(N->n==N->cap) N->v=realloc(N->v,(N->cap=N->cap*2+32)*48); snprintf(N->v[N->n++],48,"%s",n); }
static void var_name(const src_t *s,const dir_t *d,char *out){ int i=d->po[0],e=i+d->pl[0]; while(i<e&&isspace(s->p[i])) i++; int k=0; while(i<e&&(isalnum(s->p[i])||s->p[i]=='_')&&k<47) out[k++]=s->p[i++]; out[k]=0; }

/* ---------- pré-contrôles ---------- */
static int next_dir_line(const src_t *s,int fromline){ for(int l=fromline+1;l<=s->nl;l++){ int st=s->ls[l-1]; if(st<s->n&&s->p[st]=='\\'){ char n[48]; int k=0,i=st+1; while(i<s->n&&(isalnum(s->p[i])||s->p[i]=='_')&&k<47) n[k++]=s->p[i++]; n[k]=0; int w=skipws(s,i); if(dir_lookup(n)>=0&&w<s->n&&s->p[w]=='{') return l; } } return 0; }
static void prechecks(const src_t *s,dirs_t *D,issues_t *I){
  int l,c;
  if(s->n>=199999) add(I,ERR,"pré-contrôle","TOOLONG",1,1,xs("Fichier de %d octets (maximum 199 998).",s->n),0,0,0,0);
  if(s->n>=3&&s->p[0]==0xEF&&s->p[1]==0xBB&&s->p[2]==0xBF) add(I,AVERT,"pré-contrôle","BOM",1,1,xs("Le fichier commence par une marque BOM UTF-8 (3 octets invisibles)."),
    "Ces octets sont copiés tels quels dans la sortie ; certains serveurs WIMS les affichent comme des caractères parasites.","Réenregistrez le fichier en « UTF-8 » (sans BOM), par ex. dans Notepad++ : Encodage > UTF-8.",0,0);
  int ncr=0; for(int i=0;i<s->n;i++) if(s->p[i]=='\r') ncr++;
  if(ncr) add(I,INFO,"pré-contrôle","CRLF",0,0,xs("Fins de ligne Windows (CRLF) : %d lignes.",ncr),"Accepté : le compilateur remplace CR par un espace. Pour un dépôt sur un serveur WIMS, préférez LF.","Facultatif : convertir en LF (Notepad++ : Édition > Convertir les sauts de ligne > Unix).",0,0);
  int bad=utf8_bad(s->p,s->n); if(bad>=0){ off2lc(s,bad,&l,&c); add(I,AVERT,"pré-contrôle","ENCODAGE",l,c,xs("Octet 0x%02X non UTF-8 : le fichier semble être en Latin-1/Windows-1252.",s->p[bad]),
    "Les accents seront mal affichés si le module WIMS est en UTF-8 (cas général depuis WIMS 4).","Réenregistrez le fichier en UTF-8 (Notepad++ : Encodage > Convertir en UTF-8).",0,0); }
  for(int i=0;i<s->n;i++) if(s->p[i]<=6&&s->p[i]!='\n'){ off2lc(s,i,&l,&c); add(I,AVERT,"pré-contrôle","CTRL",l,c,xs("Caractère de contrôle 0x%02X (invisible).",s->p[i]),"Le compilateur le remplace par un espace.","Supprimez ce caractère (souvent issu d'un copier-coller).",0,0); break; }
  /* parenthèses / crochets / accolades : même règle que checkparentheses (tout le fichier, sans échappement) */
  { int *st=malloc(sizeof(int)*(s->n+1)), sp=0, rep=0;
    for(int i=0;i<s->n&&rep<5;i++){ unsigned char ch=s->p[i];
      if(ch=='('||ch=='['||ch=='{') st[sp++]=i;
      else if(ch==')'||ch==']'||ch=='}'){ char want= ch==')'?'(':ch==']'?'[':'{';
        if(sp&&s->p[st[sp-1]]==want){ sp--; continue; }
        off2lc(s,i,&l,&c);
        int has=0; for(int k=0;k<sp;k++) if(s->p[st[k]]==want) has=1;
        if(!has){ add(I,ERR,"pré-contrôle","PAREN",l,c,xs("'%c' fermant en trop (aucun '%c' ouvert avant).",ch,want),0,xs("Supprimez ce '%c' ou ajoutez le '%c' manquant plus haut. Dans un texte, écrivez &#%d; à la place.",ch,want,ch==')'?41:ch==']'?93:125),0,0); rep++; }
        else { while(sp&&s->p[st[sp-1]]!=want&&rep<5){ int o=st[sp-1],l2,c2; off2lc(s,o,&l2,&c2); char cl= s->p[o]=='('?')':s->p[o]=='['?']':'}';
            issue_t *x=add(I,ERR,"pré-contrôle","PAREN",l2,c2,xs("'%c' ouvert ligne %d col %d n'est pas fermé : on rencontre '%c' ligne %d col %d avant son '%c'.",s->p[o],l2,c2,ch,l,c,cl),0,
              xs("Ajoutez le '%c' manquant avant la ligne %d col %d (ou supprimez ce '%c' s'il est en trop). Dans un texte, écrivez &#%d; à la place du '%c'.",cl,l,c,s->p[o],s->p[o]=='('?40:s->p[o]=='['?91:123,s->p[o]),0,0); x->line2=l; x->col2=c; rep++; sp--; }
          if(sp) sp--; }
      } }
    for(int k=0;k<sp&&rep<5;k++){ int o=st[k]; off2lc(s,o,&l,&c); char cl= s->p[o]=='('?')':s->p[o]=='['?']':'}'; int nx=next_dir_line(s,l);
      issue_t *x=add(I,ERR,"pré-contrôle","PAREN",l,c,xs("'%c' ouvert ici n'est jamais fermé.",s->p[o]),0,
        nx? xs("Ajoutez '%c' à la fin de la directive commencée ici, très probablement avant la ligne %d (début de la directive suivante).",cl,nx)
          : xs("Ajoutez '%c' à l'endroit voulu (avant la fin du fichier).",cl),0,0); if(nx){x->line2=nx;x->col2=1;} rep++; }
    free(st); }
  /* directives (si les accolades sont déséquilibrées, la structure n'est pas fiable : on s'arrête là) */
  for(int i=0;i<I->n;i++) if(!strcmp(I->v[i].code,"PAREN")) return;
  int nst=0,nsteps=0,ntitle=0; int fst=-1,fsteps=-1; names_t V={0};
  for(int i=0;i<D->n;i++){ dir_t *d=&D->v[i]; off2lc(s,d->off,&l,&c);
    if(d->idx<0){ int dist; const char *nb=nearest(d->name,&dist); int ci=!_stricmp(nb,d->name);
      int st0=s->ls[l-1]; int cmt= s->p[st0]==':'||s->p[st0]=='%';
      add(I,cmt?INFO:AVERT,"pré-contrôle","DIRINC",l,c,xs("Directive inconnue \\%s : le compilateur l'ignore SANS message, son contenu est perdu.",d->name),
        "Seules les directives de la table de oef2wims sont reconnues (title, statement, answer, choice, real, text, ...). Les majuscules comptent.",
        dist<=2? xs("Vouliez-vous écrire \\%s ?%s",nb,ci?" (attention aux majuscules)":"") : xs("Vérifiez le nom ; si c'est une macro, utilisez \\mdef ou la variable d'environnement oef2wims_mdef."),0,0); continue; }
    const char *n=d->name;
    if(!strcmp(n,"statement")){ nst++; if(fst<0) fst=i; else { int l1,c1; off2lc(s,D->v[fst].off,&l1,&c1); issue_t *x=add(I,ERR,"pré-contrôle","STMT2",l,c,xs("Second \\statement ligne %d (le premier est ligne %d).",l,l1),0,0,0,0); x->line2=l1; x->col2=c1; } }
    if(!strcmp(n,"steps")||!strcmp(n,"nextstep")){ nsteps++; if(fsteps<0) fsteps=i; else { int l1,c1; off2lc(s,D->v[fsteps].off,&l1,&c1); issue_t *x=add(I,ERR,"pré-contrôle","STEPS2",l,c,xs("Second \\%s ligne %d (déjà un \\%s ligne %d).",n,l,D->v[fsteps].name,l1),0,0,0,0); x->line2=l1; x->col2=c1; } }
    if(!strncmp(n,"title",5)) ntitle++;
    if(is_vardef(n)){ char v[48]; var_name(s,d,v); add_name(&V,v); }
    if((!strcmp(n,"answer")||!strcmp(n,"reply"))&&d->np>=1){ int a=d->po[0],e=a+d->pl[0]; while(a<e&&isspace(s->p[a])) a++; while(e>a&&isspace(s->p[e-1])) e--;
      int len=0,sp=0; for(int k=a;k<e;k++){ if(isspace(s->p[k])){ if(!sp) len++; sp=1; } else { len++; sp=0; } }
      int hasv=memchr(s->p+a,'\\',e-a)!=0;
      if(len>=40){ int l2,c2; off2lc(s,a,&l2,&c2); add(I,hasv?AVERT:ERR,"pré-contrôle","PROMPT",l2,c2,xs("Libellé de \\%s de %d caractères (maximum 39)%s.",n,len,hasv?" avant remplacement des variables":""),0,0,0,0); } }
  }
  /* une \answer dont la bonne réponse est seulement \v (avec \condition dans le fichier) est une réponse libre :
     \v reçoit la réponse de l'élève, ce n'est pas une variable non définie */
  { int hascond=0; for(int i=0;i<D->n;i++) if(!strncmp(D->v[i].name,"condition",9)) hascond=1;
    if(hascond) for(int i=0;i<D->n;i++){ dir_t *d=&D->v[i]; if((strcmp(d->name,"answer")&&strcmp(d->name,"reply"))||d->np<2) continue;
      int a=d->po[1],e=a+d->pl[1]; while(a<e&&isspace(s->p[a])) a++; if(a>=e||s->p[a]!='\\') continue; char v[48]; int q=a+1,m=0;
      while(q<e&&(isalnum(s->p[q])||s->p[q]=='_')&&m<47) v[m++]=s->p[q++]; v[m]=0; while(q<e&&isspace(s->p[q])) q++; if(m&&(q>=e||s->p[q]==';')) add_name(&V,v); } }
  /* variables utilisées dans les réponses */
  for(int i=0;i<D->n;i++){ dir_t *d=&D->v[i]; if(d->idx<0) continue; int j0,j1;
    if(!strcmp(d->name,"answer")||!strcmp(d->name,"reply")){ j0=1;j1=1; } else if(!strcmp(d->name,"choice")){ j0=1;j1=2; } else if(!strcmp(d->name,"condition")){ j0=1;j1=1; } else continue;
    for(int j=j0;j<=j1&&j<d->np;j++){ int a=d->po[j],e=a+d->pl[j];
      for(int k=a;k<e;k++){ if(s->p[k]=='$'||(s->p[k]=='\\'&&k+1<e&&(s->p[k+1]=='('||s->p[k+1]=='['))) break; /* zone LaTeX : on ne vérifie pas */
        if(s->p[k]!='\\') continue; char v[48]; int q=k+1,m=0; while(q<e&&(isalnum(s->p[q])||s->p[q]=='_')&&m<47) v[m++]=s->p[q++]; v[m]=0;
        if(!m||isdigit((unsigned char)v[0])||(q<e&&s->p[q]=='{')||builtin_var(v)||has_name(&V,v)||dir_lookup(v)>=0) continue;
        off2lc(s,k,&l,&c); add(I,AVERT,"pré-contrôle","VARINC",l,c,xs("Variable \\%s utilisée dans \\%s mais jamais définie (\\real, \\integer, \\text, \\function, ...).",v,d->name),
          "Une variable non définie est remplacée par une chaîne vide : la bonne réponse attendue sera vide ou fausse.",xs("Définissez-la avant \\statement, par ex. \\real{%s=...}, ou corrigez son orthographe.",v),0,0); } } }
  if(!ntitle) add(I,AVERT,"pré-contrôle","NOTITLE",1,1,xs("Pas de \\title."),"Le titre sert à identifier l'exercice dans le module WIMS.","Ajoutez \\title{Titre de l'exercice} en première ligne.",0,0);
  if(!nst) { int stmtlike=-1,dist; for(int i=0;i<D->n;i++) if(D->v[i].idx<0&&!strcmp(nearest(D->v[i].name,&dist),"statement")&&dist<=3){ stmtlike=i; break; }
    int first=-1; for(int i=0;i<D->n;i++){ const char *n=D->v[i].name; if(!strcmp(n,"answer")||!strcmp(n,"choice")||!strcmp(n,"reply")){ first=i; break; } }
    if(stmtlike>=0){ off2lc(s,D->v[stmtlike].off,&l,&c); add(I,ERR,"pré-contrôle","NOSTMT",l,c,xs("Pas de \\statement : \\%s ligne %d est probablement une faute de frappe.",D->v[stmtlike].name,l),0,xs("Renommez \\%s en \\statement.",D->v[stmtlike].name),0,0);
      for(int k=0;k<I->n;k++) if(!strcmp(I->v[k].code,"DIRINC")&&I->v[k].line==l&&I->v[k].col==c) I->v[k].sev=-1; }
    else if(first>=0){ off2lc(s,D->v[first].off,&l,&c); add(I,ERR,"pré-contrôle","NOSTMT",l,c,xs("Pas de \\statement ; la première réponse (\\%s) est ligne %d.",D->v[first].name,l),0,xs("Insérez \\statement{...} juste avant la ligne %d.",l),0,0); }
    else add(I,ERR,"pré-contrôle","NOSTMT",s->nl,1,xs("Pas de \\statement dans le fichier."),0,xs("Ajoutez \\statement{...} après les définitions de variables (fin de fichier, ligne %d).",s->nl),0,0); }
  free(V.v);
}

/* ---------- exécution d'un processus ---------- */
static void write_file(const wchar_t *p,const buf_t *b,int bom){ HANDLE h=CreateFileW(p,GENERIC_WRITE,0,0,CREATE_ALWAYS,0,0); DWORD w;
  if(h==INVALID_HANDLE_VALUE){ ewprint(L"oef2wims-v2: impossible d'écrire %ls\n",p); return; } if(bom) WriteFile(h,"\xEF\xBB\xBF",3,&w,0); if(b->n) WriteFile(h,b->p,(DWORD)b->n,&w,0); CloseHandle(h); }
static void swap_ext(wchar_t *dst,const wchar_t *src,const wchar_t *ext){ wcscpy(dst,src); wchar_t *d=wcsrchr(dst,L'.'),*sl=wcsrchr(dst,L'\\'); if(d&&(!sl||d>sl)) *d=0; wcscat(dst,ext); }

/* ---------- JSON / HTML ---------- */
static void jstr(buf_t *b,const char *s){ bput(b,"\"",1); for(;s&&*s;s++){ unsigned char c=*s; if(c=='"'||c=='\\'){ bput(b,"\\",1); bput(b,(char*)&c,1);} else if(c=='\n') bput(b,"\\n",2); else if(c=='\t') bput(b,"\\t",2); else if(c<32) bprintf(b,"\\u%04x",c); else bput(b,(char*)&c,1);} bput(b,"\"",1); }
static void hesc(buf_t *b,const char *s,size_t n){ for(size_t i=0;i<n&&s[i];i++){ char c=s[i]; if(c=='<') bput(b,"&lt;",4); else if(c=='>') bput(b,"&gt;",4); else if(c=='&') bput(b,"&amp;",5); else if(c=='"') bput(b,"&quot;",6); else bput(b,&c,1);} }

/* ---------- résultat d'un fichier ---------- */
typedef struct { wchar_t oef[MAX_PATH*2], log[MAX_PATH*2], json[MAX_PATH*2]; DWORD rc; int nerr,nwarn,ninfo; char verdict[48]; char *first; char *acorriger; } res_t;
static const char *SEV[]={"INFO","AVERTISSEMENT","ERREUR"};

static void parse_trace_loc(const wchar_t *tr,int *l,int *c,char *dir,size_t dn){ buf_t T={0}; *l=*c=0; dir[0]=0; if(!read_file(tr,&T)||!T.p) return;
  char *a=strstr(T.p,"\nderniere_ligne_OEF: "); if(a) sscanf(a+21,"%d col %d",l,c); a=strstr(T.p,"\nderniere_directive: \\"); if(a) sscanf(a+22,"%47[a-z_A-Z0-9]",dir); (void)dn; free(T.p); }

static int run_one(const wchar_t *oef,const wchar_t *def,const wchar_t *logp,res_t *R){
  wchar_t full[MAX_PATH*2],logw[MAX_PATH*2],defw[MAX_PATH*2],jsw[MAX_PATH*2],trw[MAX_PATH*2],prevw[MAX_PATH*2+8];
  GetFullPathNameW(oef,MAX_PATH*2,full,0); if(logp) wcscpy(logw,logp); else swap_ext(logw,full,L".log");
  if(def) GetFullPathNameW(def,MAX_PATH*2,defw,0); else swap_ext(defw,full,L".def"); swap_ext(jsw,logw,L".json"); wcscpy(trw,full); wcscat(trw,L".trace");
  wcscpy(R->oef,full); wcscpy(R->log,logw); wcscpy(R->json,jsw);
  buf_t S={0}; int have=read_file(full,&S); src_t s; src_init(&s,have?S.p:"",have?(int)S.n:0);
  dirs_t D={0}; issues_t I={0}; char *a;
  if(have&&S.n) { parse_dirs(&s,&D); prechecks(&s,&D,&I); }
  /* --diff : sauvegarde de l'ancien .def */
  int hadprev=0; if(g_diff){ wcscpy(prevw,defw); wcscat(prevw,L".prev"); if(GetFileAttributesW(defw)!=INVALID_FILE_ATTRIBUTES) hadprev=CopyFileW(defw,prevw,FALSE); }
  FILETIME before={0}; WIN32_FILE_ATTRIBUTE_DATA fa; int existed=GetFileAttributesExW(defw,GetFileExInfoStandard,&fa); if(existed) before=fa.ftLastWriteTime;
  /* compilation */
  wchar_t *cmd=calloc(32768,sizeof(wchar_t)); int amode=0;
  buf_t O={0},E={0}; DWORD rc=255; double ms=0; char ts[64]; now_str(ts);
  int ran=core_exec(g_trace?g_tcomp:g_comp,oef,def,g_trace?trw:0,!g_quiet,&O,&E,&rc,&ms,cmd,&amode);
  int defnew=GetFileAttributesExW(defw,GetFileExInfoStandard,&fa)&&(!existed||CompareFileTime(&fa.ftLastWriteTime,&before));
  /* erreur du compilateur */
  char cmsg[512]=""; int cl=0,cc=0; char cchar=0; issue_t *CI=0;
  if(ran&&rc){ char *er=strstr(O.p,"ERROR "); if(er){ char *eol=strchr(er,'\n'); size_t n=eol?(size_t)(eol-er-6):strlen(er+6); if(n>=sizeof cmsg) n=sizeof cmsg-1; memcpy(cmsg,er+6,n); cmsg[n]=0;
      char *at=strstr(cmsg," at line "); if(at&&sscanf(at," at line %d col %d",&cl,&cc)==2){ char *q=strstr(cmsg," '"); if(q&&q<at){ cchar=q[2]; *q=0; } else *at=0; } }
    else if(strstr(O.p,"ERROR")){ snprintf(cmsg,sizeof cmsg,"%s",E.p); char *z=cmsg+strlen(cmsg); while(z>cmsg&&isspace((unsigned char)z[-1])) *--z=0; }
    else snprintf(cmsg,sizeof cmsg,"(code de retour %lu sans message ERROR)",rc);
    const emsg_t *m=0; for(int i=0;i<NEMSG&&!m;i++) if(strstr(cmsg,EMSG[i].key)) m=&EMSG[i];
    if(m&&!strcmp(m->code,"PAREN")&&!strncmp(cmsg,"Unmatched parentheses?",22)) {} /* même famille */
    /* fusion avec le pré-contrôle de même nature */
    issue_t *P=0; if(m) for(int i=0;i<I.n;i++) if(!strcmp(I.v[i].code,m->code)&&I.v[i].sev==ERR&&(!cl||(I.v[i].line==cl&&I.v[i].col==cc)||strcmp(m->code,"PAREN"))){ P=&I.v[i]; break; }
    if(m&&!P&&!strcmp(m->code,"PAREN")&&cl) for(int i=0;i<I.n;i++) if(!strcmp(I.v[i].code,"PAREN")&&I.v[i].line2==cl&&I.v[i].col2==cc){ P=&I.v[i]; break; }
    char *detail=0; int L=cl,C=cc;
    if(cl&&cchar) detail=xs("Le compilateur signale le caractère '%c' ligne %d colonne %d.",cchar,cl,cc);
    if(P){ if(!L){ L=P->line; C=P->col; } detail= detail? xs("%s %s",detail,P->msg) : xd(P->msg); }
    if(!L&&m&&!strcmp(m->code,"EMPTY")){ L=1; C=1; }
    if(!L&&m&&!strcmp(m->code,"OUTPUT")) detail=xs("Fichier visé : %s",a=u8(defw));
    if(!L&&!(m&&(!strcmp(m->code,"EMPTY")||!strcmp(m->code,"OUTPUT")))){ /* relance instrumentée pour localiser */
      wchar_t tdef[MAX_PATH*2],ttr[MAX_PATH*2],tmp[MAX_PATH]; GetTempPathW(MAX_PATH,tmp); swprintf(tdef,MAX_PATH*2,L"%lsoef2wims-v2-%lu.def",tmp,GetCurrentProcessId()); swprintf(ttr,MAX_PATH*2,L"%lsoef2wims-v2-%lu.trace",tmp,GetCurrentProcessId());
      if(GetFileAttributesW(g_tcomp)!=INVALID_FILE_ATTRIBUTES){ wchar_t *c2=calloc(32768,sizeof(wchar_t)); int m2;
        buf_t o2={0},e2={0}; DWORD r2; double ms2; core_exec(g_tcomp,full,tdef,ttr,0,&o2,&e2,&r2,&ms2,c2,&m2);
        int tl,tc; char dn[64]; parse_trace_loc(g_trace?trw:ttr,&tl,&tc,dn,sizeof dn); if(g_trace) {} 
        if(tl){ L=tl; C=tc; char *d2=xs("Position retrouvée par oef2wims-trace.exe : dernière ligne OEF traitée%s%s.",*dn?", directive \\":"",dn); detail= detail? xs("%s %s",detail,d2):d2; }
        DeleteFileW(tdef); DeleteFileW(ttr); free(c2); free(o2.p); free(e2.p); } }
    CI=add(&I,ERR,"compilateur",m?m->code:"AUTRE",L,C,xs("%s%s%s",cmsg,detail?" — ":"",detail?detail:""),m?m->expl:"Message non répertorié.",P&&P->fix?P->fix:(m?m->fix:"Relancez avec --trace et lisez la section RESUME."),m?m->avant:0,m?m->apres:0);
    if(P){ CI->line2=P->line2; CI->col2=P->col2; if(P->line2==0&&P->line&&(P->line!=L||P->col!=C)){ CI->line2=P->line; CI->col2=P->col; } P->sev=-1; }
    free(detail); }
  /* validateur Python */
  int vran=0,vrej=0; buf_t VO={0},VE={0}; DWORD vrc=0;
  if(g_validator&&have){ wchar_t *c3=calloc(32768,sizeof(wchar_t)); quote(c3,g_python); memmove(c3,c3+1,wcslen(c3)*sizeof(wchar_t)); quote(c3,g_validator); quote(c3,full);
    wchar_t pyexe[MAX_PATH*2]; if(!SearchPathW(0,g_python,wcschr(g_python,L'.')?0:L".exe",MAX_PATH*2,pyexe,0)) wcscpy(pyexe,g_python);
    SetEnvironmentVariableW(L"PYTHONIOENCODING",L"utf-8"); SetEnvironmentVariableW(L"PYTHONUTF8",L"1");
    vran=run_proc(pyexe,c3,&VO,&VE,0,&vrc,0); free(c3);
    SetEnvironmentVariableW(L"PYTHONIOENCODING",0); SetEnvironmentVariableW(L"PYTHONUTF8",0);
    if(!vran) add(&I,INFO,"validateur","VALID",0,0,xs("Validateur non lancé (python introuvable : %s).",a=u8(g_python)),0,"Installez Python 3 ou indiquez --python C:\\chemin\\python.exe.",0,0);
    else { buf_t all={0}; bput(&all,VO.p,VO.n); bput(&all,"\n",1); bput(&all,VE.p,VE.n);
      for(char *ln=all.p,*nx;ln&&*ln;ln=nx){ nx=strchr(ln,'\n'); if(nx) *nx++=0; int sev=-1; char *k=strstr(ln,": erreur: "); if(k) sev=ERR; else if((k=strstr(ln,": avertissement: "))) sev=AVERT; if(sev<0) continue;
        char *q=k; int nums[2]={0,0},ni=0; while(ni<2&&q>ln){ char *z=q; while(z>ln&&isdigit((unsigned char)z[-1])) z--; if(z==q||z==ln||z[-1]!=':') break; nums[1-ni]=atoi(z); ni++; q=z-1; }
        if(ni<2){ nums[0]=nums[1]; nums[1]=0; }
        if(sev==ERR) vrej=1; char *txt=strchr(k+2,':')+2;
        add(&I,sev==ERR?AVERT:INFO,"validateur","VALID",nums[0],nums[1],xs("[oef_validate.py] %s",txt),0,0,0,0); }
      free(all.p);
      int crej=rc!=0; if(vrej!=crej) add(&I,AVERT,"validateur","DESACCORD",0,0,xs("Désaccord : le compilateur %s le fichier, le validateur Python le %s.",crej?"REFUSE":"accepte",vrej?"refuse":"accepte"),
        "Les deux outils ne voient pas la même chose : le compilateur fait foi pour WIMS.", crej?"Corrigez d'abord l'erreur du compilateur.":"Lisez le diagnostic du validateur : c'est peut-être un faux positif, ou un problème que WIMS ne verra qu'à l'exécution.",0,0); } }
  /* --diff */
  buf_t DF={0}; int dadd=0,ddel=0;
  if(g_diff&&defnew){ buf_t A={0},B={0}; int okA=hadprev&&read_file(prevw,&A), okB=read_file(defw,&B);
    if(!okA) bprintf(&DF,"(pas de .def précédent : première compilation)\n");
    else if(okB){ char **la=0,**lb=0; int na=0,nb=0; for(char *p=A.p;p&&*p;){ char *e=strchr(p,'\n'); la=realloc(la,(na+1)*sizeof*la); la[na++]=p; if(!e) break; *e=0; p=e+1; }
      for(char *p=B.p;p&&*p;){ char *e=strchr(p,'\n'); lb=realloc(lb,(nb+1)*sizeof*lb); lb[nb++]=p; if(!e) break; *e=0; p=e+1; }
      int pre=0; while(pre<na&&pre<nb&&!strcmp(la[pre],lb[pre])) pre++; int suf=0; while(suf<na-pre&&suf<nb-pre&&!strcmp(la[na-1-suf],lb[nb-1-suf])) suf++;
      ddel=na-pre-suf; dadd=nb-pre-suf;
      if(!ddel&&!dadd) bprintf(&DF,"Aucune différence avec le .def précédent.\n");
      else { bprintf(&DF,"Zone modifiée : lignes %d à %d du nouveau .def (%d ligne(s) retirée(s), %d ajoutée(s))\n",pre+1,nb-suf,ddel,dadd);
        for(int i=pre,k=0;i<na-suf&&k<30;i++,k++) bprintf(&DF,"- %.200s\n",la[i]); for(int i=pre,k=0;i<nb-suf&&k<30;i++,k++) bprintf(&DF,"+ %.200s\n",lb[i]); }
      free(la); free(lb); }
    free(A.p); free(B.p); }
  /* ---------- tri et rédaction ---------- */
  int nerr=0,nwarn=0,ninfo=0; for(int i=0;i<I.n;i++){ if(I.v[i].sev==ERR) nerr++; else if(I.v[i].sev==AVERT) nwarn++; else if(I.v[i].sev==INFO) ninfo++; }
  int *ord=malloc(sizeof(int)*(I.n+1)),no=0; for(int sv=ERR;sv>=INFO;sv--){ for(int i=0;i<I.n;i++) if(I.v[i].sev==sv&&!strcmp(I.v[i].orig,"compilateur")) ord[no++]=i; for(int i=0;i<I.n;i++) if(I.v[i].sev==sv&&strcmp(I.v[i].orig,"compilateur")) ord[no++]=i; }
  const char *verdict= rc? "ERREUR : le compilateur refuse le fichier" : nwarn? "OK avec avertissements" : "OK";
  snprintf(R->verdict,sizeof R->verdict,"%s",rc?"ERREUR":nwarn?"OK (avertissements)":"OK");
  buf_t L={0}, AC={0};
  bprintf(&L,"=== oef2wims-v2 : %s ===\n",a=u8(full)); free(a);
  bprintf(&L,"Verdict : %s   (code de retour %lu, %d erreur(s), %d avertissement(s), %d info(s))\n\n",verdict,rc,nerr,nwarn,ninfo);
  bprintf(&AC,"=== À CORRIGER (%d point(s) ; traitez-les dans l'ordre, puis recompilez) ===\n",nerr+nwarn);
  if(!nerr&&!nwarn) bprintf(&AC,"Rien à corriger.\n");
  int num=0;
  for(int k=0;k<no;k++){ issue_t *x=&I.v[ord[k]]; if(x->sev<0) continue;
    if(x->sev==INFO&&num==nerr+nwarn) bprintf(&AC,"\n--- Pour information ---\n");
    num++; bprintf(&AC,"\n[%d] %s (%s, %s)",num,SEV[x->sev],x->orig,x->code); if(x->line) bprintf(&AC," — ligne %d, colonne %d",x->line,x->col); bput(&AC,"\n",1);
    bprintf(&AC,"    Problème    : %s\n",x->msg);
    if(x->line) excerpt(&AC,&s,x->line,x->col,"    ");
    if(x->line2&&(x->line2!=x->line)){ bprintf(&AC,"    Voir aussi ligne %d, colonne %d :\n",x->line2,x->col2); excerpt(&AC,&s,x->line2,x->col2,"    "); }
    const emsg_t *m=emsg(x->code); const char *ex=x->expl?x->expl:(m?m->expl:0), *fx=x->fix?x->fix:(m?m->fix:0);
    if(ex) bprintf(&AC,"    Explication : %s\n",ex); if(fx) bprintf(&AC,"    Correction  : %s\n",fx);
    const char *av=x->av?x->av:(m?m->avant:0), *ap=x->ap?x->ap:(m?m->apres:0);
    if(av&&*av&&x->sev==ERR){ bprintf(&AC,"    Exemple     : avant  ->  "); for(const char *p=av;*p;p++) if(*p=='\n') bput(&AC," / ",3); else bput(&AC,p,1);
      bprintf(&AC,"\n                  après  ->  "); for(const char *p=ap;*p;p++) if(*p=='\n') bput(&AC," / ",3); else bput(&AC,p,1); bput(&AC,"\n",1); }
    if(num==1&&x->sev>=AVERT){ R->first=xs("%s%s%s",x->line?"":"",x->msg,""); if(x->line){ free(R->first); R->first=xs("l.%d c.%d : %s",x->line,x->col,x->msg);} } }
  bput(&L,AC.p,AC.n);
  bprintf(&L,"\n\n=== DÉTAILS TECHNIQUES ===\nDate (locale)        : %s\n",ts);
  bprintf(&L,"Compilateur          : %s\n  sha256             : %s\n  version            : WIMS 4.31b (oef2wims 3.22)%s\n",a=u8(g_trace?g_tcomp:g_comp),g_trace?"(voir oef2wims-trace.exe)":g_comp_sha,g_trace?" - build instrumenté":""); free(a);
  bprintf(&L,"Commande             : %s\n",a=u8(cmd)); free(a);
  if(amode) bprintf(&L,"Chemins non ANSI     : compilateur lancé en mode %s (chemin hors page de code %u ou trop long) ; sorties replacées au chemin d'origine\n",AMODE[amode],GetACP());
  if(have){ char hx[65]; sha256(S.p,S.n,hx); bprintf(&L,"Source               : %zu octets, %d lignes, sha256 %s, %s\n",S.n,s.nl,hx,s.utf8ok?"UTF-8 valide":"pas en UTF-8"); }
  else bprintf(&L,"Source               : introuvable ou illisible\n");
  bprintf(&L,"Directives trouvées  : %d\n",D.n);
  bprintf(&L,"Code de retour       : %lu\nDurée                : %.1f ms\n",rc,ms);
  if(defnew){ long long sz; char dh[65]; sha_file(defw,dh,&sz); bprintf(&L,"Fichier .def produit : %s (%lld octets, sha256 %s)\n",a=u8(defw),sz,dh); free(a);} else bprintf(&L,"Fichier .def produit : aucun\n");
  bprintf(&L,"\n--- stdout du compilateur ---\n%s\n--- stderr du compilateur ---\n%s\n",O.p?O.p:"",E.p?E.p:"");
  if(g_diff){ bprintf(&L,"\n--- Différences avec le .def précédent (%s.prev) ---\n",a=u8(defw)); free(a); if(DF.n) bput(&L,DF.p,DF.n); else bprintf(&L,"(pas de nouveau .def)\n"); }
  if(g_validator) { bprintf(&L,"\n--- Validateur Python (%s) : %s, code %lu ---\n",a=u8(g_validator),!vran?"non lancé":vrej?"REFUSE":"accepte",vrc); free(a); if(VO.n) bput(&L,VO.p,VO.n); if(VE.n) bput(&L,VE.p,VE.n); }
  if(g_trace){ buf_t T={0}; bprintf(&L,"\n--- Trace des appels C (résumé) ---\n"); if(read_file(trw,&T)&&T.p){ char *b=strstr(T.p,"\n== RESUME ==\n"),*e=b?strstr(b,"\n== FIN ==\n"):0; if(b&&e) bput(&L,b+1,e-b); bprintf(&L,"\n(trace complète : %s)\n",a=u8(trw)); free(a);} free(T.p); }
  write_file(logw,&L,1);
  if(g_json){ buf_t J={0}; bprintf(&J,"{\n  \"fichier\": "); jstr(&J,a=u8(full)); free(a); bprintf(&J,",\n  \"verdict\": "); jstr(&J,R->verdict);
    bprintf(&J,",\n  \"code_retour\": %lu,\n  \"duree_ms\": %.1f,\n  \"message_compilateur\": ",rc,ms); jstr(&J,cmsg);
    bprintf(&J,",\n  \"def\": "); if(defnew){ jstr(&J,a=u8(defw)); free(a);} else bput(&J,"null",4);
    if(amode) bprintf(&J,",\n  \"chemin_ansi\": \"%s\"",amode==1?"court":"temporaire");
    bprintf(&J,",\n  \"erreurs\": %d, \"avertissements\": %d, \"infos\": %d",nerr,nwarn,ninfo);
    if(g_validator) bprintf(&J,",\n  \"validateur\": {\"lance\": %s, \"verdict\": \"%s\", \"code\": %lu}",vran?"true":"false",vrej?"refuse":"accepte",vrc);
    if(g_diff&&defnew) bprintf(&J,",\n  \"diff\": {\"lignes_retirees\": %d, \"lignes_ajoutees\": %d}",ddel,dadd);
    bprintf(&J,",\n  \"problemes\": [");
    int f=1; for(int k=0;k<no;k++){ issue_t *x=&I.v[ord[k]]; if(x->sev<0) continue; const emsg_t *m=emsg(x->code);
      bprintf(&J,"%s\n    {\"severite\": \"%s\", \"source\": ",f?"":",",SEV[x->sev]); jstr(&J,x->orig); bprintf(&J,", \"code\": \"%s\", \"ligne\": %d, \"colonne\": %d",x->code,x->line,x->col);
      if(x->line2) bprintf(&J,", \"ligne2\": %d, \"colonne2\": %d",x->line2,x->col2);
      bprintf(&J,", \"message\": "); jstr(&J,x->msg); bprintf(&J,", \"explication\": "); jstr(&J,x->expl?x->expl:m?m->expl:""); bprintf(&J,", \"correction\": "); jstr(&J,x->fix?x->fix:m?m->fix:""); bput(&J,"}",1); f=0; }
    bprintf(&J,"\n  ]\n}\n"); write_file(jsw,&J,0); free(J.p); }
  if(!g_quiet&&(nerr||nwarn)){ econs("\n",1); econs(AC.p,AC.n); ewprint(L"(journal complet : %ls)\n",logw); }
  R->rc=rc; R->nerr=nerr; R->nwarn=nwarn; R->ninfo=ninfo; R->acorriger=AC.p;
  free(L.p); free(O.p); free(E.p); free(VO.p); free(VE.p); free(DF.p); free(cmd); free(ord); free(D.v); free(S.p); free(s.ls);
  return ran?(int)rc:255; }

/* ---------- rapport HTML du lot ---------- */
static void rel_link(buf_t *H,const wchar_t *target,const wchar_t *base){ size_t bl=wcslen(base); char *a;
  if(!_wcsnicmp(target,base,bl)&&(target[bl]==L'\\')){ a=u8(target+bl+1); for(char *p=a;*p;p++) if(*p=='\\') *p='/'; hesc(H,a,strlen(a)); free(a); }
  else { a=u8(target); bput(H,"file:///",8); for(char *p=a;*p;p++) if(*p=='\\') *p='/'; hesc(H,a,strlen(a)); free(a); } }
static void html_report(const wchar_t *path,res_t *R,int n,const char *ts){
  wchar_t base[MAX_PATH*2]; GetFullPathNameW(path,MAX_PATH*2,base,0); wchar_t *sl=wcsrchr(base,L'\\'); if(sl) *sl=0;
  int ok=0,ko=0,av=0; for(int i=0;i<n;i++){ if(R[i].rc) ko++; else { ok++; if(R[i].nwarn) av++; } }
  buf_t H={0}; bprintf(&H,"<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><title>Rapport oef2wims-v2</title><style>"
    "body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222}table{border-collapse:collapse;width:100%%}td,th{border:1px solid #ccc;padding:4px 8px;vertical-align:top;font-size:14px}"
    "th{background:#f0f0f0;cursor:pointer}.ERREUR{background:#fde2e2}.OK{background:#e5f6e5}.av{background:#fff4d6}pre{background:#f7f7f7;padding:8px;overflow:auto;font-size:12px}.box{display:inline-block;padding:8px 16px;margin-right:8px;border-radius:6px;font-size:18px}</style>"
    "<script>function s(c){var t=document.getElementById('t'),r=[].slice.call(t.rows,1);var d=t.getAttribute('data-d')==c?-1:1;t.setAttribute('data-d',d==1?c:'');"
    "r.sort(function(a,b){var x=a.cells[c].getAttribute('data-v')||a.cells[c].innerText,y=b.cells[c].getAttribute('data-v')||b.cells[c].innerText;return (isNaN(x-y)?x.localeCompare(y):x-y)*d});r.forEach(function(e){t.tBodies[0].appendChild(e)})}</script></head><body>");
  bprintf(&H,"<h1>Rapport de compilation OEF</h1><p>%s — compilateur WIMS 4.31b (oef2wims%s.exe)</p>",ts,g_trace?"-trace":"");
  bprintf(&H,"<div><span class=\"box\" style=\"background:#eee\">%d fichier(s)</span><span class=\"box OK\">%d OK</span><span class=\"box av\">%d avec avertissements</span><span class=\"box ERREUR\">%d en erreur</span></div>",n,ok,av,ko);
  bprintf(&H,"<p>Cliquez sur un en-tête pour trier, sur un fichier pour voir les points à corriger.</p><table id=\"t\"><thead><tr><th onclick=\"s(0)\">Fichier</th><th onclick=\"s(1)\">Verdict</th><th onclick=\"s(2)\">Erreurs</th><th onclick=\"s(3)\">Avert.</th><th onclick=\"s(4)\">Premier point à corriger</th><th>Journaux</th></tr></thead><tbody>");
  for(int i=0;i<n;i++){ char *a=u8(R[i].oef); const char *nm=strrchr(a,'\\'); nm=nm?nm+1:a;
    bprintf(&H,"<tr class=\"%s\"><td><details><summary>",R[i].rc?"ERREUR":R[i].nwarn?"av":"OK"); hesc(&H,nm,strlen(nm)); bprintf(&H,"</summary><pre>"); if(R[i].acorriger) hesc(&H,R[i].acorriger,strlen(R[i].acorriger)); bprintf(&H,"</pre></details></td>");
    bprintf(&H,"<td>%s</td><td data-v=\"%d\">%d</td><td data-v=\"%d\">%d</td><td>",R[i].verdict,R[i].nerr,R[i].nerr,R[i].nwarn,R[i].nwarn); if(R[i].first) hesc(&H,R[i].first,strlen(R[i].first));
    bprintf(&H,"</td><td><a href=\""); rel_link(&H,R[i].log,base); bprintf(&H,"\">.log</a>"); if(g_json){ bprintf(&H," <a href=\""); rel_link(&H,R[i].json,base); bprintf(&H,"\">.json</a>"); } bprintf(&H,"</td></tr>\n"); free(a); }
  bprintf(&H,"</tbody></table></body></html>\n"); write_file(path,&H,0); free(H.p); }

static int is_dir(const wchar_t *p){ DWORD a=GetFileAttributesW(p); return a!=INVALID_FILE_ATTRIBUTES&&(a&FILE_ATTRIBUTE_DIRECTORY); }
static int ends(const wchar_t *s,const wchar_t *x){ size_t a=wcslen(s),b=wcslen(x); return a>=b&&!_wcsicmp(s+a-b,x); }
static void usage(FILE *f){ fprintf(f,
 "oef2wims-v2.exe : compile un OEF avec oef2wims.exe et explique comment le corriger.\n"
 "Usage : oef2wims-v2.exe fichier.oef [sortie.def] [options]\n"
 "        oef2wims-v2.exe a.oef b.oef ... | dossier   [options]   (lot : .log par fichier + oef2wims-rapport.html)\n"
 "        oef2wims-v2.exe --watch dossier [options]                 (recompile à chaque enregistrement ; Ctrl+C pour arrêter)\n"
 "Options : --trace            utilise oef2wims-trace.exe (trace complète des appels C, résumé dans le .log)\n"
 "          --json             écrit aussi nom.json (et oef2wims-batch.json en lot)\n"
 "          --diff             garde l'ancien .def en .def.prev et liste les différences dans le .log\n"
 "          --validator chemin\\oef_validate.py  ajoute les diagnostics du validateur Python\n"
 "          --python python.exe  interpréteur pour --validator (défaut : python)\n"
 "          --log chemin.log   (1 fichier) journal ailleurs / (lot) chemin du rapport HTML\n"
 "          --quiet            n'affiche pas la sortie du compilateur ni le résumé à l'écran\n"); }

static int batch(wchar_t **files,int nf,const wchar_t *html_path){
  res_t *R=calloc(nf,sizeof*R); int worst=0,nok=0,nerr=0; char ts[64]; now_str(ts);
  for(int i=0;i<nf;i++){ int rc=run_one(files[i],0,0,&R[i]); if(rc) nerr++; else nok++; if(rc>worst) worst=rc; }
  html_report(html_path,R,nf,ts);
  wchar_t bl[MAX_PATH*2]; wcscpy(bl,html_path); wchar_t *sl=wcsrchr(bl,L'\\'); wcscpy(sl?sl+1:bl,L"oef2wims-batch.log");
  buf_t S={0}; char *a; bprintf(&S,"=== oef2wims-v2 : résumé du lot ===\nDate (locale) : %s\nFichiers : %d   OK : %d   ERREURS : %d\n\n",ts,nf,nok,nerr);
  for(int i=0;i<nf;i++){ bprintf(&S,"%-20s %s\n",R[i].verdict,a=u8(R[i].oef)); free(a); if(R[i].first&&R[i].rc) bprintf(&S,"                     -> %s\n",R[i].first); }
  write_file(bl,&S,1); free(S.p);
  if(g_json){ buf_t J={0}; bprintf(&J,"{\n  \"date\": \"%s\", \"fichiers\": %d, \"ok\": %d, \"erreurs\": %d,\n  \"resultats\": [",ts,nf,nok,nerr);
    for(int i=0;i<nf;i++){ bprintf(&J,"%s\n    {\"fichier\": ",i?",":""); jstr(&J,a=u8(R[i].oef)); free(a); bprintf(&J,", \"verdict\": \"%s\", \"code_retour\": %lu, \"erreurs\": %d, \"avertissements\": %d, \"premier_point\": ",R[i].verdict,R[i].rc,R[i].nerr,R[i].nwarn); jstr(&J,R[i].first?R[i].first:""); bprintf(&J,", \"json\": "); jstr(&J,a=u8(R[i].json)); free(a); bput(&J,"}",1); }
    bprintf(&J,"\n  ]\n}\n"); wcscpy(sl?sl+1:bl,L"oef2wims-batch.json"); write_file(bl,&J,0); free(J.p); }
  ewprint(L"oef2wims-v2: %d fichier(s), %d OK, %d erreur(s) -> %ls\n",nf,nok,nerr,html_path);
  return worst; }

static int watch(const wchar_t *dir){
  typedef struct { wchar_t name[MAX_PATH]; FILETIME t; long long sz; } ent_t; ent_t *E=0; int ne=0,cap=0;
  ewprint(L"oef2wims-v2: surveillance de %ls (Ctrl+C pour arrêter)\n",dir);
  for(int first=1;;first=0){ wchar_t pat[MAX_PATH*2]; swprintf(pat,MAX_PATH*2,L"%ls\\*.oef",dir); WIN32_FIND_DATAW fd; HANDLE h=FindFirstFileW(pat,&fd);
    if(h!=INVALID_HANDLE_VALUE){ do{ int k; for(k=0;k<ne&&wcscmp(E[k].name,fd.cFileName);k++);
        long long sz=((long long)fd.nFileSizeHigh<<32)|fd.nFileSizeLow;
        if(k==ne){ if(ne==cap) E=realloc(E,(cap=cap*2+16)*sizeof*E); wcscpy(E[ne].name,fd.cFileName); E[ne].t=fd.ftLastWriteTime; E[ne].sz=sz; ne++; if(first) continue; }
        else if(!CompareFileTime(&E[k].t,&fd.ftLastWriteTime)&&E[k].sz==sz) continue;
        else { E[k].t=fd.ftLastWriteTime; E[k].sz=sz; }
        Sleep(300); wchar_t f[MAX_PATH*2]; swprintf(f,MAX_PATH*2,L"%ls\\%ls",dir,fd.cFileName); res_t R={0}; SYSTEMTIME t; GetLocalTime(&t);
        ewprint(L"\n[%02d:%02d:%02d] modification : %ls\n",t.wHour,t.wMinute,t.wSecond,fd.cFileName); run_one(f,0,0,&R);
        ewprint(L"[%02d:%02d:%02d] %hs (%d erreur(s), %d avertissement(s)) -> %ls\n",t.wHour,t.wMinute,t.wSecond,R.verdict,R.nerr,R.nwarn,R.log);
      }while(FindNextFileW(h,&fd)); FindClose(h); }
    Sleep(1000); } }

int wmain(int argc,wchar_t **argv){
  GetModuleFileNameW(0,g_self,MAX_PATH*2); wcscpy(g_comp,g_self); wchar_t *sl=wcsrchr(g_comp,L'\\'); if(!sl) sl=wcsrchr(g_comp,L'/');
  wcscpy(sl?sl+1:g_comp,L"oef2wims.exe"); wcscpy(g_tcomp,g_comp); sl=wcsrchr(g_tcomp,L'\\'); wcscpy(sl?sl+1:g_tcomp,L"oef2wims-trace.exe");
  wchar_t *logp=0,*wdir=0,**in=calloc(argc,sizeof*in); int nin=0;
  for(int i=1;i<argc;i++){ wchar_t *x=argv[i];
    if(!wcscmp(x,L"--trace")) g_trace=1; else if(!wcscmp(x,L"--json")) g_json=1; else if(!wcscmp(x,L"--diff")) g_diff=1; else if(!wcscmp(x,L"--quiet")) g_quiet=1;
    else if(!wcscmp(x,L"--validator")&&i+1<argc) g_validator=argv[++i]; else if(!wcscmp(x,L"--python")&&i+1<argc) g_python=argv[++i];
    else if(!wcscmp(x,L"--log")&&i+1<argc) logp=argv[++i]; else if(!wcscmp(x,L"--watch")&&i+1<argc) wdir=argv[++i];
    else if(!wcscmp(x,L"-h")||!wcscmp(x,L"--help")){ usage(stdout); return 0; } else if(x[0]==L'-'&&x[1]==L'-'){ ewprint(L"option inconnue : %ls\n",x); usage(stderr); return 2; } else in[nin++]=x; }
  if(GetFileAttributesW(g_comp)==INVALID_FILE_ATTRIBUTES){ fprintf(stderr,"oef2wims-v2: oef2wims.exe introuvable à côté de oef2wims-v2.exe\n"); return 2; }
  if(g_trace&&GetFileAttributesW(g_tcomp)==INVALID_FILE_ATTRIBUTES){ fprintf(stderr,"oef2wims-v2: --trace demandé mais oef2wims-trace.exe est absent\n"); return 2; }
  if(g_validator&&GetFileAttributesW(g_validator)==INVALID_FILE_ATTRIBUTES){ ewprint(L"oef2wims-v2: validateur introuvable : %ls\n",g_validator); return 2; }
  sha_file(g_comp,g_comp_sha,0);
  if(wdir){ if(!is_dir(wdir)){ ewprint(L"oef2wims-v2: %ls n'est pas un dossier\n",wdir); return 2; } return watch(wdir); }
  if(!nin){ usage(stderr); return 2; }
  if(!is_dir(in[0])&&(nin==1||(nin==2&&!ends(in[1],L".oef")&&!is_dir(in[1])))){ res_t R={0}; return run_one(in[0],nin==2?in[1]:0,logp,&R); }
  wchar_t **files=0; int nf=0,cap=0;
  for(int i=0;i<nin;i++){ if(is_dir(in[i])){ wchar_t pat[MAX_PATH*2]; swprintf(pat,MAX_PATH*2,L"%ls\\*.oef",in[i]); WIN32_FIND_DATAW fd; HANDLE h=FindFirstFileW(pat,&fd);
      if(h!=INVALID_HANDLE_VALUE){ do{ if(nf==cap) files=realloc(files,(cap=cap*2+16)*sizeof*files); files[nf]=malloc(MAX_PATH*2*sizeof(wchar_t)); swprintf(files[nf++],MAX_PATH*2,L"%ls\\%ls",in[i],fd.cFileName);}while(FindNextFileW(h,&fd)); FindClose(h);} }
    else { if(nf==cap) files=realloc(files,(cap=cap*2+16)*sizeof*files); files[nf++]=in[i]; } }
  wchar_t hp[MAX_PATH*2]; if(logp) wcscpy(hp,logp); else if(is_dir(in[0])) swprintf(hp,MAX_PATH*2,L"%ls\\oef2wims-rapport.html",in[0]); else wcscpy(hp,L"oef2wims-rapport.html");
  { wchar_t t[MAX_PATH*2]; GetFullPathNameW(hp,MAX_PATH*2,t,0); wcscpy(hp,t); }
  return batch(files,nf,hp); }
