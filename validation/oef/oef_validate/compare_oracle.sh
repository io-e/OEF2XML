#!/bin/sh
# Compare le validateur au vrai compilateur oef2wims (compilé depuis src/OefMsg2wims).
# Usage : compare_oracle.sh /chemin/oef2wims /chemin/wims
OEF2WIMS=$1; ROOT=$2; HERE=$(dirname "$0"); TMP=$(mktemp -d)
agree=0; disagree=0; total=0
for f in $(find "$ROOT" -name '*.oef' | sort); do
  total=$((total+1))
  if "$OEF2WIMS" "$f" "$TMP/x.def" 2>&1 | grep -q ERROR; then c=KO; else c=OK; fi
  if python3 "$HERE/oef_validate.py" -q "$f" >/dev/null 2>&1; then v=OK; else v=KO; fi
  if [ $c = $v ]; then agree=$((agree+1)); else disagree=$((disagree+1)); echo "DESACCORD compilateur=$c validateur=$v $f"; fi
done
echo "total=$total accord=$agree desaccord=$disagree"
rm -rf "$TMP"
