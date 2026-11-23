# Report verification summary

Report: *Secure API Web Application: A Zero-Trust API Communication Platform*, Naytik Goyal (24BCS10960), November 2026.
Final files: `output/Cybersecurity_Project_Report_Naytik_Goyal.pdf` (107 pages) and `output/Cybersecurity_Project_Report_Naytik_Goyal.docx` (editable).
Checked on 28 October 2026, including a second round of testing after five fixes (see "Changes made to the author's repository"). Statuses: PASS, FAIL, NOT VERIFIED, NOT APPLICABLE. Nothing is marked PASS without the evidence named beside it.

## Size and contents of the final report
12 front-matter pages (roman numerals) and 95 pages from Chapter 1 (arabic); about 27,000 words; 53 figures; 32 tables; 37 references; 5 chapters; Appendix-1 (user manual), Appendix-2 (API and test reference), Appendix-3 (code excerpts); Achievements.

## Checklist

| Item | Status | Evidence and notes |
|---|---|---|
| Order of contents follows the template (title, certificate, acknowledgement, contents, lists, abstract, graphical abstract, abbreviations, Chapters 1-5, references, appendix with user manual, achievements) | PASS | Page-by-page review of the final PDF |
| Fonts and sizes: Times New Roman; body 12 pt, 1.5 spacing, justified; chapter titles 16 pt bold centred; headings 14 pt bold; sub-headings 12 pt bold; captions 10 pt bold | PASS | Set in the document styles; the PDF embeds Times New Roman and Courier New (checked with a font listing) |
| Abstract and certificate: 14 pt, double spacing; abstract fits one page | PASS | The certificate's signature block is single-spaced so the page holds the whole certificate |
| Figure captions below figures; table captions above tables; lists use the identical captions | PASS | The lists are generated from the same caption text |
| Each chapter, the references and each appendix start on a new page | PASS | Chapters begin on PDF pages 13, 19, 28, 44 and 84; automated check plus visual review |
| Contents, list of figures and list of tables match the final layout | PASS | 134 entries mapped to their pages; page map stable after the second build pass. They are generated text with dot leaders, not a Word field that updates itself |
| Roman numerals for front matter, arabic from Chapter 1, title page unnumbered | PASS | Footer numbers checked on the rendered pages |
| Figure and table numbers consistent and every one mentioned in the text | PASS | Cross-check of all 53 figures and 32 tables against their captions and mentions. A duplicate-identifier error found during this check was fixed, and the builder now stops if one recurs |
| Specimen cover and certificate layouts | NOT VERIFIED | The template PDF refers to specimen pages but does not contain them. The layout follows the reference report and the template's certificate rules |
| Margins | NOT APPLICABLE | The template gives none; 2.54 cm on all sides was used |
| Every repository claim checked against code or a run | PASS | `discovery/02-source-of-truth.md`; statements in the report use the behaviour observed, not the project's documents |
| Screenshots are genuine | PASS | 8 browser screenshots from the live stack (`evidence/screenshots`). The two sign-in screenshots are cropped to remove the page's demonstration-credential note |
| Terminal figures are real output | PASS | Rendered from the saved logs in `evidence/`. In the four functional-flow figures, lines longer than 84 characters are shortened with "..."; the full text is in the log files. Local scratch-folder paths in the figures are replaced by `<test copy>`; the raw logs keep the real paths |
| Diagrams match the code | PASS | Drawn from the verified architecture; reviewed against the source and the test results |
| Test results match observed output | PASS | First round: 17 of 17 unit tests; 19 of 19 live flows; 28 of 28 attacker checks in the corrected run; TLS, timing, rate-limit, lockout, browser and Loki probes; the stock `run_all.py` result (3 pass, 2 fail) reported as observed. Re-test after the fixes: 9 of 9 new Auth Server tests and 17 of 17 again; the 19 flows repeated with all 48 comparable result lines identical; timing, lockout, Grafana and toolkit re-tests (R-01 to R-06) in `evidence/after-fixes/` |
| Implemented, tested and proposed features kept separate | PASS | Threat register, defects table and future work |
| No credentials or secrets in the report or evidence | PASS | Text scan of the PDF and of `evidence/` and `source/` for demonstration passwords, the Vault token, keys and token strings found none. Demonstration passwords were redacted from two attacker logs. Images cannot be text-scanned, so the screenshots were reviewed by eye |
| Citations: existence, authors, titles, years, identifiers | PASS (with one flag) | 37 sources: 29 checked on the official page or registry record, 7 through search results that list the venue page, 1 flagged (Halfond, Viegas and Orso 2006; its PDF could not be opened because of a certificate error). See `references/references-verified.md` |
| Citations: every sentence supported by the full text of its source | NOT VERIFIED | Statements were limited to what the official pages, abstracts and registry records say. Full texts were not read. NIST SP 800-63B-4 is cited only for its scope, not for specific rules |
| Every reference is cited in the text and every citation resolves | PASS | The builder fails on an unknown citation and lists unused references (none) |
| Similarity or plagiarism check | NOT VERIFIED | No checking service was available. No similarity score is claimed |
| Final PDF inspected visually | PASS | All 107 pages reviewed as contact sheets after the final build (eight sheets), many pages reviewed at readable size during the work, and automated checks for empty pages and stranded headings. Remaining short pages are chapter and appendix ends |
| Word file valid | PASS | Passed the Office schema validation (2,325 paragraphs) |
| Word file paginates the same as the PDF | NOT VERIFIED | Microsoft Word was not available. The PDF was produced with LibreOffice 26.8; Word may break pages slightly differently |
| Editable source saved | PASS | `source/` (text), `build/` (builder, diagrams, scripts), `assets/`, `output/*.docx` |

## What the author should check before submission
1. **Cover and certificate:** the institution (Chandigarh University, B.E. Computer Science Engineering) was taken from the reference report and the author's answers; the university's postal code 140413 comes from secondary listings and the official page names only the highway, village and district. The day of the viva is blank.
2. **Achievements:** the report states that no publications, patents, certifications or competition entries are claimed. Change it if there are any.
3. **Timeline:** the phase dates in Chapter 1 are approximate; they follow the build log's order and the September to mid-October period given by the author.
4. **Alternatives in Chapter 3** are presented as an analysis of three designs, not as a record of decisions taken at the time.
5. **AI-use statement:** none is included, as instructed. Check this against the university's current rules.
6. **Viva preparation:** the project's own `build-log.md` and `README.md` use phrases such as "sandbox" and earlier "sessions". Examiners who read the repository may ask what they refer to.
7. **Weaknesses reported:** Chapter 4 lists 16 findings, including ones that contradict statements in the project's documents. Five (D-01 to D-05) were fixed and re-tested; eleven remain open and are listed with recommendations. Chapter 4 describes the system as first tested, followed by a section on the fixes.
8. **Review the change to your repository:** see the next section. Your `docs/` folder still says, for example, that the toolkit passes 22 of 22 checks and describes a lockout per username; the report does not edit your documents.

## Changes made to the author's repository
After the first round the author asked for the findings to be fixed. Eleven existing files were changed and one test file was added, in `auth-server/`, `attacker-toolkit/`, `infra/grafana-dashboard.json`, `dashboard/src/components/AttackHistory.jsx` and the README. The originals were copied first to `pre-fix-backup/`, and the whole change is in `evidence/after-fixes/changes-to-repo.patch`.

| Finding | Change | Re-test result |
|---|---|---|
| D-01 login timing | One bcrypt comparison for every attempt, against a dummy hash when the username is unknown | Medians 56.5 ms against 56.0 ms (before: 131.5 against 10.7 ms) |
| D-02 lockout abuse | Lockout keyed by username and source address; account-wide failures logged | An attacker on another address is locked out; the real user logs in (200); one source stays locked |
| D-03, D-04 Grafana | Two queries corrected | All three panels return data |
| D-05 toolkit runner | Keys from Vault with a read token; SKIP status; brute force last; stricter replay check; SKIP shown in the dashboard | Without keys: 3 pass, 2 SKIP, exit 2. With a Vault token: 28 of 28, exit 0 |

The re-test found one mistake made during the fixing (a missing import in one attack script). It was corrected and a static check was run over every edited file. Findings D-06 to D-16 (the other code, configuration and documentation items) were not part of this fix round.

## Limitations of this verification
- Everything was tested on one machine, with Vault in development mode.
- The attack list is fixed; passing it does not show that no other attack works.
- Timing used four samples per group in the first round and eight in the re-test.
- The lockout re-test used a second container as the attacker's address, because one laptop has only one external address.
- The continuous-integration workflow was not run.
- The author's own working copy and Docker data were left untouched; the tests ran from a copy with newly generated keys.

## How to rebuild
Needs Node.js with the `docx` package, Python with PyMuPDF, Pillow and Playwright (headless Chromium), and LibreOffice. From `build/`, run `./build_all.sh --assets`. The paths to the helper environments are set at the top of that script.
