@appendix 1 | USER MANUAL: SECURE API WEB APPLICATION

This manual takes a reader from an empty machine to a running, tested system. The commands are the ones used to produce the results in Chapter 4. Run them in a terminal on macOS or Linux.

## A1.1 What you need

- **Docker** with Docker Compose (the test machine used Docker Engine 29.8.0 and Compose v5.5.1), with the Docker daemon running.
- **Python 3** with `pip`, **curl** and **openssl** on the command line.
- About 4 GB of free disk space for container images.
- These local ports free: 3000, 3001, 3100, 4000, 5173, 6379, 8000 and 8200.
- A web browser. Playwright is not needed to use the system; it was used only to take the screenshots.

## A1.2 Generate certificates and keys

From the project's `infra` folder, run the generator. It creates a local certificate authority, one certificate for each of the three services, the JWT key pair, the HMAC key and a file with the database bootstrap passwords. It deletes any certificates already in `infra/certs`, so use it deliberately.

@code
cd infra
chmod +x scripts/*.sh
./scripts/gen-certs.sh
@endcode

## A1.3 Start Vault and load the secrets

Vault must be running before the other services, because they read their secrets from it as they start. The second command writes the JWT keys, the HMAC key and the database credentials into Vault and then deletes the local copies.

@code
docker compose up -d vault
./scripts/vault-init.sh
@endcode

## A1.4 Start everything else

@code
docker compose up --build -d
docker compose ps
@endcode

The first start builds four images and takes a minute or two. When it has finished, `docker compose ps` should show the Gateway, Auth Server, Resource Service, PostgreSQL, Redis and Vault as healthy and the other four containers as running.

## A1.5 Try the API with curl

Log in as the standard user and keep the access token in a shell variable. The demonstration usernames are `naytik` (read and write), `rishi` (read only) and `admin` (read, write and administration). Their demonstration passwords are listed in the project's README and on the sign-in page; they are not reproduced in this report.

@code
CA=certs/ca.crt
TOKEN=$(curl -s --cacert $CA -X POST https://localhost:4000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"naytik","password":"<demo password>"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl --cacert $CA -X POST https://localhost:3000/orders \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"item":"Mechanical Keyboard","quantity":1}'

curl --cacert $CA https://localhost:3000/orders -H "Authorization: Bearer $TOKEN"
@endcode

A request from the read-only user to create an order returns HTTP 403, which shows that the permission is enforced by the server. The captured output of this sequence is shown in {fig:flowa} and {fig:flowb}.

## A1.6 Open the dashboard

Open `http://localhost:5173` in a browser. The services use certificates from the local authority, so the browser will warn about them the first time. Either open `https://localhost:3000/health` once and accept the warning, or add `infra/certs/ca.crt` to the browser's trusted authorities. {fig:a1login} shows the sign-in page.

@figure a1login | screens/S01-login-screen.png | 9 | Sign-in page of the dashboard (credential note cropped out)

Sign in as `admin` to see the Security Operations Dashboard ({fig:a1admin}). The top row shows request metrics. The live request feed lists allowed and denied requests as they happen. The denies-only list shows rejected tokens and blocked requests. The three buttons under Attack Simulation make real requests with a forged token, a tampered token and a rapid burst, and the results appear in the feed within about a second. The Attack History panel shows the last report posted by the attacker toolkit.

@figure a1admin | screens/S03-admin-dashboard-before-attacks.png | 15 | Administrator's Security Operations Dashboard

Sign in as `naytik` to see the customer view ({fig:a1user}). Type an item name and a quantity and press Create Order; the order appears in the list, and the Delete button removes it. Signing in as `rishi` shows a read-only page with no creation form.

@figure a1user | screens/S06-readwrite-user-orders-view-empty.png | 15 | Customer view for a user with read and write permission

## A1.7 Run the attacker toolkit

Two of the scripts need a key that the secrets script has moved into Vault. Give the runner a Vault token that is allowed to read those two secrets (the development token is in `docker-compose.yml`) and it fetches the keys itself.

@code
cd attacker-toolkit
pip install -r requirements.txt
export VAULT_TOKEN=<development token from docker-compose.yml>
python3 run_all.py
@endcode

All five scripts should pass, 28 checks in total, and the runner exits with code 0. The results appear in the dashboard's Attack History panel within ten seconds.

Without a token the replay check and the algorithm-confusion check cannot run. They are reported as SKIP, nothing is counted as a pass that did not run, and the runner exits with code 2. The scripts run in a fixed order with the brute-force script last, because it deliberately locks out the address it attacks. To run one script alone, for example `python3 attack_injection.py`, make sure that address is not locked out (see the troubleshooting table).

## A1.8 View the logs in Grafana

Open `http://localhost:3001`. The "Secure API Platform - Security Overview" dashboard is provisioned automatically. At the time of this report only its rate-limit panel works as shipped (Section 4.5.6). To see raw log lines, use the Explore view with the Loki data source and the query `{service="gateway"}`.

## A1.9 Rotate the HMAC key

@code
./scripts/rotate-hmac-key.sh
docker compose restart gateway resource-service
@endcode

The script writes a new version of the key into Vault. Both services must be restarted to pick it up. After the restart, a request signed with the old key is refused with HTTP 401.

## A1.10 Stop the system

@code
docker compose down        # stops the containers and keeps the database volume
docker compose down -v     # also deletes the database volume for a completely fresh start
@endcode

## A1.11 Troubleshooting

{tab:trouble} lists the problems met while preparing this report and the usual remedies.

@table trouble | Common problems and remedies | 2.6,3,4.4
| Symptom | Likely cause | Remedy |
| --- | --- | --- |
| Compose stops with a message to run the certificate script first | The `infra/.env` file with database passwords does not exist | Run `./scripts/gen-certs.sh` |
| Cannot connect to the Docker daemon | Docker Desktop is not running | Start Docker and repeat the command |
| Login returns "Too many attempts" (HTTP 429) | More than ten login or refresh calls in one minute from your address | Wait one minute |
| Login returns "account locked" (HTTP 423) | Five wrong passwords for that username from this address | Wait 15 minutes, or restart the Auth Server. Other addresses are not affected |
| The browser shows a certificate warning, or dashboard calls fail | The certificates come from a local authority your browser does not trust | Open `https://localhost:3000/health` once and accept it, or trust `infra/certs/ca.crt` |
| A service exits at start with a Vault error | Vault was not running or had no secrets when the service started | Start Vault, run `./scripts/vault-init.sh`, then restart the three services |
| Vault has lost its secrets after a restart | Development-mode Vault keeps data in memory, and the script removed the local key files | Run `./scripts/gen-certs.sh` again, then `./scripts/vault-init.sh`, then restart the services (this recovery path was not exercised for this report) |
| A port is already in use | Another program uses 3000, 3001, 3100, 4000, 5173, 6379, 8000 or 8200 | Stop that program or change the published port in the Compose file |
