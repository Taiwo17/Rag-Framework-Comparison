# Docker Container Security and Resource Limits

## Objective

Harden the RAG API containers by reducing privileges and restricting resource consumption.

## Security Configuration

- Dedicated non-root user: `appuser`
- User ID: 10001
- Linux capabilities: All dropped (`cap_drop: ALL`)
- Privilege escalation: Disabled (`no-new-privileges:true`)
- FAISS vector store: Mounted read-only

## Resource Limits

| Resource           | Per API Replica |
| ------------------ | --------------- |
| CPU limit          | 2 CPUs          |
| Memory limit       | 3 GB            |
| CPU reservation    | 0.5 CPUs        |
| Memory reservation | 1 GB            |

## Verification Results

| Test                             | Result      |
| -------------------------------- | ----------- |
| Non-root execution               | Passed      |
| Privilege escalation restriction | Passed      |
| Linux capabilities dropped       | Passed      |
| Memory limit enforced            | Passed      |
| CPU limit enforced               | Passed      |
| Both API replicas healthy        | Passed      |
| FAISS access                     | Passed      |
| HTTPS health endpoint            | HTTP 200 OK |
| Vector store loaded              | True        |
| LLM loaded                       | True        |

## Conclusion

The RAG API containers were successfully hardened using non-root execution, restricted Linux capabilities, disabled privilege escalation, and Docker resource limits. Both replicas remained healthy and operational after these changes.
