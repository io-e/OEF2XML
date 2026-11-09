# faux validateur (oef_validate.py introuvable) : imprime des accents et un diagnostic au format du vrai
import sys
f = sys.argv[1]
print("Résumé : vérification de « %s » — éèàçù ΣΩ 数学" % f)
print("%s:3:9: avertissement: accolade peut-être non fermée (test accents é)" % f)
