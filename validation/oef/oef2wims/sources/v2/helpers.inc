typedef struct { char *p; size_t n, cap; } buf_t;
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
