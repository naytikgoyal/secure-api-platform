# Report progress record

Last updated: 2026-10-28 (end of Stage 4, live evidence captured)

## Stage status
| Stage | Status |
|---|---|
| 1-4 Inputs, template, repository audit, live run | DONE |
| 5 Questions to the user | DONE: answers received (title, degree, single author, November 2026, designation, HOD, timeline); defaults chosen for the rest |
| 6 Blueprint | DONE |
| 7 Chapters 1-5, appendices, achievements written | DONE |
| 8 Diagrams, screenshots, terminal figures | DONE (20 diagrams and charts, 8 screenshots, 9 terminal figures) |
| 9 Assemble DOCX and PDF | DONE: `output/Cybersecurity_Project_Report_Naytik_Goyal.docx` and `.pdf`, 95 pages |
| 10-12 Verification and delivery | DONE: see `Report_Verification_Summary.md` |
| 13 Fix findings D-01 to D-05 in the repository, re-test, update the report | DONE: report is now 107 pages; originals in `pre-fix-backup/`; patch in `evidence/after-fixes/` |

## Decisions taken
Title "Secure API Web Application: A Zero-Trust API Communication Platform"; Chandigarh University, B.E. Computer Science Engineering; supervisor Mr. Joban Singh (Assistant Professor); HOD Ms. Jasneet Kaur; November 2026; viva day left blank; no AI-use statement (author's instruction); achievements: none claimed; margins 2.54 cm; roman front matter; "Figure N"/"Table N" numbering.

## Still open (for the author)
Items 1-8 under "What the author should check before submission" in `Report_Verification_Summary.md`. Findings D-06 to D-16 remain open by design.

## Environment notes
LibreOffice 26.8.1 installed for the current user only (`~/Applications/LibreOffice.app`; installer checked against the official SHA-256). Test stack torn down; the author's own containers and Docker volume were never touched. Scratch environments (PDF tools, Playwright, docx library) live in the session's scratch folder and can be recreated; paths are set at the top of `build/build_all.sh`.

## Resume instructions
Edit the text in `source/*.md`, then run `build/build_all.sh` (add `--assets` to redraw diagrams and terminal figures). Output goes to `output/`.
