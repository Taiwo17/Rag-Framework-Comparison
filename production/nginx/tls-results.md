# HTTPS/TLS Implementation and Test Results

## 1. Overview

HTTPS/TLS was configured to encrypt communication between clients and the Springer Capital RAG API.

Nginx acts as the TLS termination point and forwards incoming requests to the internal FastAPI service over the Docker network.

## 2. TLS Certificate Generation

A self-signed RSA 2048-bit certificate was generated using OpenSSL.

Certificate files:

- `production/nginx/certs/server.crt` — TLS certificate.
- `production/nginx/certs/server.key` — private key.

Certificate configuration:

- Common Name: localhost
- Subject Alternative Names: DNS:localhost, IP:127.0.0.1
- Validity: 365 days
- Key algorithm: RSA 2048-bit

The certificate is intended for local development and testing.

## 3. Nginx HTTPS Configuration

Nginx was configured to:

- Listen for HTTPS traffic on port 443 inside the container.
- Use the generated certificate and private key.
- Support TLS 1.2 and TLS 1.3.
- Forward requests to the `rag-api` service.
- Preserve relevant request headers.
- Redirect HTTP traffic to HTTPS.

Docker port mappings:

| Protocol | Host Port | Container Port |
| -------- | --------: | -------------: |
| HTTP     |      8080 |             80 |
| HTTPS    |      8443 |            443 |

The certificate directory is mounted into the Nginx container as read-only.

## 4. Test Results

### HTTPS Health Check

Command:

```bash
curl -k -i https://localhost:8443/health
```

Result:

- HTTP status: 200 OK
- API status: healthy
- Vector store: loaded
- LLM: loaded

Status: Passed

The `-k` option was used because the development certificate is self-signed and not issued by a trusted certificate authority.

### HTTP-to-HTTPS Redirect

Command:

```
curl -I http://localhost:8080/health
```

Result:

- HTTP status: 301 Moved Permanently
- Redirect destination: `https://localhost:8443/health`

Status: Passed

## 5. Deployment Architecture

The HTTPS request flow is:

1. Client sends an HTTPS request to Nginx on host port 8443.
2. Nginx terminates the TLS connection using the configured certificate.
3. Nginx forwards the request to the internal FastAPI service.
4. FastAPI processes the request.
5. Nginx returns the response over the encrypted HTTPS connection.

HTTP requests on port 8080 are redirected to HTTPS.

## 6. Security Considerations and Limitations

The current certificate is self-signed and intended only for local development.

Before public production deployment:

1. Obtain a trusted TLS certificate from a certificate authority, such as Let's Encrypt.
2. Configure a valid public domain name.
3. Automate certificate renewal.
4. Protect private keys with appropriate filesystem permissions and secret-management controls.
5. Review TLS configuration and security headers.
6. Consider encrypting internal service communication where deployment requirements demand it.

The current configuration provides HTTPS at the Nginx entry point. Communication between Nginx and the FastAPI containers remains HTTP within the Docker network.

## 7. Conclusion

HTTPS/TLS was successfully implemented at the Nginx reverse proxy.

Testing confirmed that HTTPS requests reach the RAG API successfully and that HTTP requests are redirected to HTTPS.

The implementation provides encrypted client-to-proxy communication for local development. A trusted certificate and additional production security controls are still required before public deployment.\
