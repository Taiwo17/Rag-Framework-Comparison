# TLS Certificate Setup

This project uses Nginx as a reverse proxy in front of the Springer Capital RAG API. TLS encrypts HTTPS connections between clients and the Nginx server.

For local development, the project uses a self-signed TLS certificate generated with OpenSSL.

## 1. Prerequisites

You need:

- OpenSSL installed.
- Docker and Docker Compose.
- The production Nginx configuration.
- Access to the project root directory.

Check your OpenSSL installation:

```bash
openssl version
```

The version used during project verification was OpenSSL 3.5.5.

## 2. Certificate and key locations

The project expects these files:

```text
production/
└── nginx/
    ├── nginx.conf
    └── certs/
        ├── server.crt
        └── server.key
```

- `server.crt` contains the public certificate.
- `server.key` contains the private key.

The Nginx configuration references these container paths:

```nginx
ssl_certificate /etc/nginx/certs/server.crt;
ssl_certificate_key /etc/nginx/certs/server.key;
```

Docker Compose mounts the certificate directory into the Nginx container as read-only:

```yaml
volumes:
  - ./nginx/certs:/etc/nginx/certs:ro
```

The `:ro` option prevents the container from modifying the host certificate files.

## 3. Generate a self-signed certificate

Run the following commands from the project root:

```bash
mkdir -p production/nginx/certs

umask 077

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout production/nginx/certs/server.key \
  -out production/nginx/certs/server.crt \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

chmod 600 production/nginx/certs/server.key
chmod 644 production/nginx/certs/server.crt
```

The command creates:

- A 2048-bit RSA private key.
- A self-signed X.509 certificate.
- A certificate valid for 365 days.
- A subject identifying `localhost`.
- Subject Alternative Names for `localhost` and `127.0.0.1`.

The `-nodes` option generates an unencrypted private key so Nginx can start without requesting a passphrase.

**Warning:** These commands overwrite existing files with the same names. Back up your existing certificate and key before regenerating them.

## 4. Protect private keys

Never commit private TLS keys to Git.

The project `.gitignore` includes:

```gitignore
# TLS certificates and private keys
production/nginx/certs/
```

Check that Git ignores the certificate directory:

```bash
git check-ignore -v production/nginx/certs/server.crt
git check-ignore -v production/nginx/certs/server.key
```

Both files should be reported as ignored.

Restrict private-key permissions:

```bash
chmod 600 production/nginx/certs/server.key
```

Keep the private key secure. Anyone who obtains it may be able to impersonate the server when using the corresponding certificate.

## 5. Inspect the certificate

Display the certificate subject, issuer, validity dates, and SAN:

```bash
openssl x509 \
  -in production/nginx/certs/server.crt \
  -noout -subject -issuer -dates -ext subjectAltName
```

Check the certificate's expiry:

```bash
openssl x509 \
  -in production/nginx/certs/server.crt \
  -noout -enddate
```

Check whether it expires within the next 30 days:

```bash
openssl x509 \
  -in production/nginx/certs/server.crt \
  -checkend 2592000 \
  -noout
```

A successful check reports that the certificate will not expire within the specified period.

## 6. Verify the certificate and private key match

Extract the public key from the certificate and calculate its SHA-256 hash:

```bash
openssl x509 \
  -in production/nginx/certs/server.crt \
  -pubkey -noout |
  openssl pkey -pubin -outform DER |
  sha256sum
```

Calculate the hash of the public key derived from the private key:

```bash
openssl pkey \
  -in production/nginx/certs/server.key \
  -pubout -outform DER |
  sha256sum
```

Both hashes must match. Different hashes indicate that the certificate and private key do not belong together.

## 7. Verify the self-signed certificate

Run:

```bash
openssl verify \
  -CAfile production/nginx/certs/server.crt \
  production/nginx/certs/server.crt
```

For the project's self-signed certificate, the expected result is:

```text
production/nginx/certs/server.crt: OK
```

This verifies the certificate against itself. It does not make the certificate trusted by browsers or external clients.

## 8. Configure Nginx for HTTPS

The project's Nginx TLS configuration includes:

```nginx
server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
}
```

The configuration enables TLS 1.2 and TLS 1.3.

The HTTP server listens on port 80 and redirects requests to HTTPS:

```nginx
server {
    listen 80;
    server_name localhost;

    return 301 https://$host:8443$request_uri;
}
```

The project maps container port 443 to host port 8443 and container port 80 to host port 8080.

## 9. Start and test the services

Start the production stack:

```bash
docker compose -f production/docker-compose.yml up -d
```

Check the services:

```bash
docker compose -f production/docker-compose.yml ps
```

Test the HTTPS health endpoint using GET:

```bash
curl -k -i https://localhost:8443/health
```

The expected response is:

```text
HTTP/1.1 200 OK
```

The API should return a JSON health response.

Test the HTTP-to-HTTPS redirect:

```bash
curl -I http://localhost:8080/health
```

The expected response is:

```text
HTTP/1.1 301 Moved Permanently
```

The `Location` header should point to:

```text
https://localhost:8443/health
```

The `-k` option in the HTTPS test tells curl to accept the self-signed certificate without normal certificate-authority verification.

## 10. Self-signed certificates versus public production certificates

Self-signed certificates are useful for:

- Local development.
- Internal testing.
- Demonstrating HTTPS configuration.
- Testing reverse-proxy TLS termination.

They are not suitable as publicly trusted certificates for a production website.

For a public deployment, use a certificate issued by a trusted Certificate Authority, such as Let's Encrypt, and configure the certificate for your actual domain name.

A public certificate must include the domain in its Subject Alternative Names. The private key must remain protected, and certificate renewal must be configured and tested.

## 11. Verified project configuration

The certificate inspected during project verification had:

| Property                 | Verified value                  |
| ------------------------ | ------------------------------- |
| Subject                  | `CN=localhost`                  |
| Issuer                   | `CN=localhost`                  |
| Valid from               | 11 November 2026                |
| Expires                  | 11 November 2027                |
| SAN                      | `DNS:localhost`, `IP:127.0.0.1` |
| Key type                 | RSA                             |
| Certificate/key match    | Passed                          |
| Self-signed verification | Passed                          |

The certificate and private key produced identical SHA-256 hashes when their public keys were extracted.

The HTTPS endpoint was reachable through Nginx. A HEAD request to `/health` returned HTTP 405 because the endpoint allows GET; use a GET request for the health-check test.
