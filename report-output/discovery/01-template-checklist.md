# Official template checklist

Source of truth: `Project Report Format.pdf` (9 pages, Word, 2024). Pages 1 and 9 are blank; page 2 is a title leaf. The specimen pages it cites (Appendix 1 cover, 2/2A certificate, 3 contents) are **not included in the PDF**, so those layouts come from the reference report (Chandigarh University style) unless the user supplies the specimens.

## Mandatory order of contents (template p.3-4)
1. Title page
2. Bonafide certificate
3. Acknowledgement
4. Table of contents
5. List of figures
6. List of tables
7. Abstract (one page)
8. **Graphical abstract** (not in the reference report; the template requires it)
9. Abbreviations / symbols
10. Chapter 1: Introduction. Identification of client and need, relevant contemporary issues, problem identification, task identification, timeline, organisation of the report
11. Chapter 2: Literature survey. Timeline of the problem worldwide, bibliometric analysis, proposed solutions by researchers, summary linking literature to the project, problem definition, goals and objectives
12. Chapter 3: Design flow/process. Concept generation, evaluation and selection of specifications/features, design constraints (regulations, economic, environmental, health, manufacturability, safety, professional, ethical, social, political), analysis and feature finalisation, **at least 2 alternative designs**, best-design selection with comparison and reasons, implementation plan (flowchart / algorithm / block diagram)
13. Chapter 4: Results analysis and validation. Implementation using modern engineering tools, drawings/schematics, report preparation, project management and communication, testing/characterisation/interpretation/data validation
14. Chapter 5: Conclusion and future work (including deviation from expected results and way ahead)
15. References
16. Appendix, including a **user manual** (complete step-by-step with pictures)
17. **Achievements**

## Formatting rules
| Item | Rule |
|---|---|
| Paper | A4; flexible cover (thick white art paper) |
| Body text | Times New Roman 12, 1.5 line spacing, justified, black |
| Chapter title | TNR 16 bold, centred ("CHAPTER-No" line then "NAME OF CHAPTER" line) |
| Heading (1.1) | TNR 14 bold, left |
| Sub-heading (1.1.1) | TNR 12 bold, left |
| Figure caption | TNR 10 bold, **below** the figure: "Figure 1: Title" |
| Table caption | TNR 10 bold, **above** the table: "Table 1: Caption" |
| Certificate and abstract | TNR 14, double spacing |
| TOC, lists of tables/figures, abbreviations | 1.5 spacing |
| Certificate content | Supervisor signature; supervisor name, then the word SUPERVISOR in capitals, then academic designation (no administrative titles), department, full institution address |
| Page numbers | Front matter in lower-case roman. Title page and certificate are numbered but not listed in the contents |
| Contents | Must list everything after it and anything before it (except title page and certificate) |
| List of tables/figures | Captions identical to those in the text |
| Appendices | Numbered Appendix-1, Appendix-2, ...; carry the title of the work; listed in contents |
| References | Heading "REFERENCES"; alphabetical by first author; single spacing, left-justified; author then (year) then 'title', journal/venue, vol, pp. |
| Figures/tables | Placed next to where they are cited |
| Margins | **Not specified** by the template |

## Conflicts between template and reference report (template wins)
| Topic | Template | Reference report | Default I will use |
|---|---|---|---|
| Graphical abstract | Required | Absent | Include |
| Front-matter page numbers | Lower-case roman | "Page \| N" arabic from page 2 | Roman for front matter, arabic from Chapter 1 (confirm) |
| Figure/table numbering | "Figure 1", "Table 1" | "Figure 3.1" (per chapter) | Sequential per template (confirm) |
| Certificate | Needs supervisor name, designation, address | No names printed | Follow template; needs supervisor designation |
| Reference style | Author (year) 'title' ..., alphabetical | Numbered [1].., alphabetical | Template style, numbered list in alphabetical order |
| Chapters per page | Not stated | Each chapter on a new page | New page per chapter (the user also requires this) |

## Page-count reality check
Reference report is 25 pages for a 2-author ML project. The template sets no minimum or maximum. Roughly 100 pages is achievable here only because the project is large (about 5,500 lines across code, scripts and docs, 5 services, plus an attacker toolkit), and only if the appendices carry the user manual, API reference, test-case tables and key code excerpts. Page budget is in `PROGRESS.md`.
