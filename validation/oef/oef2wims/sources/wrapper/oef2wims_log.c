/* oef2wims-log.exe : enveloppe de journalisation autour de oef2wims.exe (WIMS 4.31b).
   Ne modifie pas le compilateur : le lance, relaie stdout/stderr/code retour, écrit nom.log.
   --trace : lance oef2wims-trace.exe (build instrumenté) et ajoute le résumé de trace (<nom>.trace) au journal.
   Build: x86_64-w64-mingw32-gcc -municode -O2 -static -I../common -o oef2wims-log.exe oef2wims_log.c -lbcrypt
   E2 : chemins Unicode/longs (common/corerun.inc, common/longpath.inc) */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include "longpath.inc"
#include <bcrypt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

typedef struct { char *p; size_t n, cap; } buf_t;
static int g_trace=0; /* --trace : utilise oef2wims-trace.exe et ajoute le résumé de trace */
static void bput(buf_t *b, const char *s, size_t n){ if(b->n+n+1>b->cap){ b->cap=(b->n+n+1)*2; b->p=realloc(b->p,b->cap);} memcpy(b->p+b->n,s,n); b->n+=n; b->p[b->n]=0; }
static void bprintf(buf_t *b, const char *fmt, ...){ char t[8192]; va_list a; va_start(a,fmt); int n=vsnprintf(t,sizeof t,fmt,a); va_end(a); if(n>0) bput(b,t,n<(int)sizeof t?n:(int)sizeof t-1); }
static char *u8(const wchar_t *w){ int n=WideCharToMultiByte(CP_UTF8,0,w,-1,0,0,0,0); char *s=malloc(n); WideCharToMultiByte(CP_UTF8,0,w,-1,s,n,0,0); return s; }

static int read_file(const wchar_t *path, buf_t *out){
  HANDLE h=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,0,OPEN_EXISTING,0,0);
  if(h==INVALID_HANDLE_VALUE) return 0; char t[65536]; DWORD r;
  while(ReadFile(h,t,sizeof t,&r,0)&&r) bput(out,t,r); if(!out->p) bput(out,"",0);
  CloseHandle(h); return 1; }

static void sha256(const char *d, size_t n, char hex[65]){
  BCRYPT_ALG_HANDLE a; BCRYPT_HASH_HANDLE h; unsigned char md[32]; strcpy(hex,"?");
  if(BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,0,0)) return;
  BCryptCreateHash(a,&h,0,0,0,0,0); BCryptHashData(h,(PUCHAR)d,(ULONG)n,0);
  BCryptFinishHash(h,md,32,0); BCryptDestroyHash(h); BCryptCloseAlgorithmProvider(a,0);
  for(int i=0;i<32;i++) sprintf(hex+2*i,"%02x",md[i]); }
static void sha_file(const wchar_t *p, char hex[65], long long *sz){
  buf_t b={0}; if(!read_file(p,&b)){strcpy(hex,"(illisible)"); if(sz)*sz=-1; return;}
  sha256(b.p,b.n,hex); if(sz)*sz=b.n; free(b.p); }

typedef struct { HANDLE rd; buf_t b; HANDLE out; } pump_t;
static DWORD WINAPI pump(LPVOID v){ pump_t *p=v; char t[4096]; DWORD r,w;
  while(ReadFile(p->rd,t,sizeof t,&r,0)&&r){ bput(&p->b,t,r); WriteFile(p->out,t,r,&w,0);} return 0; }

static void quote(wchar_t *cmd, const wchar_t *a){ /* règles CommandLineToArgvW */
  wcscat(cmd,L" \""); size_t L=wcslen(cmd);
  for(const wchar_t *s=a;;s++){ int bs=0; while(*s==L'\\'){bs++;s++;}
    if(!*s){ for(int i=0;i<bs*2;i++) cmd[L++]=L'\\'; break; }
    if(*s==L'"'){ for(int i=0;i<bs*2+1;i++) cmd[L++]=L'\\'; }
    else for(int i=0;i<bs;i++) cmd[L++]=L'\\';
    cmd[L++]=*s; }
  cmd[L++]=L'"'; cmd[L]=0; }

static wchar_t g_comp[MAX_PATH*2], g_self[MAX_PATH*2];
static char g_comp_sha[65], g_self_sha[65];
#include "corerun.inc"

static void now_str(char *s){ SYSTEMTIME t; GetLocalTime(&t); TIME_ZONE_INFORMATION z; GetTimeZoneInformation(&z);
  int b=-(int)z.Bias; sprintf(s,"%04d-%02d-%02d %02d:%02d:%02d.%03d (UTC%+03d:%02d)",t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond,t.wMilliseconds,b/60,abs(b%60)); }

static void context(buf_t *L, const buf_t *src, int line, int col){
  int ln=1; const char *s=src->p, *e=src->p+src->n;
  bprintf(L,"\n--- Contexte (ligne %d, colonne %d) ---\n",line,col);
  while(s<e||ln==1){ const char *q=memchr(s,'\n',e-s); if(!q) q=e; size_t n=q-s; if(n&&s[n-1]=='\r') n--;
    if(ln>=line-3&&ln<=line+3){ bprintf(L,"%s%5d | ",ln==line?">>":"  ",ln); bput(L,s,n); bput(L,"\n",1);
      if(ln==line){ bput(L,"          ",9); for(int i=1;i<col;i++){ unsigned char c= (size_t)(i-1)<n? s[i-1]:' '; bput(L,c=='\t'?"\t":" ",1);} bput(L,"^\n",2);} }
    if(q>=e) break; s=q+1; ln++; }
  if(line>ln) bprintf(L,"(ligne %d au-delà de la fin du fichier : %d lignes)\n",line,ln); }

/* compile un fichier ; renvoie code de retour ; ajoute une ligne au résumé */
static int run_one(const wchar_t *oef, const wchar_t *def, const wchar_t *logp, int raw_argc, wchar_t **raw_argv, buf_t *summary){
  wchar_t full[MAX_PATH*2], logw[MAX_PATH*2], cwd[MAX_PATH*2], defw[MAX_PATH*2];
  GetFullPathNameW(oef,MAX_PATH*2,full,0); GetCurrentDirectoryW(MAX_PATH*2,cwd);
  if(logp) wcscpy(logw,logp); else { wcscpy(logw,full); wchar_t *d=wcsrchr(logw,L'.'), *sl=wcsrchr(logw,L'\\');
    if(d&&(!sl||d>sl)) *d=0; wcscat(logw,L".log"); }
  if(def) GetFullPathNameW(def,MAX_PATH*2,defw,0); else { wcscpy(defw,full); wchar_t *d=wcsrchr(defw,L'.'), *sl=wcsrchr(defw,L'\\');
    if(d&&(!sl||d>sl)) *d=0; wcscat(defw,L".def"); }
  buf_t L={0}, src={0}; char ts[64], hex[65]; now_str(ts);
  int have=read_file(full,&src); int nl=0; for(size_t i=0;have&&i<src.n;i++) if(src.p[i]=='\n') nl++;
  if(have&&src.n&&src.p[src.n-1]!='\n') nl++;
  if(have) sha256(src.p,src.n,hex); else strcpy(hex,"(fichier introuvable/illisible)");
  /* ligne de commande */
  wchar_t *cmd=calloc(32768,sizeof(wchar_t)); cmd[0]=0; quote(cmd,g_comp); memmove(cmd,cmd+1,(wcslen(cmd))*sizeof(wchar_t));
  quote(cmd,oef); if(def) quote(cmd,def);
  bprintf(&L,"=== oef2wims-log : journal de compilation OEF ===\n");
  bprintf(&L,"Date (locale)        : %s\n",ts);
  char *a; bprintf(&L,"Enveloppe            : %s\n  sha256             : %s\n",a=u8(g_self),g_self_sha); free(a);
  bprintf(&L,"Compilateur          : %s\n  sha256             : %s\n  version            : WIMS 4.31b (oef2wims 3.22)%s\n",a=u8(g_comp),g_comp_sha,g_trace?" - build instrumenté OEF_TRACE":""); free(a);
  bprintf(&L,"Commande enveloppe   :"); for(int i=0;i<raw_argc;i++){ bprintf(&L," [%s]",a=u8(raw_argv[i])); free(a);} bput(&L,"\n",1);
  bprintf(&L,"Commande compilateur : %s\n",a=u8(cmd)); free(a);
  bprintf(&L,"Répertoire courant   : %s\n",a=u8(cwd)); free(a);
  bprintf(&L,"Fichier source       : %s\n",a=u8(full)); free(a);
  if(have) bprintf(&L,"  taille             : %llu octets\n  lignes             : %d\n  sha256             : %s\n",(unsigned long long)src.n,nl,hex);
  else bprintf(&L,"  %s\n",hex);
  wchar_t env[32768]; DWORD en=GetEnvironmentVariableW(L"oef2wims_mdef",env,32768);
  if(en&&en<32768){ bprintf(&L,"oef2wims_mdef        : %s\n",a=u8(env)); free(a);} else bprintf(&L,"oef2wims_mdef        : (non défini)\n");
  wchar_t trw[MAX_PATH*2]; wcscpy(trw,full); wcscat(trw,L".trace");
  if(g_trace){ SetEnvironmentVariableW(L"OEF2WIMS_TRACE",trw); bprintf(&L,"Trace complète       : %s\n",a=u8(trw)); free(a); }
  bprintf(&L,"Sortie .def attendue : %s\n",a=u8(defw)); free(a);
  DeleteFileW(L""); /* no-op */
  FILETIME before={0}; WIN32_FILE_ATTRIBUTE_DATA fa; int existed=GetFileAttributesExW(defw,GetFileExInfoStandard,&fa); if(existed) before=fa.ftLastWriteTime;

  DWORD rc=255; buf_t PO={0},PE={0}; double ms=0; int amode=0; wchar_t *cmd2=calloc(32768,sizeof(wchar_t));
  if(g_trace) SetEnvironmentVariableW(L"OEF2WIMS_TRACE",0);
  int ran=core_exec(g_comp,oef,def,g_trace?trw:0,1,&PO,&PE,&rc,&ms,cmd2,&amode); free(cmd2);
  if(amode) bprintf(&L,"Chemins non ANSI     : compilateur lancé en mode %s (chemin hors page de code %u ou trop long) ; sorties replacées au chemin d'origine\n",AMODE[amode],GetACP());
  if(!ran){
    bprintf(&L,"\n!!! Impossible de lancer le compilateur (erreur Windows %lu)\n",GetLastError());
    fprintf(stderr,"oef2wims-log: impossible de lancer oef2wims.exe\n");
  } else { struct { buf_t b; } po={PO}, pe={PE};
    bprintf(&L,"\nCode de retour       : %lu (%s)\n",rc,rc==0?"succès":"ERREUR");
    bprintf(&L,"Durée                : %.1f ms\n",ms);
    if(GetFileAttributesExW(defw,GetFileExInfoStandard,&fa)&&(!existed||CompareFileTime(&fa.ftLastWriteTime,&before))){
      long long sz; char dh[65]; sha_file(defw,dh,&sz); bprintf(&L,"Fichier .def produit : %s\n  taille             : %lld octets\n  sha256             : %s\n",a=u8(defw),sz,dh); free(a);
    } else bprintf(&L,"Fichier .def produit : aucun (ou non modifié)\n");
    bprintf(&L,"\n--- stdout du compilateur (%zu octets) ---\n",po.b.n); if(po.b.n) bput(&L,po.b.p,po.b.n); bprintf(&L,"\n--- fin stdout ---\n");
    bprintf(&L,"--- stderr du compilateur (%zu octets) ---\n",pe.b.n); if(pe.b.n) bput(&L,pe.b.p,pe.b.n); bprintf(&L,"\n--- fin stderr ---\n");
    char *er=po.b.p?strstr(po.b.p,"ERROR "):0;
    if(er){ char *eol=strchr(er,'\n'); size_t n=eol?(size_t)(eol-er):strlen(er);
      bprintf(&L,"\n=== DIAGNOSTIC ===\nMessage : "); bput(&L,er+6,n-6); bput(&L,"\n",1);
      char *at=strstr(er," at line "); int ln,co;
      if(at&&at<er+n&&sscanf(at," at line %d col %d",&ln,&co)==2&&have) context(&L,&src,ln,co);
      else bprintf(&L,"(pas de position ligne/colonne fournie par le compilateur)\n");
      bput(summary,"ERREUR ",7); a=u8(full); bput(summary,a,strlen(a)); free(a); bput(summary," : ",3); bput(summary,er+6,n-6); bput(summary,"\n",1);
    } else { bprintf(summary,"%-6s %s\n",rc?"ERREUR":"OK",a=u8(full)); free(a); }
    free(po.b.p); free(pe.b.p);
  }
  if(g_trace){ buf_t T={0}; bprintf(&L,"\n=== TRACE DES APPELS C (résumé de oef2wims-trace) ===\n");
    if(read_file(trw,&T)&&T.p){ char *b=strstr(T.p,"\n== RESUME ==\n"), *e=b?strstr(b,"\n== FIN ==\n"):0;
      if(b&&e){ bput(&L,b+1,(size_t)(e-b)); bprintf(&L,"\n(trace complète, appel par appel : %s)\n",a=u8(trw)); free(a);
        char *lo=strstr(b,"\nderniere_ligne_OEF: "), *lc=strstr(b,"\nderniere_ligne_C: ");
        if(lo&&lc){ char x[160],y[160]; sscanf(lo+21,"%159[^\n]",x); sscanf(lc+19,"%159[^\n]",y); bprintf(summary,"       trace : ligne OEF %s ; dernière ligne C %s\n",x,y); } }
      else bprintf(&L,"(résumé absent : le compilateur s'est arrêté avant de l'écrire)\n"); }
    else bprintf(&L,"(fichier trace introuvable)\n"); free(T.p); }
  HANDLE h=CreateFileW(logw,GENERIC_WRITE,0,0,CREATE_ALWAYS,0,0); DWORD w;
  if(h!=INVALID_HANDLE_VALUE){ WriteFile(h,"\xEF\xBB\xBF",3,&w,0); WriteFile(h,L.p,(DWORD)L.n,&w,0); CloseHandle(h);}
  else fprintf(stderr,"oef2wims-log: impossible d'écrire le journal\n");
  free(L.p); free(src.p); free(cmd); return (int)rc; }

static int is_dir(const wchar_t *p){ DWORD a=GetFileAttributesW(p); return a!=INVALID_FILE_ATTRIBUTES&&(a&FILE_ATTRIBUTE_DIRECTORY); }
static int ends(const wchar_t *s,const wchar_t *x){ size_t a=wcslen(s),b=wcslen(x); return a>=b&&!_wcsicmp(s+a-b,x); }

int wmain(int argc, wchar_t **argv){
  GetModuleFileNameW(0,g_self,MAX_PATH*2); wcscpy(g_comp,g_self); wchar_t *sl=wcsrchr(g_comp,L'\\'); if(!sl) sl=wcsrchr(g_comp,L'/');
  for(int i=1;i<argc;i++) if(!wcscmp(argv[i],L"--trace")) g_trace=1;
  wcscpy(sl?sl+1:g_comp,g_trace?L"oef2wims-trace.exe":L"oef2wims.exe"); sha_file(g_self,g_self_sha,0); sha_file(g_comp,g_comp_sha,0);
  if(g_trace&&GetFileAttributesW(g_comp)==INVALID_FILE_ATTRIBUTES){ fprintf(stderr,"oef2wims-log: --trace demandé mais oef2wims-trace.exe est absent du dossier de l'enveloppe\n"); return 2; }
  wchar_t *logp=0, **in=calloc(argc,sizeof*in); int nin=0;
  for(int i=1;i<argc;i++){ if(!wcscmp(argv[i],L"--log")&&i+1<argc) logp=argv[++i];
    else if(!wcscmp(argv[i],L"--trace")) ;
    else if(!wcscmp(argv[i],L"-h")||!wcscmp(argv[i],L"--help")){ printf("Usage: oef2wims-log.exe fichier.oef [sortie.def] [--log chemin.log] [--trace]\n       oef2wims-log.exe a.oef b.oef ... | dossier  [--log oef2wims-batch.log] [--trace]\n  --trace : utilise oef2wims-trace.exe ; écrit <fichier>.oef.trace (tous les appels C) et ajoute son résumé au .log\n"); return 0; }
    else in[nin++]=argv[i]; }
  if(nin==0){ fprintf(stderr,"Usage: oef2wims-log.exe fichier.oef [sortie.def] [--log chemin.log]\n"); return 2; }
  buf_t S={0};
  /* mode simple : 1 fichier, ou fichier + .def */
  if(!is_dir(in[0])&&(nin==1||(nin==2&&!ends(in[1],L".oef")&&!is_dir(in[1])))){
    return run_one(in[0],nin==2?in[1]:0,logp,argc,argv,&S); }
  /* mode lot */
  wchar_t **files=0; int nf=0, cap=0;
  for(int i=0;i<nin;i++){ if(is_dir(in[i])){ wchar_t pat[MAX_PATH*2]; swprintf(pat,MAX_PATH*2,L"%ls\\*.oef",in[i]); WIN32_FIND_DATAW fd; HANDLE h=FindFirstFileW(pat,&fd);
      if(h!=INVALID_HANDLE_VALUE){ do{ if(nf==cap) files=realloc(files,(cap=cap*2+16)*sizeof*files);
        files[nf]=malloc(MAX_PATH*2*sizeof(wchar_t)); swprintf(files[nf++],MAX_PATH*2,L"%ls\\%ls",in[i],fd.cFileName);}while(FindNextFileW(h,&fd)); FindClose(h);} }
    else { if(nf==cap) files=realloc(files,(cap=cap*2+16)*sizeof*files); files[nf++]=in[i]; } }
  char ts[64]; now_str(ts); int nok=0, nerr=0, worst=0; buf_t R={0};
  for(int i=0;i<nf;i++){ int rc=run_one(files[i],0,0,argc,argv,&R); if(rc) nerr++; else nok++; if(rc>worst) worst=rc; }
  char *a; bprintf(&S,"=== oef2wims-log : résumé du lot ===\nDate (locale) : %s\nCompilateur   : %s (sha256 %s, WIMS 4.31b)\n",ts,a=u8(g_comp),g_comp_sha); free(a);
  bprintf(&S,"Fichiers      : %d   OK : %d   ERREURS : %d\n(détail de chaque fichier dans nom.log à côté de chaque .oef)\n\n",nf,nok,nerr); if(R.n) bput(&S,R.p,R.n);
  wchar_t sp[MAX_PATH*2]; if(logp) wcscpy(sp,logp); else if(is_dir(in[0])) swprintf(sp,MAX_PATH*2,L"%ls\\oef2wims-batch.log",in[0]); else wcscpy(sp,L"oef2wims-batch.log");
  HANDLE h=CreateFileW(sp,GENERIC_WRITE,0,0,CREATE_ALWAYS,0,0); DWORD w; if(h!=INVALID_HANDLE_VALUE){ WriteFile(h,"\xEF\xBB\xBF",3,&w,0); WriteFile(h,S.p,(DWORD)S.n,&w,0); CloseHandle(h);}
  { buf_t M={0}; bprintf(&M,"oef2wims-log: %d fichier(s), %d OK, %d erreur(s) -> %s\n",nf,nok,nerr,a=u8(sp)); free(a); out_utf8(GetStdHandle(STD_ERROR_HANDLE),&M); free(M.p); }
  return worst; }
