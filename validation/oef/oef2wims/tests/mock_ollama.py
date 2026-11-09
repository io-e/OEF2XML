#!/usr/bin/env python3
"""Faux serveur Ollama (/api/chat) pour tester oef_llm_fix.py sans modèle."""
import json, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
CALLS = {}
def src_of(prompt):
    s = prompt.split("=== SOURCE ACTUEL (numéros de ligne pour référence seulement) ===\n", 1)[1].rstrip("\n")
    return "\n".join(re.sub(r"^\s*\d+ \| ", "", l, count=1) for l in s.split("\n"))
def answer(prompt):
    name = re.search(r"« (.+?) »", prompt).group(1); n = CALLS[name] = CALLS.get(name, 0) + 1; s = src_of(prompt)
    wrap = lambda t: f"Voici le fichier corrigé :\n```oef\n{t}```\n"
    if name.startswith("c02"): return wrap(s.replace("f'(1.}", "f'(1).}"))
    if name.startswith("c03"): return wrap(s.replace("randint(1..9)\n\\statement", "randint(1..9)}\n\\statement"))
    if name.startswith("c08"): return wrap(s.replace("\\statment", "\\statement"))
    if name.startswith("c09"):  # style deepseek-r1
        return "<think>Il y a deux \\statement, je les fusionne.</think>\n" + wrap(s.replace("\\statement{Partie 1}", "\\statement{Partie 1 <br> Partie 2}").replace("\\statement{Partie 2}\n", ""))
    if name.startswith("c04"):  # 1er essai inutile, 2e essai correct
        return wrap(s) if n == 1 else wrap(s.replace("4.)}", "4.}"))
    if name.startswith("c11"):  # mauvais : supprime la réponse
        return wrap(s.replace("\\answer{Donnez la valeur exacte de la derivee seconde en x egal deux}{3}\n", ""))
    if name.startswith("c06"):  # réécrit tout
        return wrap("\\title{Nouveau}\n\\statement{Tout autre chose}\n\\answer{a}{1}\n\\answer{b}{2}\n\\answer{c}{3}\n\\answer{d}{4}\n")
    return "Désolé, je ne peux pas aider avec ça."   # c07 etc. : réponse inutilisable
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert self.path == "/api/chat" and req["stream"] is False and req["options"]["temperature"] == 0.1
        body = json.dumps({"model": req["model"], "message": {"role": "assistant", "content": answer(req["messages"][-1]["content"])}, "done": True}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 11434), H).serve_forever()
