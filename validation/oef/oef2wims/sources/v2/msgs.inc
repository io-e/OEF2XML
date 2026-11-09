/* Explications en français de TOUS les messages d'erreur de oef2wims (WIMS 4.31b).
   Sources : oef2wims.c, oeflines.c, outexec.c, process.c, sp.c (oef_error / sp_error)
   et Lib/libwims.c error() appelé depuis Lib/text.c et Lib/liblines.c. */
typedef struct { const char *key, *code, *titre, *expl, *fix, *avant, *apres; } emsg_t;
static const emsg_t EMSG[]={
 {"Unmatched parentheses","PAREN","Parenthèse, crochet ou accolade non appariés",
  "Le compilateur compte les (), [] et {} dans TOUT le fichier, y compris dans le texte de l'énoncé, sans aucun échappement possible. "
  "Un caractère ouvrant sans fermant (ou un fermant en trop) bloque toute la compilation.",
  "Si le caractère signalé est ouvrant : ajoutez le fermant correspondant à l'endroit indiqué. "
  "S'il est fermant : supprimez-le ou ajoutez l'ouvrant manquant. Dans un texte, un intervalle comme [0;1[ doit être écrit avec des entités HTML : &#91;0;1&#91; (&#91; pour [, &#93; pour ]), ou avec \\lbrack / \\rbrack en LaTeX.",
  "\\statement{Calculer f(\\x pour x = 2.}","\\statement{Calculer f(\\x) pour x = 2.}"},
 {"unmatched_parentheses","SPPAREN","Parenthèse non fermée dans un appel de fonction",
  "Une fonction (par ex. randint(, simplify(, slib( ...) est appelée avec une parenthèse ouvrante sans fermante, "
  "après substitution des variables.",
  "Vérifiez l'appel de fonction dans la directive indiquée : chaque nom( doit avoir sa ) avant la fin de la directive.",
  "\\real{a=randint(1..10}","\\real{a=randint(1..10)}"},
 {"Multiple definition of steps","STEPS2","\\steps (ou \\nextstep) défini deux fois",
  "Un exercice ne peut avoir qu'une seule directive \\steps ou \\nextstep.",
  "Gardez une seule directive \\steps{...} et regroupez-y toutes les étapes, séparées par des virgules ou des points-virgules.",
  "\\steps{r1}\n\\steps{r2}","\\steps{r1\n r2}"},
 {"Multiple definition of statement","STMT2","\\statement défini deux fois",
  "L'énoncé (\\statement) doit être unique ; un second \\statement est refusé.",
  "Fusionnez les deux énoncés dans un seul \\statement{...}, ou renommez le second (par ex. \\hint ou \\feedback).",
  "\\statement{Partie 1}\n\\statement{Partie 2}","\\statement{Partie 1 <br> Partie 2}"},
 {"Answer prompt too long","PROMPT","Libellé de \\answer trop long",
  "Le premier argument de \\answer{libellé}{...} est limité à 39 caractères (MAX_PROMPTLEN=40, après remplacement des variables).",
  "Raccourcissez le libellé et déplacez la phrase explicative dans le \\statement.",
  "\\answer{Donnez la valeur exacte de la dérivée en x=2}{\\d}","\\answer{f'(2) =}{\\d}"},
 {"No statement defined","NOSTMT","Aucun \\statement",
  "Tout exercice OEF doit contenir une directive \\statement{...} (l'énoncé). Elle manque ou son nom est mal orthographié.",
  "Ajoutez \\statement{...} après les définitions de variables et avant les \\answer / \\choice.",
  "\\title{Exo}\n\\answer{x=}{3}","\\title{Exo}\n\\statement{Résoudre 2x=6.}\n\\answer{x=}{3}"},
 {"Unable to open output file","OUTPUT","Impossible d'écrire le fichier .def",
  "Le compilateur n'a pas pu créer le fichier de sortie : dossier inexistant ou protégé en écriture, fichier .def ouvert dans un autre programme, ou chemin trop long.",
  "Vérifiez le dossier de sortie, fermez le .def s'il est ouvert, ou indiquez un autre chemin en 2e argument.",
  "oef2wims.exe exo.oef C:\\Windows\\exo.def","oef2wims.exe exo.oef D:\\sortie\\exo.def"},
 {"Source file bad or too long","TOOLONG","Fichier source illisible ou trop gros",
  "Le fichier doit faire moins de 199 999 octets et être lisible.",
  "Découpez l'exercice, retirez les images intégrées / longs blocs de données, ou vérifiez le chemin et les droits.",
  "(fichier de 250 Ko)","(deux exercices de 125 Ko)"},
 {"Empty source file","EMPTY","Fichier vide",
  "Le fichier .oef ne contient aucun octet.",
  "Vérifiez que l'enregistrement a bien eu lieu et que le bon fichier est compilé ; un OEF minimal contient au moins \\title et \\statement.",
  "(vide)","\\title{Exo}\n\\statement{Énoncé}"},
 {"formula too long","FORMULA","Expression trop longue",
  "Une ligne de calcul ou un bloc à exécuter dépasse 45 000 caractères après remplacement.",
  "Découpez le calcul en plusieurs variables intermédiaires.",
  "\\text{t=... (50 000 caractères)}","\\text{t1=...}\n\\text{t2=...}\n\\text{t=\\t1,\\t2}"},
 {"syntax_error","SYNTAX","Erreur de syntaxe dans une fonction texte",
  "Une fonction de manipulation de texte (wims(...), text ...) a reçu une syntaxe invalide (mot-clé absent ou arguments mal placés).",
  "Relisez la directive indiquée (dernière directive traitée) et comparez avec la documentation de la commande.",
  "\\text{t=wims(text select abc)}","\\text{t=wims(text select abc mask 101)}"},
 {"text_bad_table","TEXTTABLE","Table de texte invalide",
  "Les chaînes passées à une commande 'text' n'ont pas la même longueur.",
  "Donnez des masques et chaînes de même longueur dans la directive indiquée.",
  "wims(text mark 1 in 10 and abc)","wims(text mark 1 in 101 and abc)"},
 {"string_too_long","STRLONG","Chaîne trop longue",
  "Une chaîne dépasse la taille maximale (45 000 caractères) lors d'un remplacement.",
  "Réduisez la taille des données ou découpez-les en plusieurs variables.","",""},
 {"cmd_output_too_long","CMDLONG","Sortie de commande trop longue",
  "Une commande a produit plus de 45 000 caractères.",
  "Réduisez la taille des données générées.","",""},
};
#define NEMSG (int)(sizeof EMSG/sizeof EMSG[0])
static const char *DIRS[]={"answer","author","choice","complex","computeanswer","condition","conditions","credits","css","description","else","email","endif","endwhile","feedback","for","format","function","help","hint","if","ifval","int","integer","keywords","language","latex","matrix","mdef","next","nextstep","observation","parameter","plot","precision","range","rational","real","reply","solution","statement","steps","text","title","title_ca","title_cn","title_en","title_es","title_fr","title_it","title_nl","title_si","variable","while","wims"};
static const int DIRPC[]={5,1,5,2,1,4,1,2,1,1,0,1,0,0,2,1,1,2,1,1,1,1,2,2,1,1,1,2,2,0,1,1,2,3,1,1,2,2,5,1,1,1,2,1,1,1,1,1,1,1,1,1,2,1,1};
#define NDIRS (int)(sizeof DIRS/sizeof DIRS[0])
