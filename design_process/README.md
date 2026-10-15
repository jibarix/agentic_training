# Agentic System Design Process

- `design_process.pdf`: the document. It covers nine phases from problem framing to production, each with its goal, questions, cited evidence and a "done when" gate. Its main text has four diagrams (the process map, the Phase 2 ladder, Phase 3 ownership and the Phase 7 loop). It ends with the source disagreements, the document's limits and an appendix of three worked examples, each with a diagram.
- `design_process.tex`: the source, maintained by hand. Unlike the guide, there is no generator; edit this file directly.

The evidence base is three independent research passes over the 15 courses and the Anthropic, OpenAI and Google guides; every practice cites its source in the document.

Rebuild (from this folder). It runs twice so the table of contents and citations resolve:

```
pdflatex -disable-installer -interaction=nonstopmode design_process.tex
pdflatex -disable-installer -interaction=nonstopmode design_process.tex
```

Maintenance rules:

- Every practice must cite a specific source location: page, slide, section or rubric line.
- Mark the author's own synthesis with `\inferred`.
- When sources disagree, add a row to "Different emphases and my design choices". Don't pick a side silently.
- Figures are TikZ in the `.tex`, styled as follows: a pale panel, white boxes, small monospace tags, one coral accent for the focal element, and a legend strip. The shared styles (`dp`, `box`, `focal`, `hub`, `flow`, `back`, `hot`, `lab`) are in the preamble. When a phase changes, update its figure too. Each caption cites its sources and marks the arrangement `\inferred`. Render with `pdftoppm` to check the layout.
- Update the version and date in `\date{}`.
- Recheck when Anthropic's "Building Effective Agents", OpenAI's practical guide or the Google/Kaggle whitepapers are revised, or when a course in `../research/` publishes a project rubric.
