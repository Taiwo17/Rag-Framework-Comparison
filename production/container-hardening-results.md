# Docker Container Hardening Results

## Objective

Reduce container privileges by running the RAG API under a dedicated non-root user.

## Implementation

- Created a dedicated Linux user named `appuser`.
- Assigned UID 10001.
- Updated the Dockerfile to use `USER appuser`.
- Applied appropriate ownership to application files.
- Preserved read-only mounting of the FAISS vector store.
- Rebuilt the API Docker image and recreated both replicas.

## Verification Results

| Test                      | Result                |
| ------------------------- | --------------------- |
| API container user        | UID 10001 (`appuser`) |
| API replica 1 health      | Healthy               |
| API replica 2 health      | Healthy               |
| FAISS vector store exists | Passed                |
| FAISS read permission     | Passed                |
| index.faiss accessible    | Passed                |
| index.pkl accessible      | Passed                |
| HTTPS health endpoint     | HTTP 200              |
| LLM loaded                | True                  |
| Vector store loaded       | True                  |

## Security Benefits

- Reduces reliance on root privileges.
- Limits the potential impact of application compromise.
- Maintains read-only access to retrieval data.
- Preserves API functionality after privilege reduction.

## Conclusion

The RAG API was successfully migrated from root execution to a dedicated non-root user. Both replicas remained healthy, and HTTPS, FAISS retrieval data access, and LLM initialization continued to function.
