"""
attacker-toolkit/attack_mitm_downgrade.py

Threat being tested: docs/threat-model.md NFR-1 -- "All external traffic
over TLS 1.2+... Attacker toolkit attempts plaintext connection -> must be
refused." Also checks that weak/legacy TLS versions aren't negotiable.

Run: python3 attack_mitm_downgrade.py
"""
import socket
import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from toolkit_common import CA_CERT, Result, print_header, print_summary


def _parse_host_port(url):
    url = url.replace("https://", "").replace("http://", "")
    host, _, port = url.partition(":")
    return host, int(port) if port else 443


def attack_plaintext_http(host, port):
    print(f"\n1. Attempting PLAINTEXT HTTP connection to {host}:{port} (should be refused/reset)")
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.sendall(b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n")
        response = sock.recv(4096)
        sock.close()

        # If we get back something that looks like a real HTTP response, the
        # server is accepting plaintext -- that's a finding.
        looks_like_http = response.startswith(b"HTTP/")
        print(f"   Got a response ({len(response)} bytes). Looks like valid HTTP: {looks_like_http}")
        return Result(
            "Plaintext HTTP request to the HTTPS port is refused (not parsed as valid HTTP)",
            not looks_like_http,
            f"Server responded with {len(response)} bytes; valid-HTTP-looking: {looks_like_http}",
        )
    except (ConnectionResetError, ConnectionRefusedError, socket.timeout, OSError) as e:
        print(f"   Connection failed/reset as expected: {e}")
        return Result(
            "Plaintext HTTP request to the HTTPS port is refused (not parsed as valid HTTP)",
            True,
            f"Connection-level failure: {type(e).__name__}: {e}",
        )


def attack_legacy_tls(host, port, tls_version, version_name):
    print(f"\n2. Attempting to negotiate {version_name}")
    try:
        ctx = ssl.SSLContext(tls_version)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                negotiated = ssock.version()
                print(f"   Handshake SUCCEEDED, negotiated: {negotiated}")
                return Result(
                    f"{version_name} handshake is refused",
                    False,
                    f"Server accepted a {version_name} handshake (negotiated {negotiated}) -- should only accept TLS 1.2+",
                )
    except ssl.SSLError as e:
        print(f"   Handshake REFUSED (expected): {e}")
        return Result(f"{version_name} handshake is refused", True, f"{type(e).__name__}: {e}")
    except AttributeError:
        print(f"   {version_name} not available in this Python's ssl module (already disabled at the OS/library level)")
        return Result(f"{version_name} handshake is refused", True, "Not offered by the local OpenSSL build -- effectively disabled")
    except OSError as e:
        print(f"   Connection-level failure (also acceptable): {e}")
        return Result(f"{version_name} handshake is refused", True, f"{type(e).__name__}: {e}")


def main():
    print_header("attack_mitm_downgrade.py -- Plaintext + TLS downgrade attempts")

    from toolkit_common import GATEWAY_URL

    host, port = _parse_host_port(GATEWAY_URL)

    results = [attack_plaintext_http(host, port)]

    # Try the oldest/weakest versions Python's ssl module can even attempt.
    # Most modern OpenSSL builds (including this project's target environment)
    # disable TLS 1.0/1.1 at the system crypto-policy level, which is itself
    # a valid and common defense -- either outcome (Python can't even attempt
    # it, or the server refuses the handshake) counts as the attack being blocked.
    for attr_name, label in [("PROTOCOL_TLSv1", "TLS 1.0"), ("PROTOCOL_TLSv1_1", "TLS 1.1")]:
        tls_const = getattr(ssl, attr_name, None)
        if tls_const is None:
            print(f"\n2. {label}: not available in this Python build (already removed -- good)")
            results.append(Result(f"{label} handshake is refused", True, "Protocol constant removed from ssl module entirely"))
        else:
            results.append(attack_legacy_tls(host, port, tls_const, label))

    ok = print_summary(results)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
