# RAG Framework Benchmark Results

## 1. Overview

This report presents the practical evaluation results of four Retrieval-Augmented Generation (RAG) frameworks:

- LlamaIndex
- Haystack
- LangChain
- LlamaStack

Each framework was tested against the same 10-page DevOps knowledge corpus using shared chunks, embeddings, retrieval settings, and evaluation questions.

The objective was to compare their retrieval behavior, answer quality, successful execution, and end-to-end execution time.

## 2. Experimental Configuration

| Parameter | Configuration |
|---|---|
| Python version | 3.12.16 |
| LLM | Ollama `qwen2.5:3b` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Embedding dimensions | 384 |
| Corpus size | 10 PDF pages |
| Chunk size | 500 tokens |
| Chunk overlap | 50 tokens |
| Retrieval top-k | 4 |
| Evaluation questions | 15 |
| Generation temperature | 0 |
| Maximum generated tokens | 500 |

The same preprocessed chunks and embeddings were used across the four frameworks to control differences in document preprocessing.

## 3. Evaluation Methodology

The evaluation consisted of three main areas.

### 3.1 Execution success

Each framework processed the same 15 questions. A successful evaluation required a generated answer and retrieved context.

### 3.2 Retrieval relevance

Retrieval relevance was assessed using the source-page allocation of the questions.

The five corpus topics were:

| Topic | Pages |
|---|---|
| Docker | 1–2 |
| Kubernetes | 3–4 |
| Terraform | 5–6 |
| AWS | 7–8 |
| CI/CD | 9–10 |

Two metrics were calculated:

- **Topic-page precision:** Relevant retrieved chunks divided by all retrieved chunks.
- **Topic-page hit rate:** Questions with at least one relevant retrieved chunk divided by the total number of questions.

These are page-based relevance measures, not semantic relevance metrics.

### 3.3 Answer quality

Generated answers were manually assessed using four dimensions:

1. Correctness.
2. Completeness.
3. Context grounding.
4. Relevance.

Each dimension received a score from 0 to 2.

The maximum score was 8 per question and 120 per framework across 15 questions.

## 4. Execution Results

| Framework | Successful | Failed | Average execution time | Total execution time |
|---|---:|---:|---:|---:|
| LlamaIndex | 15 | 0 | 343.56 sec | 85.89 min |
| Haystack | 15 | 0 | 292.28 sec | 73.07 min |
| LangChain | 15 | 0 | 272.69 sec | 68.17 min |
| LlamaStack | 15 | 0 | 194.87 sec | 48.72 min |

All four frameworks completed the evaluation successfully, with no failed questions or missing generated answers and retrieval records.

LlamaStack recorded the lowest average end-to-end execution time in this particular experiment. LangChain recorded the second-lowest, followed by Haystack and LlamaIndex.

These measurements include retrieval and answer generation. They should not be interpreted as isolated framework processing times.

## 5. Retrieval Results

| Framework | Retrieved chunks | Relevant chunks | Topic-page precision | Topic-page hit rate |
|---|---:|---:|---:|---:|
| LlamaIndex | 60 | 33 | 55.00% | 100% |
| Haystack | 60 | 33 | 55.00% | 100% |
| LangChain | 60 | 33 | 55.00% | 100% |
| LlamaStack | 45 | 28 | 62.22% | 93.33% |

### 5.1 Observations

- LlamaIndex, Haystack, and LangChain returned four chunks for each question.
- LlamaStack returned three chunks per question, despite the configured top-k value of four.
- LlamaIndex, Haystack, and LangChain retrieved at least one topic-relevant chunk for every question.
- LlamaStack achieved the highest topic-page precision but had a lower hit rate.

### 5.2 Retrieval limitation

LlamaStack's lower retrieval count means its precision denominator differs from the other frameworks. Therefore, its precision result should not be interpreted as a directly equivalent comparison with frameworks returning four chunks.

The page-based metric also has limitations. A retrieved chunk from the correct topic pages may still be irrelevant to the specific question. Semantic retrieval evaluation would provide a more detailed assessment.

## 6. Answer-Quality Results

| Framework | Score | Percentage |
|---|---:|---:|
| LlamaStack | 101/120 | 84.17% |
| LlamaIndex | 100/120 | 83.33% |
| Haystack | 100/120 | 83.33% |
| LangChain | 100/120 | 83.33% |

### 6.1 Observations

The manual assessment produced relatively close scores across all four frameworks.

LlamaStack achieved the highest score at 84.17%, while LlamaIndex, Haystack, and LangChain each achieved 83.33%.

The small difference suggests that all four implementations were capable of generating useful answers under the experimental configuration.

However, the review also identified examples of unsupported details, incomplete explanations, and technical inaccuracies in individual answers.

The detailed question-by-question assessment is available in:

`evaluation/results/answer-quality-review.md`

### 6.2 Scoring limitation

The answer-quality scores are based on manual assessment. They are project-specific judgments rather than results from a standardized evaluation benchmark.

## 7. Overall Comparison

| Metric | Best observed result | Framework |
|---|---|---|
| Successful evaluations | 15/15 | All four |
| Lowest average execution time | 194.87 sec | LlamaStack |
| Highest topic-page precision | 62.22% | LlamaStack |
| Highest topic-page hit rate | 100% | LlamaIndex, Haystack, LangChain |
| Highest manual answer-quality score | 84.17% | LlamaStack |

### 7.1 Key findings

**Execution performance:** LlamaStack recorded the lowest average end-to-end execution time. This is an observation from one local evaluation run, not proof of inherently superior framework performance.

**Retrieval behavior:** LlamaIndex, Haystack, and LangChain returned four chunks per question and achieved a 100% topic-page hit rate. LlamaStack returned three chunks per question.

**Answer quality:** All frameworks achieved similar manual answer-quality scores, with LlamaStack slightly ahead.

**Architectural differences:** The frameworks offer different approaches to RAG development. LlamaIndex emphasizes data ingestion and retrieval, Haystack emphasizes modular pipelines, LangChain provides a broad LLM application ecosystem, and LlamaStack provides standardized APIs and a provider-based runtime.

## 8. Experiment Limitations

The results should be interpreted within the following limitations:

1. **Small corpus:** The experiment used a 10-page DevOps corpus.
2. **Limited questions:** Only 15 questions were used.
3. **Single evaluation run:** Execution times were measured from individual runs and may be affected by CPU load, model warmup, and server conditions.
4. **Different retrieval counts:** LlamaStack returned three chunks rather than four, affecting direct precision comparisons.
5. **Manual answer assessment:** Answer-quality scoring involves reviewer judgment.
6. **Page-based relevance:** The retrieval metrics do not measure semantic relevance at the individual question level.
7. **No production load testing:** Concurrent users, horizontal scaling, high availability, and disaster recovery were not evaluated.
8. **Shared preprocessing:** Native ingestion and chunking capabilities were not independently benchmarked.

## 9. Conclusion

The experiment demonstrated that LlamaIndex, Haystack, LangChain, and LlamaStack can all support functional RAG implementations using a shared corpus and evaluation configuration.

LlamaStack recorded the lowest average execution time and highest manual answer-quality score in this experiment. However, its lower retrieval count and hit rate should be considered when interpreting its retrieval results.

LlamaIndex, Haystack, and LangChain achieved a 100% topic-page hit rate, demonstrating consistent coverage of the question topics under the tested configuration.

The results do not establish a universal winner. Framework selection should consider the application's retrieval requirements, architecture, integration needs, observability, deployment environment, and operational constraints.

Further evaluation using larger datasets, repeated runs, semantic retrieval metrics, and production-scale workloads would provide stronger evidence for framework selection.