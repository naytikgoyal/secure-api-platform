@appendix 3 | KEY CODE EXCERPTS: SECURE API WEB APPLICATION

The excerpts below are copied unchanged from the repository, and each caption gives the file and line range. They are the parts of the code on which the security argument of Chapter 3 depends most directly.

## A3.1 Signing a request (Gateway)

The signer builds the canonical message from the upper-case method, the request target, the body, the timestamp and a random nonce, and returns the HMAC-SHA256 signature in hexadecimal ({fig:signjs}).

@codefile signjs | gateway/src/sign.js | 10 | 18 | Request signing in the Gateway

## A3.2 Verifying a signature (Resource Service)

The verifier checks the time window first and then compares the expected and provided signatures with a constant-time function ({fig:signingpy}). Nonce uniqueness is checked afterwards by the nonce store, so that no store write is spent on a forged request.

@codefile signingpy | resource-service/signing.py | 31 | 66 | Signature verification in the Resource Service

## A3.3 Reserving a nonce

The nonce is stored with one atomic Redis command that sets the key only if it does not exist and gives it an expiry. Two requests racing on the same nonce cannot both succeed ({fig:noncepy}).

@codefile noncepy | resource-service/nonce_store.py | 28 | 33 | Atomic nonce reservation

## A3.4 Account lockout

The lockout counts failures for each pair of username and source address, including usernames that do not exist ({fig:lockoutcode}). It also keeps an account-wide count across all addresses, which only raises a warning. A lock expires when its time has passed ({fig:lockoutcheck}).

@codefile lockoutcode | auth-server/src/accountLockout.js | 56 | 77 | Recording a failed login: per-source lock and account-wide count

@codefile lockoutcheck | auth-server/src/accountLockout.js | 85 | 96 | Checking whether a source is locked out of an account

## A3.5 Least-privilege database role

The role used by the Resource Service is created by this block when the database is first initialised. The password is passed to the client as a variable, not pasted into the SQL text ({fig:rolescript}).

@codefile rolescript | infra/postgres-init/01-create-app-role.sh | 36 | 42 | Creation of the application database role

## A3.6 One password comparison for every login

When the username does not exist, the submitted password is compared with a hash of a random value, so an unknown name costs the same time as a known one ({fig:authenticate}). This is the fix for finding D-01.

@codefile authenticate | auth-server/src/users.js | 40 | 56 | Authentication with one bcrypt comparison whatever the username
