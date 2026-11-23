@uh ABBREVIATIONS AND SYMBOLS

**Abbreviations**

@table - | | 2,7
| Abbreviation | Full form |
| --- | --- |
| API | Application Programming Interface |
| BOLA | Broken Object Level Authorization |
| CA | Certificate Authority |
| CORS | Cross-Origin Resource Sharing |
| CSP | Content Security Policy |
| CWE | Common Weakness Enumeration |
| HMAC | Hash-based Message Authentication Code |
| HSTS | HTTP Strict Transport Security |
| HTTP / HTTPS | Hypertext Transfer Protocol / Secure |
| IDOR | Insecure Direct Object Reference |
| JSON | JavaScript Object Notation |
| JWT | JSON Web Token |
| KV | Key-Value (Vault secrets engine) |
| mTLS | Mutual Transport Layer Security |
| NIST | National Institute of Standards and Technology |
| OWASP | Open Worldwide Application Security Project |
| RFC | Request for Comments |
| RS256 | RSA signature with SHA-256 |
| SHA | Secure Hash Algorithm |
| SQL | Structured Query Language |
| SSE | Server-Sent Events |
| STRIDE | Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege |
| TLS | Transport Layer Security |
| TTL | Time To Live |
| UUID | Universally Unique Identifier |
| XSS | Cross-Site Scripting |

**Symbols used in the signing description**

@table - | | 2,7
| Symbol | Description |
| --- | --- |
| K | Shared HMAC secret key held in Vault |
| M | Canonical message: method, request target, body, timestamp and nonce joined by line feeds |
| σ | Signature, σ = HMAC-SHA256(K, M), written in hexadecimal |
| t | Unix timestamp (seconds) put in the request when it is signed |
| Δ | Allowed clock difference between signer and verifier (60 seconds) |
| n | Random 128-bit nonce, hexadecimal |
| T | Nonce retention time in Redis (300 seconds) |
