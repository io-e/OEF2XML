# run_parity_E2.ps1 - non-régression E2 : enveloppe (v2 / log) vs référence Linux : rc, stdout, .def
param([string]$Exe, [string]$Args1 = "", [string]$Corpus = "$PSScriptRoot\..\..\test_E1\corpus",
      [string]$Reference = "$PSScriptRoot\..\..\test_E1\reference", [string]$Out)
$ErrorActionPreference = 'Stop'; $Exe=(Resolve-Path $Exe).Path
New-Item -ItemType Directory -Force $Out | Out-Null; $work=Join-Path $Out 'work'; New-Item -ItemType Directory -Force $work | Out-Null
function Sha($p){ if(Test-Path -LiteralPath $p){ (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower() } else { 'NONE' } }
$ref=@{}; Get-Content "$Reference\reference.tsv" | % { $c=$_ -split "`t"; $ref[$c[0]]=$c }
$tsv=Join-Path $Out 'parity_E2.tsv'; "id`trc_ref`trc`tstdout`tdef`tresult" | Set-Content $tsv
$sw=[Diagnostics.Stopwatch]::StartNew()
foreach($f in (Get-ChildItem $Corpus -Filter *.oef | Sort-Object Name)){
  $b=$f.BaseName; Copy-Item $f.FullName "$work\$b.oef" -Force; $so="$work\so_$b.txt"; $se="$work\se_$b.txt"; $def="$work\out_$b.def"; Remove-Item $def -ErrorAction SilentlyContinue
  $al=@(); if($Args1){ $al+=$Args1 -split ' ' }; $al+="$b.oef","out_$b.def"
  $p=Start-Process -FilePath $Exe -ArgumentList $al -WorkingDirectory $work -NoNewWindow -Wait -PassThru -RedirectStandardOutput $so -RedirectStandardError $se
  $r=$ref[$b]; $st= if((Sha $so) -eq $r[2]){'SAME'}else{'DIFF'}; $d= if((Sha $def) -eq $r[4]){'SAME'}else{'DIFF'}
  $res= if("$($p.ExitCode)" -eq $r[1] -and $st -eq 'SAME' -and $d -eq 'SAME'){'IDENTICAL'}else{'DIFFERENT'}
  "$b`t$($r[1])`t$($p.ExitCode)`t$st`t$d`t$res" | Add-Content $tsv
  Remove-Item "$work\$b.*","$work\so_$b.txt","$work\se_$b.txt","$work\out_$b.def" -ErrorAction SilentlyContinue }
$all=Import-Csv $tsv -Delimiter "`t"
"exe=$Exe args=$Args1 sha256=$(Sha $Exe) files=$($all.Count) identical=$(($all|?{$_.result -eq 'IDENTICAL'}).Count) different=$(($all|?{$_.result -eq 'DIFFERENT'}).Count) seconds=$([math]::Round($sw.Elapsed.TotalSeconds,1))"
