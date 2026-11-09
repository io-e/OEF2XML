/* corerun.inc (E2) : lance le compilateur ANSI (oef2wims.exe / oef2wims-trace.exe) avec des chemins
   qu'il sait ouvrir. Le compilateur lit argv et appelle fopen() dans la page de code ANSI : un chemin
   avec des caractères hors de cette page (chinois, grec, emoji... sur un système cp1252) ou de plus
   de 259 caractères échoue. Sans toucher au compilateur :
     mode 0 « direct »  : tous les chemins sont représentables -> commande strictement identique à avant ;
     mode 1 « court »   : noms courts 8.3 (GetShortPathNameW) du .oef et du dossier du .def ;
     mode 2 « temporaire » : copie du .oef dans un dossier temporaire ASCII, compilation, puis
                             déplacement du .def (et de la trace) vers le chemin d'origine (MoveFileExW).
   Dans les modes 1 et 2, les chemins substitués affichés par le compilateur sur stdout sont
   remplacés par les chemins d'origine (UTF-8). Requiert : buf_t, bput, pump_t, pump, quote. */
static int ansi_ok(const wchar_t *full){
  if(!full) return 1; if(wcslen(full)>=MAX_PATH-1) return 0;
  UINT cp=GetACP(); if(cp==CP_UTF8) return 1;
  BOOL used=FALSE; int n=WideCharToMultiByte(cp,WC_NO_BEST_FIT_CHARS,full,-1,0,0,0,&used); if(!n||used) return 0;
  char *s=malloc(n); WideCharToMultiByte(cp,WC_NO_BEST_FIT_CHARS,full,-1,s,n,0,0);
  int m=MultiByteToWideChar(cp,0,s,-1,0,0); wchar_t *w=malloc(m*sizeof(wchar_t)); MultiByteToWideChar(cp,0,s,-1,w,m);
  int ok=!wcscmp(w,full); free(s); free(w); return ok; }
static char *acp(const wchar_t *w){ int n=WideCharToMultiByte(CP_ACP,0,w,-1,0,0,0,0); char *s=malloc(n); WideCharToMultiByte(CP_ACP,0,w,-1,s,n,0,0); return s; }
static void dir_of(wchar_t *d,const wchar_t *p){ wcscpy(d,p); wchar_t *s=wcsrchr(d,L'\\'); if(s){ if(s==d+2&&d[1]==L':') s[1]=0; else *s=0; } }
static const wchar_t *base_of(const wchar_t *p){ const wchar_t *s=wcsrchr(p,L'\\'); return s?s+1:p; }
static void derived_def(wchar_t *d,const wchar_t *oef){ wcscpy(d,oef); size_t n=wcslen(d); if(n>=4&&!_wcsicmp(d+n-4,L".oef")) d[n-4]=0; wcscat(d,L".def"); }

typedef struct { int mode; wchar_t tdir[MAX_PATH]; wchar_t a_oef[MAX_PATH*2],a_def[MAX_PATH*2],a_tr[MAX_PATH*2]; wchar_t r_def[MAX_PATH*2],r_tr[MAX_PATH*2]; int def_move,tr_move,def_pre; } amap_t;
static const char *AMODE[]={"direct","court (8.3)","copie temporaire"};

static int dir_usable(const wchar_t *d){ DWORD a=GetFileAttributesW(d); if(a==INVALID_FILE_ATTRIBUTES){ CreateDirectoryW(d,0); a=GetFileAttributesW(d); } return a!=INVALID_FILE_ATTRIBUTES&&(a&FILE_ATTRIBUTE_DIRECTORY); }
/* dossier de base ASCII : %TEMP%, sinon dossier de l'exe, sinon C:\ProgramData\oef2wims\tmp */
static int ascii_tmpbase(wchar_t *b){ wchar_t t[MAX_PATH*2];
  if(GetTempPathW(MAX_PATH,t)&&ansi_ok(t)&&wcslen(t)<120&&dir_usable(t)){ wcscpy(b,t); return 1; }
  dir_of(t,g_self); if(ansi_ok(t)&&wcslen(t)<120&&dir_usable(t)){ wcscpy(b,t); wcscat(b,L"\\"); return 1; }
  CreateDirectoryW(L"C:\\ProgramData\\oef2wims",0); CreateDirectoryW(L"C:\\ProgramData\\oef2wims\\tmp",0); wcscpy(b,L"C:\\ProgramData\\oef2wims\\tmp\\"); return 1; }

/* prépare amap ; full_oef/full_def/full_tr = chemins absolus d'origine (full_tr peut être NULL) */
static void amap_prepare(amap_t *M,const wchar_t *full_oef,const wchar_t *full_def,const wchar_t *full_tr){
  memset(M,0,sizeof*M); wcscpy(M->r_def,full_def); if(full_tr) wcscpy(M->r_tr,full_tr);
  if(ansi_ok(full_oef)&&ansi_ok(full_def)&&ansi_ok(full_tr)) return;
  /* mode 1 : noms courts (OEF2WIMS_FORCE_TEMP=1 : passe directement au mode 2, pour les tests) */
  if(!GetEnvironmentVariableW(L"OEF2WIMS_FORCE_TEMP",0,0)) { wchar_t so[MAX_PATH*2],dd[MAX_PATH*2],sd[MAX_PATH*2],td[MAX_PATH*2],st[MAX_PATH*2]; int ok=1;
    ok=GetShortPathNameW(full_oef,so,MAX_PATH*2)&&ansi_ok(so);
    dir_of(dd,full_def); if(ok) ok=GetShortPathNameW(dd,sd,MAX_PATH*2)&&wcslen(sd)<MAX_PATH-40;
    if(ok){ if(sd[wcslen(sd)-1]!=L'\\') wcscat(sd,L"\\");
      if(ansi_ok(base_of(full_def))&&wcslen(sd)+wcslen(base_of(full_def))<MAX_PATH-1) swprintf(M->a_def,MAX_PATH*2,L"%ls%ls",sd,base_of(full_def));
      else { swprintf(M->a_def,MAX_PATH*2,L"%ls~oef2wims-%lu.def",sd,GetCurrentProcessId()); M->def_move=1; }
      ok=ansi_ok(M->a_def); }
    if(ok&&full_tr){ dir_of(td,full_tr); ok=GetShortPathNameW(td,st,MAX_PATH*2)&&wcslen(st)<MAX_PATH-40;
      if(ok){ if(st[wcslen(st)-1]!=L'\\') wcscat(st,L"\\");
        if(ansi_ok(base_of(full_tr))&&wcslen(st)+wcslen(base_of(full_tr))<MAX_PATH-1) swprintf(M->a_tr,MAX_PATH*2,L"%ls%ls",st,base_of(full_tr));
        else { swprintf(M->a_tr,MAX_PATH*2,L"%ls~oef2wims-%lu.trace",st,GetCurrentProcessId()); M->tr_move=1; }
        ok=ansi_ok(M->a_tr); } }
    if(ok){ M->mode=1; wcscpy(M->a_oef,so);
      if(M->def_move&&GetFileAttributesW(full_def)!=INVALID_FILE_ATTRIBUTES) M->def_pre=CopyFileW(full_def,M->a_def,FALSE);
      return; }
    M->def_move=M->tr_move=0; M->a_def[0]=M->a_tr[0]=0; }
  /* mode 2 : copie temporaire ASCII */
  M->mode=2; wchar_t b[MAX_PATH*2]; ascii_tmpbase(b); static int seq=0;
  swprintf(M->tdir,MAX_PATH,L"%lsoef2wims-%lu-%d",b,GetCurrentProcessId(),seq++); CreateDirectoryW(M->tdir,0);
  /* nom ASCII proche de l'original (aide à lire stdout brut) */
  wchar_t nm[64]=L"exo"; { const wchar_t *o=base_of(full_oef); int k=0; for(;o[k]&&k<40;k++){ wchar_t c=o[k]; nm[k]=(c<128&&c>32&&c!=L'%')?c:L'_'; } nm[k]=0; size_t n=wcslen(nm); if(n>=4&&!_wcsicmp(nm+n-4,L".oef")) nm[n-4]=0; }
  swprintf(M->a_oef,MAX_PATH*2,L"%ls\\%ls.oef",M->tdir,nm);
  if(!CopyFileW(full_oef,M->a_oef,FALSE)) swprintf(M->a_oef,MAX_PATH*2,L"%ls\\absent\\%ls.oef",M->tdir,nm); /* même effet : source introuvable */
  wchar_t dd[MAX_PATH*2]; dir_of(dd,full_def);
  if(GetFileAttributesW(dd)==INVALID_FILE_ATTRIBUTES) swprintf(M->a_def,MAX_PATH*2,L"%ls\\absent\\%ls.def",M->tdir,nm); /* dossier inexistant : même erreur */
  else { swprintf(M->a_def,MAX_PATH*2,L"%ls\\%ls.def",M->tdir,nm); M->def_move=1; if(GetFileAttributesW(full_def)!=INVALID_FILE_ATTRIBUTES) M->def_pre=CopyFileW(full_def,M->a_def,FALSE); }
  if(full_tr){ swprintf(M->a_tr,MAX_PATH*2,L"%ls\\%ls.trace",M->tdir,nm); M->tr_move=1; } }

/* après exécution : rapatrie les sorties, nettoie */
static void amap_finish(amap_t *M){
  if(!M->mode) return;
  if(M->def_move){ if(GetFileAttributesW(M->a_def)!=INVALID_FILE_ATTRIBUTES) MoveFileExW(M->a_def,M->r_def,MOVEFILE_REPLACE_EXISTING|MOVEFILE_COPY_ALLOWED);
    else if(M->def_pre) DeleteFileW(M->r_def); /* le compilateur a supprimé le .def (comme il l'aurait fait sur place) */ }
  if(M->tr_move&&GetFileAttributesW(M->a_tr)!=INVALID_FILE_ATTRIBUTES) MoveFileExW(M->a_tr,M->r_tr,MOVEFILE_REPLACE_EXISTING|MOVEFILE_COPY_ALLOWED);
  if(M->mode==2){ wchar_t p[MAX_PATH*2],ab[MAX_PATH*2]; WIN32_FIND_DATAW fd; swprintf(p,MAX_PATH*2,L"%ls\\*",M->tdir); HANDLE h=FindFirstFileW(p,&fd);
    if(h!=INVALID_HANDLE_VALUE){ do{ if(fd.cFileName[0]==L'.') continue; swprintf(p,MAX_PATH*2,L"%ls\\%ls",M->tdir,fd.cFileName); DeleteFileW(p);}while(FindNextFileW(h,&fd)); FindClose(h); }
    swprintf(ab,MAX_PATH*2,L"%ls\\absent",M->tdir); RemoveDirectoryW(ab); RemoveDirectoryW(M->tdir); } }

static void breplace(buf_t *b,const char *from,const char *to){ if(!b->p||!*from) return; buf_t o={0}; size_t fl=strlen(from),tl=strlen(to); const char *p=b->p,*e=b->p+b->n;
  while(p<e){ const char *q=0; for(const char *s=p;s+fl<=e;s++) if(!memcmp(s,from,fl)){ q=s; break; } if(!q){ bput(&o,p,e-p); break; } bput(&o,p,q-p); bput(&o,to,tl); p=q+fl; }
  if(!o.p) bput(&o,"",0); free(b->p); *b=o; }
static void out_utf8(HANDLE h,const buf_t *b){ DWORD md,w; if(!b->n) return;
  if(GetConsoleMode(h,&md)){ int k=MultiByteToWideChar(CP_UTF8,0,b->p,(int)b->n,0,0); wchar_t *t=malloc((k+1)*sizeof(wchar_t)); MultiByteToWideChar(CP_UTF8,0,b->p,(int)b->n,t,k); WriteConsoleW(h,t,k,&w,0); free(t); }
  else WriteFile(h,b->p,(DWORD)b->n,&w,0); }

static int run_proc(const wchar_t *exe,wchar_t *cmd,buf_t *out,buf_t *err,int relay,DWORD *rc,double *ms){
  SECURITY_ATTRIBUTES sa={sizeof sa,0,TRUE}; HANDLE ord,owr,erd,ewr; CreatePipe(&ord,&owr,&sa,0); CreatePipe(&erd,&ewr,&sa,0);
  SetHandleInformation(ord,HANDLE_FLAG_INHERIT,0); SetHandleInformation(erd,HANDLE_FLAG_INHERIT,0);
  STARTUPINFOW si={sizeof si}; si.dwFlags=STARTF_USESTDHANDLES; si.hStdInput=GetStdHandle(STD_INPUT_HANDLE); si.hStdOutput=owr; si.hStdError=ewr;
  PROCESS_INFORMATION pi; LARGE_INTEGER f,t0,t1; QueryPerformanceFrequency(&f); QueryPerformanceCounter(&t0); *rc=255;
  if(!CreateProcessW(exe,cmd,0,0,TRUE,0,0,0,&si,&pi)){ CloseHandle(owr); CloseHandle(ewr); CloseHandle(ord); CloseHandle(erd); return 0; }
  CloseHandle(owr); CloseHandle(ewr);
  HANDLE nul=CreateFileW(L"NUL",GENERIC_WRITE,FILE_SHARE_WRITE,0,OPEN_EXISTING,0,0);
  pump_t po={ord,{0},relay?GetStdHandle(STD_OUTPUT_HANDLE):nul}, pe={erd,{0},relay?GetStdHandle(STD_ERROR_HANDLE):nul};
  HANDLE th[2]={CreateThread(0,0,pump,&po,0,0),CreateThread(0,0,pump,&pe,0,0)};
  WaitForSingleObject(pi.hProcess,INFINITE); WaitForMultipleObjects(2,th,TRUE,INFINITE); GetExitCodeProcess(pi.hProcess,rc);
  CloseHandle(pi.hProcess); CloseHandle(pi.hThread); CloseHandle(th[0]); CloseHandle(th[1]); CloseHandle(ord); CloseHandle(erd); CloseHandle(nul);
  QueryPerformanceCounter(&t1); if(ms) *ms=(t1.QuadPart-t0.QuadPart)*1000.0/f.QuadPart;
  *out=po.b; *err=pe.b; if(!out->p) bput(out,"",0); if(!err->p) bput(err,"",0); return 1; }

/* Lance le compilateur. oef/def = arguments tels que donnés (def peut être NULL), tr = chemin de trace (OEF2WIMS_TRACE) ou NULL.
   cmd_disp reçoit la commande telle qu'avec les chemins d'origine (pour les journaux). *mode = 0/1/2. */
static int core_exec(const wchar_t *exe,const wchar_t *oef,const wchar_t *def,const wchar_t *tr,int relay,buf_t *O,buf_t *E,DWORD *rc,double *ms,wchar_t *cmd_disp,int *mode){
  wchar_t foef[MAX_PATH*2],fdef[MAX_PATH*2],ftr[MAX_PATH*2],t[MAX_PATH*2];
  GetFullPathNameW(oef,MAX_PATH*2,foef,0); if(def) GetFullPathNameW(def,MAX_PATH*2,fdef,0); else { derived_def(t,oef); GetFullPathNameW(t,MAX_PATH*2,fdef,0); }
  if(tr) GetFullPathNameW(tr,MAX_PATH*2,ftr,0);
  cmd_disp[0]=0; quote(cmd_disp,exe); memmove(cmd_disp,cmd_disp+1,wcslen(cmd_disp)*sizeof(wchar_t)); quote(cmd_disp,oef); if(def) quote(cmd_disp,def);
  amap_t M; amap_prepare(&M,foef,fdef,tr?ftr:0); *mode=M.mode;
  int ran;
  if(!M.mode){ if(tr) SetEnvironmentVariableW(L"OEF2WIMS_TRACE",tr);
    wchar_t *cmd=calloc(32768,sizeof(wchar_t)); wcscpy(cmd,cmd_disp); ran=run_proc(exe,cmd,O,E,relay,rc,ms); free(cmd); }
  else { if(tr) SetEnvironmentVariableW(L"OEF2WIMS_TRACE",M.a_tr);
    wchar_t *cmd=calloc(32768,sizeof(wchar_t)); quote(cmd,exe); memmove(cmd,cmd+1,wcslen(cmd)*sizeof(wchar_t)); quote(cmd,M.a_oef); quote(cmd,M.a_def);
    ran=run_proc(exe,cmd,O,E,0,rc,ms); free(cmd);
    /* stdout : « <argv1>.. -> <sortie> » ; on remet les chemins d'origine (UTF-8) */
    char *f1=acp(M.a_oef),*f2=acp(M.a_def),*t1=u8(oef),*t2; wchar_t dd[MAX_PATH*2]; if(def) t2=u8(def); else { derived_def(dd,oef); t2=u8(dd); }
    breplace(O,f2,t2); breplace(O,f1,t1); breplace(E,f2,t2); breplace(E,f1,t1); free(f1); free(f2); free(t1); free(t2);
    if(relay){ out_utf8(GetStdHandle(STD_OUTPUT_HANDLE),O); out_utf8(GetStdHandle(STD_ERROR_HANDLE),E); } }
  if(tr) SetEnvironmentVariableW(L"OEF2WIMS_TRACE",0);
  amap_finish(&M); return ran; }
