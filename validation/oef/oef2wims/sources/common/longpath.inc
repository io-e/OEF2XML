/* longpath.inc (E2) : chemins > 260 caractères pour les API fichiers Win32 des enveloppes.
   À inclure juste après <windows.h>. Ajoute \\?\ (ou \\?\UNC\) aux chemins absolus longs. */
static const wchar_t *lp_fix(const wchar_t *p, wchar_t *b, size_t bn){
  if(!p||wcslen(p)<240||!wcsncmp(p,L"\\\\?\\",4)) return p;
  if(p[0]&&p[1]==L':'&&p[2]==L'\\'){ if(wcslen(p)+5>bn) return p; wcscpy(b,L"\\\\?\\"); wcscat(b,p); return b; }
  if(p[0]==L'\\'&&p[1]==L'\\'){ if(wcslen(p)+9>bn) return p; wcscpy(b,L"\\\\?\\UNC\\"); wcscat(b,p+2); return b; }
  return p; }
#define LPB wchar_t _b1[1100],_b2[1100]
static HANDLE lp_CreateFileW(LPCWSTR p,DWORD a,DWORD s,LPSECURITY_ATTRIBUTES sa,DWORD c,DWORD f,HANDLE t){ LPB; (void)_b2; return CreateFileW(lp_fix(p,_b1,1100),a,s,sa,c,f,t); }
static DWORD lp_GetFileAttributesW(LPCWSTR p){ LPB; (void)_b2; return GetFileAttributesW(lp_fix(p,_b1,1100)); }
static BOOL lp_GetFileAttributesExW(LPCWSTR p,GET_FILEEX_INFO_LEVELS l,LPVOID d){ LPB; (void)_b2; return GetFileAttributesExW(lp_fix(p,_b1,1100),l,d); }
static BOOL lp_CopyFileW(LPCWSTR a,LPCWSTR b,BOOL f){ LPB; return CopyFileW(lp_fix(a,_b1,1100),lp_fix(b,_b2,1100),f); }
static BOOL lp_MoveFileExW(LPCWSTR a,LPCWSTR b,DWORD f){ LPB; return MoveFileExW(lp_fix(a,_b1,1100),lp_fix(b,_b2,1100),f); }
static BOOL lp_DeleteFileW(LPCWSTR p){ LPB; (void)_b2; return DeleteFileW(lp_fix(p,_b1,1100)); }
static HANDLE lp_FindFirstFileW(LPCWSTR p,LPWIN32_FIND_DATAW d){ LPB; (void)_b2; return FindFirstFileW(lp_fix(p,_b1,1100),d); }
static DWORD lp_GetShortPathNameW(LPCWSTR p,LPWSTR o,DWORD n){ LPB; (void)_b2; const wchar_t *q=lp_fix(p,_b1,1100); DWORD r=GetShortPathNameW(q,o,n);
  if(r&&r<n&&q!=p){ if(!wcsncmp(o,L"\\\\?\\UNC\\",8)){ memmove(o+2,o+8,(wcslen(o+8)+1)*sizeof(wchar_t)); r-=6; } else if(!wcsncmp(o,L"\\\\?\\",4)){ memmove(o,o+4,(wcslen(o+4)+1)*sizeof(wchar_t)); r-=4; } } return r; }
#define CreateFileW lp_CreateFileW
#define GetFileAttributesW lp_GetFileAttributesW
#define GetFileAttributesExW lp_GetFileAttributesExW
#define CopyFileW lp_CopyFileW
#define MoveFileExW lp_MoveFileExW
#define DeleteFileW lp_DeleteFileW
#define FindFirstFileW lp_FindFirstFileW
#define GetShortPathNameW lp_GetShortPathNameW
