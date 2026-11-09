# test_unicode_E2.ps1 - chemins Unicode/longs : oef2wims.exe (référence) vs oef2wims-v2.exe / oef2wims-log.exe (E2)
param([string]$Root = "$PSScriptRoot\..\..\test_E2")
$ErrorActionPreference='Continue'; $B=(Resolve-Path "$PSScriptRoot\..").Path; $V3=(Resolve-Path "$B\..").Path
$ref="$B\oef2wims.exe"; $v2="$B\oef2wims-v2.exe"; $lg="$B\oef2wims-log.exe"
function Sha($p){ if(Test-Path -LiteralPath $p){ (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower().Substring(0,12) } else { 'NONE' } }
function Run($exe,[string[]]$a){ $o=& $exe @a 2>&1 | Out-String; [pscustomobject]@{rc=$LASTEXITCODE; out=$o} }
New-Item -ItemType Directory -Force $Root | Out-Null; $Root=(Resolve-Path $Root).Path
$ok="$V3\test_E1\corpus\00001.oef"; $bad="$V3\exemples_v2\c03_accolade_manquante.oef"
# référence ASCII
$asc="$Root\ascii"; New-Item -ItemType Directory -Force $asc | Out-Null; Copy-Item $ok "$asc\ok.oef" -Force; Copy-Item $bad "$asc\bad.oef" -Force
$null=Run $ref @("$asc\ok.oef"); $refsha=Sha "$asc\ok.def"; "ASCII reference .def sha=$refsha"
$long='long_'+('répertoire_très_long_'*9)
$dirs=@('Exercices été','数学','Συνάρτηση','test_😀','avec des espaces',"$long\数学_sous_dossier")
$rows=@()
foreach($d in $dirs){ $p="$Root\$d"; New-Item -ItemType Directory -Force -Path $p | Out-Null
  $n= if($d -eq '数学'){'练习'} elseif($d -like 'test_*'){'ok😀'} elseif($d -like 'Συν*'){'άσκηση'} else {'exo été'}
  Copy-Item -LiteralPath $ok "$p\$n.oef" -Force; Copy-Item -LiteralPath $bad "$p\c03 bad.oef" -Force
  Get-ChildItem -LiteralPath $p -Include *.def,*.log,*.json,*.prev,*.trace,*.html -Recurse:$false -ErrorAction SilentlyContinue | Remove-Item -Force
  $r0=Run $ref @("$p\$n.oef"); $s0=Sha "$p\$n.def"; Remove-Item -LiteralPath "$p\$n.def" -ErrorAction SilentlyContinue
  $r1=Run $v2 @('--json','--diff','--quiet',"$p\$n.oef"); $s1=Sha "$p\$n.def"
  $r1b=Run $v2 @('--json','--diff','--quiet',"$p\$n.oef"); $prev=Test-Path -LiteralPath "$p\$n.def.prev"
  $j=Get-Content -LiteralPath "$p\$n.json" -Raw -Encoding utf8 | ConvertFrom-Json
  $mode= if($j.chemin_ansi){$j.chemin_ansi}else{'direct'}
  Remove-Item -LiteralPath "$p\$n.def" -ErrorAction SilentlyContinue
  $r2=Run $lg @("$p\$n.oef"); $s2=Sha "$p\$n.def"
  $r3=Run $v2 @('--json','--quiet',"$p\c03 bad.oef"); $jb=Get-Content -LiteralPath "$p\c03 bad.json" -Raw -Encoding utf8 | ConvertFrom-Json
  $e=$jb.problemes | ?{ $_.source -eq 'compilateur' } | select -First 1
  $env:OEF2WIMS_FORCE_TEMP='1'; Remove-Item -LiteralPath "$p\$n.def" -ErrorAction SilentlyContinue
  $r4=Run $v2 @('--json','--quiet','--trace',"$p\$n.oef"); $s4=Sha "$p\$n.def"; $tr=Test-Path -LiteralPath "$p\$n.oef.trace"; $j4=(Get-Content -LiteralPath "$p\$n.json" -Raw -Encoding utf8 | ConvertFrom-Json).chemin_ansi
  Remove-Item Env:OEF2WIMS_FORCE_TEMP
  $rows+=[pscustomobject]@{dossier=($d.Substring(0,[Math]::Min(24,$d.Length))); len=("$p\$n.oef").Length; ref_rc=$r0.rc; ref_def=$s0; v2_rc=$r1.rc; v2_def=$s1; mode=$mode; diff_prev=$prev; json_name=($j.fichier -eq "$p\$n.oef"); log_rc=$r2.rc; log_def=$s2; err_rc=$r3.rc; err_pos="$($e.ligne):$($e.colonne)"; tmp_def=$s4; tmp_mode=$j4; tmp_trace=$tr } }
$rows | Export-Csv -Encoding utf8 -NoTypeInformation "$Root\results_E2.csv"; $rows | ConvertTo-Json -EscapeHandling EscapeNonAscii
# lot sur dossier Unicode
$p="$Root\数学"; $rb=Run $v2 @('--json','--quiet',$p); ("batch rc=$($rb.rc) :: $($rb.out.Trim())") | ConvertTo-Json -EscapeHandling EscapeNonAscii
$h=Get-Content -LiteralPath "$p\oef2wims-rapport.html" -Raw -Encoding utf8; "html contient 练习.oef : $($h.Contains('练习.oef'))  liens .log : $(([regex]::Matches($h,'href=""([^""]+\.log)""')|%{$_.Groups[1].Value}) -join ' | ')" | ConvertTo-Json -EscapeHandling EscapeNonAscii
$bj=Get-Content -LiteralPath "$p\oef2wims-batch.json" -Raw -Encoding utf8 | ConvertFrom-Json; ("batch.json fichiers : $(($bj.resultats|%{Split-Path $_.fichier -Leaf}) -join ', ')") | ConvertTo-Json -EscapeHandling EscapeNonAscii
$rl=Run $lg @($p); ("log batch rc=$($rl.rc) :: $($rl.out.Trim())") | ConvertTo-Json -EscapeHandling EscapeNonAscii
# console : sortie relayée avec chemin d'origine
("console v2 : " + (Run $v2 @("$Root\Συνάρτηση\άσκηση.oef")).out.Split("`n")[0]) | ConvertTo-Json -EscapeHandling EscapeNonAscii
("console ref: " + (Run $ref @("$Root\Συνάρτηση\άσκηση.oef")).out.Split("`n")[0]) | ConvertTo-Json -EscapeHandling EscapeNonAscii
