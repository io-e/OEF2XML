# Corpus metadata

- `corpus.map`: each renumbered corpus file (`00001.oef` …) and where it came from (upstream WIMS 4.31b path, or `xml2oef` output).
- `per_file.csv`: per-file statistics from `oef_corpus_stats.py`. Its `origin` column is the class (`upstream_class`, `upstream_module`, `upstream_model`, `generated`, ...).

The OEF files themselves are not committed. Upstream files come from the WIMS 4.31b sources (Debian `wims_4.31b+dfsg1.orig.tar.gz`, GPL); generated files come from the owner's Eleda programs.
To reproduce the §14.2 bounds: `python3 ../oef_corpus_stats.py --corpus <corpus dir> --map corpus.map --out <dir>`, then `scope_bounds.py` (see its `--help`).
