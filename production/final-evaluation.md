# Springer Capital RAG Framework Comparison

## Final Evaluation and Production-Readiness Report

**Project:** Springer Capital Intern Project  
**Evaluation:** RAG Framework Benchmark and Phase 2 Production-Readiness Engineering  
**Status:** Implementation and core testing completed; final validation and operational improvements remain outstanding.

---

## 1. Executive Summary

This project evaluated four popular Retrieval-Augmented Generation (RAG) frameworks—LlamaIndex, Haystack, LangChain, and LlamaStack—using a shared dataset, embedding model, language model, and evaluation process.

The initial benchmark compared retrieval performance, response quality, and end-to-end execution time. All four frameworks completed the 15-question evaluation without reported failures.

LlamaStack recorded the shortest average end-to-end execution time and the highest measured topic-page precision. However, the results do not establish that it is universally the best framework. The benchmark used one local model, a small document collection, a limited question set, and a single local execution environment.

Phase 2 extended the project beyond framework comparison. It introduced a FastAPI service around the LangChain implementation, Docker containerization, Nginx reverse proxying, Redis-backed rate limiting, API-key authentication, container hardening, concurrency testing, replica failover testing, and backup and restoration procedures.

The project demonstrates practical production-readiness engineering and identifies the additional work required before a genuinely production-grade distributed deployment.

## 2. Project Objectives

The project had two primary objectives.

### Phase 1: RAG framework evaluation

- Compare LlamaIndex, Haystack, LangChain, and LlamaStack.
- Use consistent documents, chunks, embeddings, and evaluation questions.
- Measure retrieval relevance, answer quality, and execution time.
- Identify the trade-offs between the frameworks.

### Phase 2: Production-readiness engineering

- Expose the selected RAG implementation through a REST API.
- Containerize the application and its supporting services.
- Introduce authentication, rate limiting, and request validation.
- Test concurrent requests and application replica failover.
- Apply container and network security controls.
- Implement backup, integrity verification, and restoration procedures.
- Document test results, limitations, and future improvements.

## 3. Phase 1: Benchmark Methodology

### 3.1 Frameworks evaluated

| Framework  | Version |
| ---------- | ------: |
| LlamaIndex | 0.14.25 |
| Haystack   |   3.4.1 |
| LangChain  |   1.4.9 |
| LlamaStack |  0.2.19 |

### 3.2 Shared evaluation environment

The benchmark used the same core resources across the four implementations:

| Component                | Configuration                             |
| ------------------------ | ----------------------------------------- |
| Document collection      | 10-page DevOps PDF                        |
| Document topics          | Docker, Kubernetes, Terraform, AWS, CI/CD |
| Number of chunks         | 20                                        |
| Chunk size               | 500 tokens                                |
| Chunk overlap            | 50 tokens                                 |
| Shared embeddings        | 20                                        |
| Embedding dimensions     | 384                                       |
| Embedding model          | sentence-transformers/all-MiniLM-L6-v2    |
| Language model           | qwen2.5:3b                                |
| Model runtime            | Ollama                                    |
| Temperature              | 0                                         |
| Maximum generated tokens | 500                                       |
| Retrieval top-k          | 4                                         |
| Evaluation questions     | 15                                        |

The use of shared chunks, embeddings, and questions was intended to reduce differences caused by data preparation and evaluation inputs.

### 3.3 Evaluation metrics

The benchmark considered:

- **End-to-end execution time:** time taken to complete retrieval and response generation.
- **Topic-page precision:** relevance of retrieved source pages to the expected topic pages.
- **Topic-page hit rate:** how often expected topic pages appeared in the retrieved results.
- **Manual answer quality:** human assessment of the generated answers.
- **Evaluation completion:** whether the framework completed the evaluation questions without reported failures.

Execution time includes retrieval and language-model generation. It should not be interpreted as isolated framework overhead.

## 4. Phase 1: Benchmark Results

### 4.1 Performance comparison

| Framework  | Average end-to-end time | Topic-page precision | Topic-page hit rate | Manual answer quality | Completed |
| ---------- | ----------------------: | -------------------: | ------------------: | --------------------: | --------: |
| LlamaIndex |              343.56 sec |               55.00% |             100.00% |                83.33% |     15/15 |
| Haystack   |              292.28 sec |               55.00% |             100.00% |                83.33% |     15/15 |
| LangChain  |              272.69 sec |               55.00% |             100.00% |                83.33% |     15/15 |
| LlamaStack |              194.87 sec |               62.22% |              93.33% |                84.17% |     15/15 |

### 4.2 Interpretation

**Execution time**

LlamaStack recorded the shortest average end-to-end execution time at 194.87 seconds. LangChain followed at 272.69 seconds, Haystack at 292.28 seconds, and LlamaIndex at 343.56 seconds.

These measurements include local language-model generation, which is computationally expensive on the available CPU-only environment. They therefore reflect the combined system rather than the framework's retrieval overhead alone.

**Retrieval precision and hit rate**

LlamaStack achieved the highest topic-page precision at 62.22%, while the other frameworks recorded 55.00%.

LlamaIndex, Haystack, and LangChain achieved a 100% topic-page hit rate. LlamaStack recorded 93.33%.

An important qualification is that LlamaStack returned three chunks, while the other frameworks returned four. The difference in retrieved chunk counts affects the precision denominator and should be considered when interpreting the comparison.

**Answer quality**

Manual answer quality was close across all four implementations. LlamaStack recorded 84.17%, while the other frameworks each recorded 83.33%.

The small difference does not establish a statistically significant quality advantage.

### 4.3 Phase 1 conclusion

All four frameworks completed the benchmark successfully.

LlamaStack was the fastest implementation in this experiment and recorded the highest measured precision and manual answer quality. LangChain also performed competitively, with the second-shortest average execution time and a 100% topic-page hit rate.

The results support selecting LangChain as the implementation used for the subsequent API engineering work. This selection should be understood as a project implementation decision, not proof that LangChain is objectively superior to the alternatives.

## 5. Phase 2: Production Architecture

Phase 2 introduced a containerized service around the LangChain RAG implementation.

### 5.1 Architecture components

| Component             | Responsibility                             |
| --------------------- | ------------------------------------------ |
| FastAPI               | Exposes the RAG query and health endpoints |
| LangChain             | Handles retrieval and RAG orchestration    |
| FAISS                 | Stores and retrieves vector embeddings     |
| Sentence Transformers | Generates query embeddings                 |
| Ollama                | Runs the local language model              |
| Nginx                 | Reverse proxy and TLS termination          |
| Redis                 | Shared rate-limit storage                  |
| Docker Compose        | Runs and connects the application services |
| Locust                | Performs load and concurrency testing      |

### 5.2 Request flow

1. A client sends a query to the API through Nginx.
2. Nginx forwards the request to an available API replica.
3. The API validates the request and checks API-key authentication.
4. The query is embedded using the configured embedding model.
5. FAISS retrieves relevant document chunks.
6. LangChain constructs the RAG context.
7. Ollama generates the response.
8. The API returns the answer, source information, and execution timings.

### 5.3 API capabilities

The FastAPI service provides:

- `GET /health` for application health checks.
- `POST /api/v1/query` for authenticated RAG queries.
- Request validation and rejection of unexpected fields.
- Query-length and whitespace validation.
- Source-document metadata in responses.
- Retrieval, generation, and total execution-time measurements.
- Generic error responses for unexpected server errors, with internal details logged rather than exposed to clients.

The API uses API-key authentication through the `X-API-Key` header.

## 6. Deployment and Containerization

The application was containerized using Docker and deployed with Docker Compose.

The deployment includes:

- A FastAPI application container.
- An Nginx reverse proxy.
- A Redis service for shared rate-limit storage.
- Health checks and restart policies.
- Container resource limits and reservations.
- A non-root application user.
- Read-only mounts for selected application data and configuration.
- Dropped Linux capabilities and `no-new-privileges`.

The application image was built successfully, and the containers were brought up with healthy service status.

### 6.1 Development workflow

A separate `production/docker-compose.dev.yml` override enables Uvicorn automatic reload.

The development configuration watches Python source files and restarts the API process when changes are detected. This was verified by modifying the timestamp of `production/api/main.py` and observing WatchFiles detect the change and restart both application processes.

This development configuration is kept separate from the main deployment configuration.

### 6.2 TLS

Nginx was configured to redirect HTTP traffic to HTTPS and support TLS 1.2 and TLS 1.3.

The project used a self-signed certificate for local development and testing. This verifies the local TLS configuration but does not provide a publicly trusted certificate suitable for an internet-facing production deployment.

## 7. Concurrency and Load Testing

Locust was used to exercise the API and observe its behaviour under different request loads.

### 7.1 Health endpoint test

| Metric                |   Result |
| --------------------- | -------: |
| Total requests        |       35 |
| Failures              |        0 |
| Median response time  |     4 ms |
| Average response time | 18.11 ms |
| 95th percentile       |   170 ms |
| Maximum response time |   244 ms |

The health endpoint handled the test successfully without reported failures.

### 7.2 RAG query tests

| Test                          | Requests completed | Failures | Average response time |
| ----------------------------- | -----------------: | -------: | --------------------: |
| Initial one-user test         |                  5 |        0 |         477,396.93 ms |
| Initial two-user test         |                  4 |        0 |       1,192,410.55 ms |
| One-user test after semaphore |                  1 |        0 |         521,841.54 ms |
| Two-user test after semaphore |                  2 |        0 |         554,027.88 ms |

The initial two-user test showed substantial latency under concurrent generation.

A per-process `asyncio.Semaphore(1)` was subsequently introduced to limit active LLM generation within each API process. The later two-user test completed two requests with an average response time of approximately 9.2 minutes.

These results suggest that CPU-based local model inference is the dominant performance bottleneck.

### 7.3 Concurrency test limitations

The tests used small request counts and a local development environment. They do not establish production-scale throughput or capacity.

The semaphore is scoped to an individual API process. It does not coordinate generation globally across multiple replicas. Both replicas also use the same local Ollama service, which remains a shared bottleneck.

A larger test programme with sustained load, more users, and isolated inference infrastructure would be required for capacity planning.

## 8. High Availability and Replica Failover

The deployment was configured to run two API replicas behind Nginx.

A basic replica failover test was performed:

1. Both API replicas were confirmed healthy.
2. Requests were sent through Nginx.
3. One API replica was stopped.
4. Requests continued to receive successful health responses through the remaining replica.
5. The stopped replica was restored.
6. Both replicas returned to a healthy state.

The test demonstrated that Nginx could continue routing health requests when one API replica was unavailable.

### 8.1 High-availability limitations

Both replicas run on the same Docker host and depend on the same local Ollama instance and supporting infrastructure.

The implementation does not provide:

- Multi-host or multi-region failover.
- Distributed orchestration.
- Independent inference capacity.
- Automated infrastructure recovery across separate hosts.
- A demonstrated global generation-concurrency limit.

The result is basic application-level replica failover, not full infrastructure-level high availability.

## 9. Security and Container Hardening

Several security controls were implemented and tested.

### 9.1 API security

- API-key authentication using the `X-API-Key` header.
- Constant-time comparison for API-key verification.
- API keys stored in environment configuration rather than source code.
- SHA-256 hashing of API keys for rate-limit identity.
- Generic unexpected-error responses to avoid exposing internal exception details.
- Request validation, including rejection of extra fields and whitespace-only input.

### 9.2 Rate limiting

SlowAPI was configured with a limit of five requests per minute.

Redis provides shared rate-limit storage across the API replicas. A lightweight temporary test endpoint using the same authentication and limiter configuration returned HTTP 200 for the first five requests and HTTP 429 for the sixth.

The temporary test endpoint was removed after testing.

The query endpoint has its own five-per-minute limiter decorator. The lightweight test demonstrated the shared limiter backend and configuration, but did not directly exercise the query endpoint's rate limit through six completed RAG requests.

### 9.3 CORS and response headers

CORS was configured for the development frontend origins:

- `http://localhost:3000`
- `http://localhost:5173`

The allowed methods and headers were restricted to the requirements of the API.

Nginx was configured with the following security headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

CORS preflight behaviour and the configured security headers were tested.

### 9.4 Redis security

Redis is exposed only to the internal Docker network and requires password authentication.

Unauthenticated Redis access was rejected, while authenticated connectivity was verified.

### 9.5 Container hardening

The API container runs as a non-root user with UID 10001.

Additional controls include:

- `no-new-privileges`.
- Dropped Linux capabilities.
- Read-only mounts for selected files.
- Explicit CPU and memory limits and reservations.
- Health checks and restart policies.

### 9.6 Security limitations

The implementation provides useful baseline application and container controls, but it is not a complete security certification.

Further work should include dependency and image vulnerability scanning, secret-management integration, audit-log retention, penetration testing, and a production certificate from a trusted certificate authority.

The FAISS index is loaded using pickle-based deserialization. The index must therefore remain a trusted, integrity-protected project artifact; untrusted index files must not be loaded.

## 10. Disaster Recovery and Backup Testing

A backup script was implemented to copy the LangChain FAISS vector store into timestamped backup directories.

The script also:

- Generates SHA-256 checksums for the FAISS index files.
- Retains the five most recent timestamped backups.
- Removes older backups after the retention threshold is exceeded.

### 10.1 Backup verification

Backup creation was tested, and checksum verification was successful for the generated index files.

### 10.2 Restoration test

A restoration test was performed using a copied backup.

The restored FAISS files passed checksum verification, and the restored index was successfully loaded using the configured LangChain embedding setup.

The restored index contained 20 vectors.

### 10.3 Retention test

The retention logic was tested using six temporary backup directories. After applying the retention procedure, five remained. The temporary test directories were removed.

### 10.4 Disaster recovery limitations

The current backup process stores backups locally on the same host.

The following remain outstanding:

- Off-site or remote backup storage.
- Automated backup scheduling.
- Automated restoration testing.
- A documented recovery-time objective (RTO).
- A documented recovery-point objective (RPO).
- Recovery testing on a separate host.

The backup and restoration tests demonstrate local recovery capability, not protection against loss of the entire host or its storage.

## 11. Overall Evaluation

The project progressed from a comparative RAG framework experiment to a working containerized RAG API with supporting operational controls.

The initial benchmark established measurable differences across the four frameworks under a shared local evaluation setup.

Phase 2 demonstrated that the selected implementation could be exposed through a REST API, containerized, protected with authentication and rate limiting, placed behind a reverse proxy, tested under limited concurrent load, and recovered from a local vector-store backup.

The work also identified practical constraints that affect real-world deployment, especially CPU-bound local inference, shared infrastructure dependencies, and the distinction between application-level redundancy and infrastructure-level high availability.

## 12. Outstanding Work and Recommendations

The following improvements are recommended before deploying the service for external production use.

| Area                  | Outstanding improvement                                                |
| --------------------- | ---------------------------------------------------------------------- |
| Inference performance | Use dedicated inference hardware or a scalable inference service       |
| Concurrency           | Introduce distributed generation limits and conduct larger load tests  |
| High availability     | Deploy replicas across separate hosts with independent failure domains |
| Backups               | Add off-site storage and automated scheduling                          |
| Recovery              | Define RTO/RPO and test restoration on a separate host                 |
| TLS                   | Replace the self-signed certificate with a trusted public certificate  |
| Security              | Add image/dependency scanning and independent penetration testing      |
| Secrets               | Integrate a dedicated secrets-management solution                      |
| Observability         | Add centralized metrics, logs, dashboards, and alerting                |
| Deployment            | Introduce CI/CD, immutable image references, and rollback procedures   |
| Evaluation            | Expand the dataset, question set, and repeated benchmark runs          |

## 13. Conclusion

The Springer Capital RAG Framework Comparison project successfully evaluated four RAG frameworks and extended the selected implementation into a containerized API with practical production-readiness controls.

The benchmark showed that framework performance varies depending on retrieval behaviour, answer quality, and end-to-end execution time. LlamaStack achieved the shortest measured execution time in the experiment, while LangChain provided a competitive result and was selected for the subsequent implementation.

Phase 2 demonstrated API deployment, containerization, basic replica failover, request protection, container hardening, concurrency testing, and local disaster-recovery procedures.

The work should be regarded as a production-readiness engineering prototype rather than a fully production-grade distributed platform. Its documented limitations provide a clear path for further engineering and operational improvements.

---

## Appendix A: Supporting Project Evidence

The following project files provide supporting implementation details and test evidence:

- `reports/benchmark-results.md`
- `production/docker-deployment-results.md`
- `production/load-testing/concurrency-results.md`
- `production/high-availability-results.md`
- `production/security-results.md`
- `production/cors-results.md`
- `production/request-validation-results.md`
- `production/redis-security-results.md`
- `production/security-headers-results.md`
- `production/container-hardening-results.md`
- `production/container-resource-security-results.md`
- `production/infrastructure-resource-limits-results.md`
- `production/nginx/tls-results.md`
- `production/backup/disaster-recovery-results.md`

## Appendix B: Reproducibility and Interpretation Notes

1. Benchmark timing includes retrieval and generation and should not be interpreted as isolated framework execution overhead.
2. The benchmark used one local model and one small document collection.
3. The benchmark results represent one local experimental run, not a statistically repeated performance study.
4. Manual answer-quality scores should be interpreted as the evaluation's recorded human assessment.
5. Locust query tests used small sample sizes and do not establish production-scale capacity.
6. API replica failover was tested on one Docker host.
7. TLS testing used a self-signed certificate.
8. Local backup restoration does not establish off-site disaster recovery.
9. The API's generation semaphore is per process, not a distributed concurrency-control mechanism.
10. The project should be reassessed under a larger dataset, broader question set, repeated runs, and a production-like deployment environment before making general performance or availability claims.
