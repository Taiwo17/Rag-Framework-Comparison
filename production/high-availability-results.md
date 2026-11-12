# High Availability and Failover Test Results

## 1. Objective

Evaluate whether the RAG API can remain available when one API replica becomes unavailable.

The experiment uses Docker Compose to run multiple API replicas and Nginx as a reverse proxy.

## 2. Architecture

- **API:** FastAPI with LangChain
- **Containerization:** Docker
- **Orchestration:** Docker Compose
- **Reverse Proxy:** Nginx
- **LLM:** Ollama running qwen2.5:3b
- **Replicas:** Two API containers

Architecture:

Client → Nginx → RAG API Replicas → Ollama

## 3. Test Environment

Two API replicas were deployed:

- production-rag-api-1
- production-rag-api-2

Nginx exposed the application through port 8080.

Both API replicas successfully passed their Docker health checks.

## 4. Failover Test

### Initial State

Both API replicas were running and healthy.

Five consecutive health-check requests through Nginx returned HTTP 200 OK.

### Failure Simulation

The first API replica was deliberately stopped:

```bash
docker stop production-rag-api-1
```

A subsequent request was sent through Nginx:

```bash
curl -i http://localhost:8080/health
```

### Observed Result

- HTTP status: 200 OK
- API status: healthy
- Vector store: loaded
- LLM: loaded

Nginx successfully routed the request to the surviving API replica.

## 5. Recovery Test

The stopped replica was restored using:

```bash
docker compose -f production/docker-compose.yml up -d --scale rag-api=2
```

Both API replicas returned to a healthy state without taking down the surviving replica.

## 6. Results Summary

| Test                      | Result |
| ------------------------- | ------ |
| Deploy two API replicas   | Passed |
| API health checks         | Passed |
| Nginx reverse proxy       | Passed |
| Stop one API replica      | Passed |
| Continue serving requests | Passed |
| Restore stopped replica   | Passed |

## 7. Limitations

This experiment demonstrates basic single-replica fault tolerance.

However:

- Both replicas run on the same Docker host.
- Both depend on the same Ollama inference service.
- The experiment does not demonstrate host-level failure recovery.
- Database or vector-store replication was not implemented.
- Large-scale concurrent failover was not tested.
- No distributed orchestration platform was used.

Therefore, this experiment should not be interpreted as proof of complete production-grade high availability.

## 8. Conclusion

The experiment demonstrated that the RAG API can continue serving health-check requests through Nginx when one API replica becomes unavailable.

The stopped replica was also successfully restored while the surviving replica remained operational.

This provides evidence of basic application-level fault tolerance within the Docker Compose deployment.
