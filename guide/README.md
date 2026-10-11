# Agentic systems compilation guide

- `agentic_guide.pdf`: the navigable guide (Orientation, 15 topic modules, course catalogue, appendices).
- `agentic_guide.tex`: generated LaTeX. Do not edit it by hand.
- `content.py`: hand-written content (course cards, module primers, curated sequences, tracks, 16-week plan).
- `build_guide.py`: parses `../research/*.md` tables and renders the `.tex`. It checks every `[[...]]` cross-reference.

Rebuild (from this folder):

```
python -I build_guide.py
pdflatex -disable-installer -interaction=nonstopmode agentic_guide.tex
pdflatex -disable-installer -interaction=nonstopmode agentic_guide.tex
```

To refresh the data, update the tables in `../research/` (same column layout) and rebuild.
