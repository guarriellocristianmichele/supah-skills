# Our READMEs pass our own prose scanner, even where that departs from mattpocock style

The README layout follows mattpocock/skills (collapsible install blocks, problem and fix sections, a reference split by invocation), but headings use sentence case and lists avoid bold lead-ins, because the scanner flags Title Case headings and `**Label:**` bullets as tells. A repo that removes slop cannot ship docs that fail its own check. CI runs the scanner on every README with `docs/readme-keep.tsv` for the deliberate exceptions (cited paper titles, list-heavy install sections).
