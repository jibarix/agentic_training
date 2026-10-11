# Screening Tasks for Agentic Automation

- `task_screening.pdf`: the document. A worksheet for deciding whether a task needs an agent, with worked examples. It is the companion to `../design_process/design_process.pdf`.
- `task_screening.tex`: the source, maintained by hand; edit this file directly. The diagram style is shared with `../design_process/design_process.tex`.

Rebuild (from this folder). It runs twice so the references resolve:

```
pdflatex -disable-installer -interaction=nonstopmode task_screening.tex
pdflatex -disable-installer -interaction=nonstopmode task_screening.tex
```

Update the version and date in `\date{}` when the document changes.
