# Verified reference list (draft for Chapter 2 and later chapters)

Verified on 28 October 2026. 37 sources: 29 at level A, 7 at level B, 1 at level C. The numbered list below is generated from `build/refs_data.py`, the same data the report uses.

## Verification levels
- **A**: the official page or a structured registry record (RFC Editor, NIST CSRC, OWASP, MITRE CWE, Crossref, HashiCorp, martinfowler.com) was opened and the details below were read from it.
- **B**: confirmed through search results that list the official venue/publisher page (USENIX, IEEE CS, IACR, Google Research, NSA/CISA, library catalogues) and agree on every detail; the page itself was not opened.
- **C**: weakly confirmed; needs a decision (see "Open items").

Metadata verification is not the same as content verification. Before each citation is used in the text, I will check that the source actually supports the sentence it is attached to.

## References (template style)

1. Barker, E. (2020) ‘Recommendation for Key Management: Part 1 – General’, NIST Special Publication 800-57 Part 1 Revision 5, National Institute of Standards and Technology, Gaithersburg, MD. https://doi.org/10.6028/NIST.SP.800-57pt1r5 **[A]**
2. Bellare, M., Canetti, R. and Krawczyk, H. (1996) ‘Keying Hash Functions for Message Authentication’, Advances in Cryptology – CRYPTO ’96, Lecture Notes in Computer Science Vol.1109, Springer, Berlin, pp.1-15. https://doi.org/10.1007/3-540-68697-5_1 **[B]**
3. Brumley, D. and Boneh, D. (2003) ‘Remote Timing Attacks are Practical’, Proceedings of the 12th USENIX Security Symposium, Washington, D.C., August 2003. **[B]**
4. Chandramouli, R. (2019) ‘Security Strategies for Microservices-based Application Systems’, NIST Special Publication 800-204, National Institute of Standards and Technology, Gaithersburg, MD. https://doi.org/10.6028/NIST.SP.800-204 **[A]**
5. Chandramouli, R. and Butcher, Z. (2020) ‘Building Secure Microservices-based Applications Using Service-Mesh Architecture’, NIST Special Publication 800-204A, National Institute of Standards and Technology, Gaithersburg, MD. https://doi.org/10.6028/NIST.SP.800-204A **[A]**
6. Dragoni, N., Giallorenzo, S., Lluch Lafuente, A., Mazzara, M., Montesi, F., Mustafin, R. and Safina, L. (2017) ‘Microservices: Yesterday, Today, and Tomorrow’, in Mazzara, M. and Meyer, B. (eds) Present and Ulterior Software Engineering, Springer, Cham, pp.195-216. https://doi.org/10.1007/978-3-319-67425-4_12 **[A]**
7. Halfond, W.G.J., Viegas, J. and Orso, A. (2006) ‘A Classification of SQL-Injection Attacks and Countermeasures’, Proceedings of the International Symposium on Secure Software Engineering, March 2006. **[C]**
8. Hannousse, A. and Yahiouche, S. (2021) ‘Securing microservices and microservice architectures: A systematic mapping study’, Computer Science Review, Vol.41, Article 100415. https://doi.org/10.1016/j.cosrev.2021.100415 **[A]**
9. Hardt, D. (ed.) (2012) ‘The OAuth 2.0 Authorization Framework’, RFC 6749, Internet Engineering Task Force, October 2012. https://www.rfc-editor.org/info/rfc6749 **[A]**
10. HashiCorp (n.d.) ‘What is Vault?’, Vault documentation, HashiCorp Developer. https://developer.hashicorp.com/vault/docs/about-vault/what-is-vault (accessed 28 October 2026) **[A]**
11. Jones, M. and Hardt, D. (2012) ‘The OAuth 2.0 Authorization Framework: Bearer Token Usage’, RFC 6750, Internet Engineering Task Force, October 2012. https://www.rfc-editor.org/info/rfc6750 **[A]**
12. Jones, M., Bradley, J. and Sakimura, N. (2015) ‘JSON Web Token (JWT)’, RFC 7519, Internet Engineering Task Force, May 2015. https://www.rfc-editor.org/info/rfc7519 **[A]**
13. Kent, K. and Souppaya, M. (2006) ‘Guide to Computer Security Log Management’, NIST Special Publication 800-92, National Institute of Standards and Technology, Gaithersburg, MD, September 2006. https://doi.org/10.6028/NIST.SP.800-92 **[A]**
14. Krawczyk, H., Bellare, M. and Canetti, R. (1997) ‘HMAC: Keyed-Hashing for Message Authentication’, RFC 2104, Internet Engineering Task Force, February 1997. https://www.rfc-editor.org/info/rfc2104 **[A]**
15. Lewis, J. and Fowler, M. (2014) ‘Microservices: a definition of this new architectural term’, martinfowler.com, 25 March 2014. https://martinfowler.com/articles/microservices.html **[A]**
16. Lodderstedt, T., Bradley, J., Labunets, A. and Fett, D. (2025) ‘Best Current Practice for OAuth 2.0 Security’, RFC 9700 (BCP 240), Internet Engineering Task Force. https://www.rfc-editor.org/info/rfc9700 **[A]**
17. McKay, K. and Cooper, D. (2019) ‘Guidelines for the Selection, Configuration, and Use of Transport Layer Security (TLS) Implementations’, NIST Special Publication 800-52 Revision 2, National Institute of Standards and Technology, Gaithersburg, MD, August 2019. https://doi.org/10.6028/NIST.SP.800-52r2 **[A]**
18. MITRE Corporation (n.d.) ‘CWE-208: Observable Timing Discrepancy’, Common Weakness Enumeration. https://cwe.mitre.org/data/definitions/208.html (accessed 28 October 2026) **[A]**
19. MITRE Corporation (n.d.) ‘CWE-639: Authorization Bypass Through User-Controlled Key’, Common Weakness Enumeration. https://cwe.mitre.org/data/definitions/639.html (accessed 28 October 2026) **[A]**
20. MITRE Corporation (n.d.) ‘CWE-89: Improper Neutralization of Special Elements used in an SQL Command (‘SQL Injection’)’, Common Weakness Enumeration. https://cwe.mitre.org/data/definitions/89.html (accessed 28 October 2026) **[A]**
21. Moriarty, K. and Farrell, S. (2021) ‘Deprecating TLS 1.0 and TLS 1.1’, RFC 8996 (BCP 195), Internet Engineering Task Force. https://www.rfc-editor.org/info/rfc8996 **[A]**
22. National Security Agency (2021) ‘Embracing a Zero Trust Security Model’, Cybersecurity Information Sheet, Version 1.0, February 2021. https://media.defense.gov/2021/Feb/25/2002588479/-1/-1/0/CSI_EMBRACING_ZT_SECURITY_MODEL_UOO115131-21.PDF **[B]**
23. OWASP Foundation (2023) ‘OWASP API Security Top 10 – 2023’, OWASP API Security Project. https://api-security.owasp.org/editions/2023/en/0x11-t10 **[A]**
24. OWASP Foundation (2025) ‘OWASP Application Security Verification Standard (ASVS) Version 5.0.0’, released 30 May 2025. https://asvs.owasp.org/ **[A]**
25. OWASP Foundation (n.d.) ‘Authentication Cheat Sheet’, OWASP Cheat Sheet Series. https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html (accessed 28 October 2026) **[A]**
26. OWASP Foundation (n.d.) ‘SQL Injection Prevention Cheat Sheet’, OWASP Cheat Sheet Series. https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html (accessed 28 October 2026) **[A]**
27. Pereira-Vale, A., Fernandez, E.B., Monge, R., Astudillo, H. and Márquez, G. (2021) ‘Security in microservice-based systems: A multivocal literature review’, Computers & Security, Vol.103, Article 102200. https://doi.org/10.1016/j.cose.2021.102200 **[A]**
28. Provos, N. and Mazières, D. (1999) ‘A Future-Adaptable Password Scheme’, Proceedings of the 1999 USENIX Annual Technical Conference, Monterey, CA, pp.81-92. **[B]**
29. PRS Legislative Research (2023) ‘The Digital Personal Data Protection Bill, 2023’, PRS India, New Delhi. https://prsindia.org/billtrack/digital-personal-data-protection-bill-2023 (accessed 28 October 2026) **[A]**
30. Rescorla, E. (2018) ‘The Transport Layer Security (TLS) Protocol Version 1.3’, RFC 8446, Internet Engineering Task Force, August 2018 (since obsoleted by RFC 9846). https://www.rfc-editor.org/info/rfc8446 **[A]**
31. Rescorla, E. (2026) ‘The Transport Layer Security (TLS) Protocol Version 1.3’, RFC 9846, Internet Engineering Task Force (obsoletes RFC 8446 and RFC 5246). https://www.rfc-editor.org/info/rfc9846 **[A]**
32. Rose, S., Borchert, O., Mitchell, S. and Connelly, S. (2020) ‘Zero Trust Architecture’, NIST Special Publication 800-207, National Institute of Standards and Technology, Gaithersburg, MD, August 2020. https://doi.org/10.6028/NIST.SP.800-207 **[A]**
33. Sheffer, Y., Hardt, D. and Jones, M. (2020) ‘JSON Web Token Best Current Practices’, RFC 8725 (BCP 225), Internet Engineering Task Force. https://www.rfc-editor.org/info/rfc8725 **[A]**
34. Shostack, A. (2014) Threat Modeling: Designing for Security, John Wiley & Sons, Indianapolis, IN. ISBN 978-1-118-80999-0. **[B]**
35. Syverson, P. (1994) ‘A Taxonomy of Replay Attacks’, Proceedings of the 7th IEEE Computer Security Foundations Workshop, pp.187-191. **[B]**
36. Temoshok, D., Fenton, J., Choong, Y.-Y., Lefkovitz, N., Regenscheid, A., Galluzzo, R. and Richer, J. (2025) ‘Digital Identity Guidelines: Authentication and Authenticator Management’, NIST Special Publication 800-63B-4, National Institute of Standards and Technology, Gaithersburg, MD, July 2025. https://doi.org/10.6028/NIST.SP.800-63b-4 **[A]**
37. Ward, R. and Beyer, B. (2014) ‘BeyondCorp: A New Approach to Enterprise Security’, ;login:, Vol.39, No.6, pp.6-11. **[B]**

Note: RFC 8725, 8996, 9700 and 9846 are cited by year only, because the RFC Editor pages show the copyright year but not the month. The PRS Legislative Research page on the Digital Personal Data Protection Bill was added while the data-protection discussion was written.

## What each source will support (claim map, content to be re-checked at drafting)
| Topic in the report | Sources |
|---|---|
| Microservices and their security surface | Lewis & Fowler 2014; Dragoni et al. 2017; NIST SP 800-204, 800-204A |
| State of research on microservice security | Pereira-Vale et al. 2021; Hannousse & Yahiouche 2021 |
| Zero trust and perimeter-security failure | NIST SP 800-207; NSA 2021; Ward & Beyer 2014 |
| OAuth 2.0 and bearer tokens | RFC 6749, 6750, 9700 |
| JWT, `alg: none`, algorithm confusion | RFC 7519, RFC 8725 |
| HMAC request signing | RFC 2104; Bellare, Canetti & Krawczyk 1996 |
| Replay attacks and nonces | Syverson 1994 |
| TLS 1.3, deprecation of TLS 1.0/1.1, TLS configuration | RFC 9846 (and 8446), RFC 8996, NIST SP 800-52r2 |
| Key management and rotation | NIST SP 800-57 Part 1 Rev.5; HashiCorp Vault docs |
| Password hashing (bcrypt) | Provos & Mazières 1999 |
| Authentication hardening, enumeration, lockout | OWASP Authentication Cheat Sheet; NIST SP 800-63B-4 (content check pending); CWE-208; Brumley & Boneh 2003 |
| Broken object-level authorisation (BOLA/IDOR) | OWASP API Security Top 10 2023 (API1); CWE-639 |
| SQL injection and parameterised queries | Halfond et al. 2006 (pending); CWE-89; OWASP SQL Injection Prevention Cheat Sheet |
| Threat modelling (STRIDE) | Shostack 2014 |
| Verification standards | OWASP ASVS 5.0.0 |
| Logging and audit | NIST SP 800-92 |

## Open items
1. **Halfond, Viegas and Orso (2006) is level C.** Two independent search listings agree on authors, title and venue, but the author's PDF failed with a certificate error twice, and the exact venue title and page range are not confirmed. Default: keep it with no page range if I can open the PDF later, otherwise drop it. The SQL-injection discussion is already covered by CWE-89 and the OWASP cheat sheet.
2. **RFC 8446 is obsolete.** RFC 9846 (2026) replaces it and also obsoletes RFC 5246 (TLS 1.2). I will cite RFC 9846 as the current specification and mention RFC 8446 as the original 2018 publication.
3. **NIST SP 800-52r2** shows a "currently being reviewed" note; it is still the published revision.
4. **No month for RFC 8725, 8996, 9700, 9846:** the RFC Editor pages give the year only; I cite the year only.
5. **Chapter 2's "bibliometric analysis"** will be a small, clearly described count over this verified corpus (by type, year and topic). It will not claim to be a Scopus or Web of Science query, because I have no access to those.
6. The two multivocal and mapping reviews (Pereira-Vale; Hannousse) report their own corpus sizes (370 + 620 items screened to 70; 1,067 studies screened to 47). Those figures come from search-result abstracts, so I will re-read the abstracts before quoting them.
