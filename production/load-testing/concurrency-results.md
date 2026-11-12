# Concurrency Testing Results

## 1. Objective

The objective of this test was to evaluate how the Springer Capital RAG API handles multiple simultaneous requests and to observe its behaviour under concurrent workloads.

The test focused on request completion, failure rates, and response latency after introducing a semaphore to limit LLM generation to one request at a time.

## 2. Test Environment

| Component           | Configuration                           |
| ------------------- | --------------------------------------- |
| API framework       | FastAPI                                 |
| RAG framework       | LangChain                               |
| LLM                 | Ollama – qwen2.5:3b                     |
| Embedding model     | all-MiniLM-L6-v2                        |
| Vector database     | FAISS                                   |
| Load testing tool   | Locust                                  |
| Number of users     | 2                                       |
| Request endpoint    | POST /api/v1/query                      |
| Concurrency control | asyncio.Semaphore(1)                    |
| Hardware            | Intel Core i5-6200U, 2 cores, 16 GB RAM |
| Model inference     | CPU-based                               |

## 3. Test Results

### Test 1: Two Concurrent Users

| Metric                |        Result |
| --------------------- | ------------: |
| Total requests        |             1 |
| Failed requests       |             0 |
| Average response time | 521,841.54 ms |
| Median response time  | 521,841.54 ms |
| 95th percentile       |    522,000 ms |
| Minimum response time |    521,842 ms |
| Maximum response time |    521,842 ms |

### Test 2: Two Concurrent Users

| Metric                |        Result |
| --------------------- | ------------: |
| Total requests        |             2 |
| Failed requests       |             0 |
| Average response time | 554,027.88 ms |
| Median response time  |    586,000 ms |
| 95th percentile       |    586,000 ms |
| Minimum response time |    521,842 ms |
| Maximum response time |    586,214 ms |

### Observations

- Both tests completed without failed requests.
- The second test recorded two successful requests.
- Response times were very high, ranging from approximately 8.7 to 9.8 minutes.
- The API uses `asyncio.Semaphore(1)` to restrict LLM generation to one request at a time.
- The results are consistent with requests waiting for access to the LLM generation slot.

## 4. Concurrency Control Implementation

An asynchronous semaphore was introduced into the FastAPI application:

```python
LLM_SEMAPHORE = asyncio.Semaphore(1)
```

The LLM invocation was then wrapped with the semaphore:

```python
async with LLM_SEMAPHORE:
    response = await app.state.llm.ainvoke(messages)
```

This restricts the application to one active LLM generation at a time.

The purpose is to prevent multiple generation requests from competing for limited CPU and memory resources.

Requests that cannot immediately acquire the semaphore wait until the active generation finishes.

**Important:** This is an application-level concurrency control mechanism. It does not increase the model's inference speed or overall processing capacity.

## 5. Performance Analysis

The tests recorded zero failed requests, indicating that the API successfully processed the requests included in the tests.

However, response latency remained high.

The main performance limitation is the local inference environment. The Qwen2.5 3B model runs on CPU hardware with an Intel Core i5-6200U processor and no NVIDIA GPU acceleration.

The earlier single-user Locust test recorded an average response time of approximately 477 seconds. The subsequent two-user tests recorded average response times of approximately 522 and 554 seconds.

These results indicate that the current hardware is unsuitable for handling multiple simultaneous, latency-sensitive RAG requests.

The semaphore provides a way to control generation concurrency, but it does not solve the underlying hardware limitation.

## 6. Limitations

The following limitations apply to this experiment:

1. **Limited hardware:** Testing was performed on a dual-core CPU without dedicated GPU acceleration.

2. **Small test sample:** Only a small number of requests completed during the tests. The results are not sufficient for statistically reliable performance conclusions.

3. **Single-machine testing:** The API and local inference service were tested using the same development environment.

4. **No distributed inference:** The tests did not involve multiple model-serving instances or a dedicated inference server.

5. **Limited concurrency:** The experiment used two Locust users and did not establish the system's maximum sustainable concurrency.

6. **No high-availability validation:** The tests did not evaluate failover, redundant API instances, or recovery from service failures.

7. **No security assessment:** Authentication, authorization, rate limiting, and vulnerability testing were outside the scope of this experiment.

8. **No disaster-recovery validation:** Backup restoration and recovery procedures were not tested.

## 7. Conclusion

The concurrency experiment demonstrated that the Springer Capital RAG API can successfully process the tested requests without returning application-level failures.

Introducing `asyncio.Semaphore(1)` provides basic control over concurrent LLM generation and helps prevent multiple generation tasks from competing for limited local resources.

However, the high response latency demonstrates that the current development hardware is a significant bottleneck.

The results should therefore be treated as an initial concurrency experiment rather than evidence of production-scale capacity.

Further testing on more capable infrastructure is required to establish sustainable throughput, response-time targets, and production readiness.

## 8. Recommendations and Next Steps

The following improvements are recommended for subsequent production-readiness work:

- **Infrastructure scaling:** Evaluate deployment on hardware with more CPU cores, sufficient memory, or GPU acceleration.
- **API scalability:** Introduce containerized deployment and multiple API instances where appropriate.
- **Load management:** Add request timeouts, queue limits, and overload protection.
- **Model serving:** Evaluate dedicated inference infrastructure to reduce the impact of model generation on API resources.
- **Monitoring:** Introduce Prometheus and Grafana to monitor request latency, CPU usage, memory consumption, and service availability.
- **High availability:** Investigate reverse-proxy routing, health checks, and API instance failover.
- **Security:** Implement API authentication, request validation, and rate limiting.
- **Disaster recovery:** Establish vector-store backups and test restoration procedures.

These recommendations are proposed next steps; they have not yet been implemented or validated by the concurrency experiment.

---

**Test status:** Initial concurrency testing completed.

**Overall assessment:** Successful request processing, but high latency and limited hardware capacity prevent any claim of production-scale concurrency readiness.
