# RAG Framework Comparison: LlamaIndex, Haystack, LangChain, and LlamaStack

## 1. Project Overview

This project compares four popular frameworks for building Retrieval-Augmented Generation (RAG) applications:

- LlamaIndex
- Haystack
- LangChain
- LlamaStack

The objective is to examine their architectures, core capabilities, retrieval approaches, extensibility, observability, and production-readiness considerations.

In addition to reviewing their features, the project implements a working RAG pipeline with each framework and evaluates their performance against the same DevOps knowledge corpus.

## 2. Project Objectives

The comparison focuses on:

- Document ingestion and preprocessing.
- Text chunking and embedding generation.
- Vector storage and retrieval.
- LLM integration and answer generation.
- Agent and tool capabilities.
- Observability and evaluation.
- Production-readiness considerations.

The practical experiment evaluates retrieval relevance, answer quality, successful execution, and end-to-end execution time.

## 3. Frameworks Compared

| Framework  | Version        |
| ---------- | -------------- |
| LlamaIndex | 0.14.25 (core) |
| Haystack   | 3.4.1          |
| LangChain  | 1.4.9          |
| LlamaStack | 0.2.19         |

Additional package versions are documented in `configs/framework-versions.json`.

## 4. Experimental Environment

The experiment uses:

| Component              | Configuration                            |
| ---------------------- | ---------------------------------------- |
| Python                 | 3.12.16                                  |
| LLM                    | Ollama `qwen2.5:3b`                      |
| Embedding model        | `sentence-transformers/all-MiniLM-L6-v2` |
| Embedding dimensions   | 384                                      |
| Vector storage         | FAISS and framework-specific stores      |
| Corpus                 | 10-page DevOps PDF                       |
| Chunk size             | 500 tokens                               |
| Chunk overlap          | 50 tokens                                |
| Retrieval top-k        | 4                                        |
| Evaluation questions   | 15                                       |
| Generation temperature | 0                                        |

Each framework uses the same preprocessed chunks and shared embeddings to maintain a controlled retrieval comparison.

## 5. Project Structure

```text
rag-framework-comparison/
│
├── .env.example
├── .gitignore
├── README.md
├── shared_ingestion.py
├── verify_corpus.py
├── the-process.md
├── feature-comparison-matrix.md
│
├── configs/
│   ├── framework-versions.json
│   ├── llamastack-build.yaml
│   ├── rag-config.json
│   └── settings.yaml
│
├── corpus/
│   └── devops-rag-corpus.pdf
│
├── evaluation/
│   ├── build_haystack_store.py
│   ├── build_langchain_store.py
│   ├── build_llamaindex_index.py
│   ├── create_answer_review.py
│   ├── evaluate_haystack.py
│   ├── evaluate_langchain.py
│   ├── evaluate_llamaindex.py
│   ├── evaluate_llamastack.py
│   ├── generate_embeddings.py
│   ├── insert_llamastack.py
│   ├── questions.json
│   ├── shared_chunks.json
│   ├── shared_embeddings.json
│   │
│   ├── run_haystack_rag.py
│   ├── run_langchain_rag.py
│   ├── run_llamaindex_rag.py
│   ├── run_llamastack_rag.py
│   │
│   ├── test_haystack_retrieval.py
│   ├── test_langchain_retrieval.py
│   ├── test_llamaindex_retrieval.py
│   │
│   ├── haystack_store.json
│   │
│   ├── vector_stores/
│   │   ├── langchain/
│   │   │   ├── index.faiss
│   │   │   └── index.pkl
│   │   │
│   │   └── llamaindex/
│   │       ├── default__vector_store.json
│   │       ├── docstore.json
│   │       ├── graph_store.json
│   │       ├── image__vector_store.json
│   │       └── index_store.json
│   │
│   └── results/
│       ├── answer-quality-review.md
│       ├── haystack-results.json
│       ├── langchain-results.json
│       ├── llamaindex-results.json
│       └── llamastack-results.json
│
├── reports/
│   └── benchmark-results.md
│
└── screenshots/
    ├── 01-project-structure.png
    ├── 02-corpus-verification.png
    ├── 03-shared-chunks.png
    ├── 04-embedding-generation.png
    ├── 05-llamaindex-implementation.png
    ├── 06-haystack-implementation.png
    ├── 07-langchain-implementation.png
    └── 08-llamastack-implementation.png
```

## 6. Evaluation Methodology

### 6.1 Corpus

A 10-page DevOps knowledge corpus was used, covering:

| Pages | Topic      |
| ----- | ---------- |
| 1–2   | Docker     |
| 3–4   | Kubernetes |
| 5–6   | Terraform  |
| 7–8   | AWS        |
| 9–10  | CI/CD      |

### 6.2 Shared preprocessing

The corpus was processed into chunks using the following configuration:

- Chunk size: 500 tokens.
- Chunk overlap: 50 tokens.
- Embedding model: `all-MiniLM-L6-v2`.
- Embedding dimensions: 384.
- Shared evaluation questions: 15.

The generated chunks and embeddings were reused across the four framework implementations.

### 6.3 Evaluation process

Each framework was evaluated using the same 15 questions.

The experiment measured:

1. Successful question processing.
2. Number of retrieved chunks.
3. Topic-page retrieval precision.
4. Topic-page hit rate.
5. Generated answer quality.
6. Average end-to-end execution time.

Answer quality was manually assessed using four dimensions:

- Correctness.
- Completeness.
- Context grounding.
- Relevance.

Each dimension received a score from 0 to 2, giving a maximum of 8 points per question and 120 points per framework.

## 7. Benchmark Results

### 7.1 Overall results

| Metric                      | LlamaIndex |   Haystack |  LangChain | LlamaStack |
| --------------------------- | ---------: | ---------: | ---------: | ---------: |
| Successful evaluations      |      15/15 |      15/15 |      15/15 |      15/15 |
| Average execution time      | 343.56 sec | 292.28 sec | 272.69 sec | 194.87 sec |
| Total execution time        |  85.89 min |  73.07 min |  68.17 min |  48.72 min |
| Average retrieved chunks    |          4 |          4 |          4 |          3 |
| Topic-page precision        |     55.00% |     55.00% |     55.00% |     62.22% |
| Topic-page hit rate         |       100% |       100% |       100% |     93.33% |
| Manual answer-quality score |     83.33% |     83.33% |     83.33% |     84.17% |

### 7.2 Key observations

- All four frameworks successfully completed the 15-question evaluation.
- LlamaStack recorded the lowest average end-to-end execution time in this experiment.
- LlamaIndex, Haystack, and LangChain achieved a 100% topic-page hit rate.
- LlamaStack recorded the highest topic-page precision, but returned three chunks rather than the configured four.
- LlamaStack achieved the highest manual answer-quality score, although the differences between frameworks were small.

The execution-time measurements include retrieval and generation. They are not isolated measurements of framework overhead.

## 8. Framework Decision Guide

| Requirement                                   | Recommended framework    |
| --------------------------------------------- | ------------------------ |
| Document-heavy RAG applications               | LlamaIndex               |
| Modular and structured RAG pipelines          | Haystack                 |
| Broad LLM integrations and agent applications | LangChain                |
| Advanced agent orchestration                  | LangChain with LangGraph |
| Standardized AI infrastructure APIs           | LlamaStack               |

The appropriate framework depends on the application's architecture, infrastructure, integration requirements, and operational needs. The benchmark results should be considered alongside these requirements rather than used as a universal ranking.

## 9. Limitations

The experiment has several limitations:

- The corpus contains only 10 pages.
- The evaluation uses 15 questions.
- Execution times are from individual runs and may be affected by model warmup, CPU utilization, and server conditions.
- LlamaStack returned fewer chunks than the other frameworks, affecting direct retrieval comparisons.
- Answer quality was assessed manually and is not a standardized evaluation metric.
- Production-scale concurrency, high availability, security, and disaster recovery were outside the scope of the initial benchmark. These areas were subsequently investigated in Phase 2 through production-readiness engineering. The results and limitations are documented in Section 13.
- Native ingestion and chunking capabilities were reviewed but not independently benchmarked because shared preprocessing was used.

The results should therefore be interpreted as a controlled, small-scale comparison.

## 10. Running the Implementations

The project uses separate Python virtual environments for the frameworks.

The implementation and evaluation scripts are located in `evaluation/`.

The general execution order is:

1. Generate shared embeddings.
2. Build or populate each framework's vector store.
3. Run retrieval tests.
4. Run individual RAG pipeline tests.
5. Execute the batch evaluation scripts.
6. Review the generated results.

The relevant scripts are:

| Framework  | Store/index setup           | Retrieval test                                 | RAG execution           | Evaluation               |
| ---------- | --------------------------- | ---------------------------------------------- | ----------------------- | ------------------------ |
| LlamaIndex | `build_llamaindex_index.py` | `test_llamaindex_retrieval.py`                 | `run_llamaindex_rag.py` | `evaluate_llamaindex.py` |
| Haystack   | `build_haystack_store.py`   | `test_haystack_retrieval.py`                   | `run_haystack_rag.py`   | `evaluate_haystack.py`   |
| LangChain  | `build_langchain_store.py`  | `test_langchain_retrieval.py`                  | `run_langchain_rag.py`  | `evaluate_langchain.py`  |
| LlamaStack | `insert_llamastack.py`      | Verified through its retrieval and RAG scripts | `run_llamastack_rag.py` | `evaluate_llamastack.py` |

LlamaStack additionally requires its server and Ollama service to be running before executing its API-dependent scripts.

Refer to `the-process.md` for the detailed setup and implementation history.

## 11. Project Documentation

The following documents provide additional information about the project's implementation, evaluation, and findings.

- [`feature-comparison-matrix.md`](feature-comparison-matrix.md) — framework capabilities, production readiness, and decision guide.
- [`reports/benchmark-results.md`](reports/benchmark-results.md) — benchmark findings and performance results.
- [`Final Evaluation Report`](production/final-evaluation.md) — consolidated evaluation of the initial framework benchmark and Phase 2 production-readiness engineering.
- [`evaluation/results/answer-quality-review.md`](evaluation/results/answer-quality-review.md) — manual answer-quality assessment.
- [`the-process.md`](the-process.md) — project implementation process.
- [`configs/rag-config.json`](configs/rag-config.json) — shared experiment configuration.
- [`configs/framework-versions.json`](configs/framework-versions.json) — framework version information.

## 12. Conclusion

This project demonstrates that LlamaIndex, Haystack, LangChain, and LlamaStack can each support a functional RAG implementation using a shared corpus and evaluation setup.

Although their benchmark results were relatively close in answer quality, their architectures and operational approaches differ.

The experiment highlights the importance of evaluating RAG frameworks not only by their ability to generate answers but also by retrieval quality, integration flexibility, observability, execution behavior, and production requirements.

---

## 13. Phase 2: Production-Readiness Engineering

Following the framework benchmark, the project was extended to investigate the production-readiness requirements of a RAG application.

The second phase uses the LangChain implementation to build and test a containerized RAG API with security, scalability, availability, and recovery controls.

### Development Workflow: Automatic Code Reloading

The project includes a separate Docker Compose override for development.

This enables Uvicorn's automatic reload feature, so changes to Python source files are detected and the API process restarts automatically without recreating containers.

**Start development mode:**

```bash
docker compose -f production/docker-compose.yml \
 -f production/docker-compose.dev.yml \
 up -d --scale rag-api=2 rag-api
```

**View API logs:**

```bash
docker compose -f production/docker-compose.yml \
 -f production/docker-compose.dev.yml \
 logs -f rag-api
```

**Stop development mode:**

```bash
docker compose -f production/docker-compose.yml \
 -f production/docker-compose.dev.yml \
 down
```

**Note:** Automatic reload applies to Python source-code changes. Changes to dependencies, Dockerfiles, or environment configuration may require rebuilding or recreating containers. The development override should not be used as the production deployment configuration.

### 13.1 Production Architecture

The production implementation uses:

| Component               | Technology          |
| ----------------------- | ------------------- |
| API framework           | FastAPI             |
| RAG framework           | LangChain           |
| LLM                     | Ollama – qwen2.5:3b |
| Embedding model         | all-MiniLM-L6-v2    |
| Vector database         | FAISS               |
| Containerization        | Docker              |
| Container orchestration | Docker Compose      |
| Reverse proxy           | Nginx               |
| Rate-limit storage      | Redis               |
| Load testing            | Locust              |
| Transport security      | HTTPS/TLS           |

Architecture:

Client → Nginx → FastAPI Replicas → LangChain RAG Pipeline → FAISS / Ollama

Redis provides shared rate-limit storage across API replicas.

### 13.2 API Implementation

A REST API was implemented using FastAPI.

| Endpoint        | Method | Purpose                               |
| --------------- | ------ | ------------------------------------- |
| `/health`       | GET    | Application health status             |
| `/api/v1/query` | POST   | Submit a question to the RAG pipeline |

The query endpoint returns the generated answer, retrieved source documents, and retrieval, generation, and total execution times.

### 13.3 Docker Deployment

The API was containerized using Docker and deployed through Docker Compose.

The deployment includes:

- FastAPI application containers.
- Nginx reverse proxy.
- Redis rate-limit storage.
- Connection to the host-based Ollama inference service.
- Mounted FAISS vector-store files.

The API successfully loaded the vector store and LLM client and processed an end-to-end RAG query.

### 13.4 Concurrency and Load Testing

Locust was used to evaluate API behaviour under concurrent requests.

An `asyncio.Semaphore(1)` was introduced to limit active LLM generation to one request per API process.

The tests recorded zero failed requests in the small samples completed. However, average query latency remained high, primarily because inference was performed on CPU-based hardware.

The results do not establish production-scale throughput or sustainable concurrency.

### 13.5 High Availability and Failover

Two FastAPI replicas were deployed behind Nginx.

A failover test was performed by stopping one API replica while sending health-check requests through the reverse proxy.

Nginx successfully routed requests to the surviving replica. The stopped replica was subsequently restored, and both replicas returned to a healthy state.

This demonstrates basic application-level failover within a single Docker host.

### 13.6 Security and Container Hardening

The following security controls were implemented and tested:

- API-key authentication using the `X-API-Key` header.
- Secure API-key comparison using `secrets.compare_digest()`.
- Redis-backed rate limiting.
- Request validation using Pydantic.
- Environment-based secret configuration.
- CORS restrictions.
- HTTPS/TLS through Nginx.
- Nginx security response headers.
- Redis authentication.
- Non-root API container execution.
- Docker capability restrictions and `no-new-privileges`.
- Container CPU and memory resource limits.
- Read-only mounts for the vector store and application source.

The query endpoint is configured for five requests per minute. The shared Redis rate-limiting mechanism was verified, although the query endpoint's six-request limit was not independently tested.

### 13.7 Disaster Recovery

A timestamped FAISS backup procedure was implemented using a Bash script.

The recovery process includes:

- Copying the FAISS index and document metadata.
- Generating SHA-256 checksums.
- Verifying backup integrity.
- Restoring the files into an isolated directory.
- Loading the restored index using LangChain.
- Retaining the five most recent timestamped backups.

The restoration test successfully loaded all 20 indexed documents.

The retention cleanup logic was also tested successfully.

Backups currently reside on the same machine as the application. Off-site storage and automated backup scheduling remain outstanding improvements.

### 13.8 Production-Readiness Assessment

| Area                        | Observed status                       |
| --------------------------- | ------------------------------------- |
| REST API implementation     | Completed                             |
| Docker containerization     | Tested                                |
| Nginx reverse proxy         | Tested                                |
| HTTPS/TLS                   | Tested with a self-signed certificate |
| Concurrent request handling | Initial testing completed             |
| Multiple API replicas       | Tested                                |
| Single-replica failover     | Passed                                |
| API authentication          | Verified                              |
| Redis-backed rate limiting  | Verified                              |
| Request validation          | Verified                              |
| Container hardening         | Verified                              |
| Resource limits             | Verified                              |
| Backup creation             | Passed                                |
| Backup restoration          | Passed                                |
| Backup retention            | Passed                                |

### 13.9 Production Limitations

The production-readiness experiment has several limitations:

1. CPU-based inference results in very high response latency.
2. Both API replicas share the same Docker host and Ollama service.
3. The TLS certificate is self-signed and is not suitable as a publicly trusted production certificate.
4. Backup storage remains on the same machine as the application.
5. Automated backup scheduling and off-site storage have not been implemented.

### 13.10 Phase 2 Conclusion

The second phase extended the original RAG benchmark into a containerized API deployment with multiple application replicas, reverse-proxy routing, authentication, rate limiting, container hardening, and disaster recovery procedures.

The experiments demonstrated successful API deployment, basic application-level failover, security-control operation, and successful FAISS restoration.

The project therefore provides a practical foundation for production-oriented RAG engineering while identifying the additional work required for a more resilient deployment.

**Phase 2 status:** Core implementation and documented tests completed, with further operational improvements identified.
