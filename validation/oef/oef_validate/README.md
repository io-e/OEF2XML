# oef_validate — validateur statique de fichiers OEF (WIMS)

Python 3, bibliothèque standard uniquement. Les règles reproduisent le compilateur
`oef2wims` de WIMS (`src/OefMsg2wims/`), lu dans les sources WIMS 4.31b (Debian
`wims_4.31b+dfsg1.orig.tar.gz`).

## Fichiers
- `oef_validate.py` : validateur (CLI).
- `oef_spec.json` : commandes, anstypes, options et limites, **générés** depuis les sources.
- `gen_spec.py` : générateur de `oef_spec.json` (`python3 gen_spec.py /chemin/wims`).
- `compare_oracle.sh` : compare le verdict du validateur à celui du vrai `oef2wims` compilé.
- `fuzz_oracle.py` : mutations aléatoires des .oef officiels, comparées au vrai compilateur.
- `tests/` : tests pytest et fichiers OEF volontairement cassés (`tests/samples/`).

## Usage
    python3 oef_validate.py exo.oef [autres.oef ou dossiers]   # code 1 si erreur
    python3 oef_validate.py --strict dossier/                   # avertissements bloquants
    python3 oef_validate.py -q dossier/                         # résumé seul
Sortie : `fichier:ligne:colonne: erreur|avertissement: message`.

## Erreurs (= refus de oef2wims, sauf mention)
- fichier vide, ou >= 199999 octets
- (), [] ou {} non appariés **dans tout le fichier, texte compris** (même position que oef2wims)
- `\statement` absent ou multiple ; `\steps`/`\nextstep` multiple
- intitulé de `\answer` >= 40 caractères (« Answer prompt too long »)
- plus de 1024 directives (le compilateur ignore la suite)
- `\for` sans `var=` ni `var in` ; `\embed{reply n}` / `\embed{choice n}` hors limites
  (ces deux dernières sont des ajouts du validateur : oef2wims ne les refuse pas)

## Avertissements
type= inconnu (anstype de module possible), option non lue par l'anstype, commande
inconnue au niveau principal (ignorée silencieusement), variable non déclarée dans un
texte (devient vide), variable utilisée avant déclaration, déclaration sans valeur,
arguments en trop, titre > 80 caractères (tronqué).

## Résultats sur les sources WIMS 4.31b
- 333 .oef : 331 sans erreur ; les 2 en erreur sont aussi refusés par oef2wims (même ligne/colonne).
- Accord avec oef2wims : 333/333 fichiers ; 1000/1000 mutations aléatoires.
- `python3 -m pytest -q tests` : 11 tests OK.
