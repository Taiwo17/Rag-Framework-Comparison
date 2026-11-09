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
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── requirements.txt
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
│   ├── run_haystack_rag.py
│   ├── run_langchain_rag.py
│   ├── run_llamaindex_rag.py
│   ├── run_llamastack_rag.py
│   ├── test_haystack_retrieval.py
│   ├── test_langchain_retrieval.py
│   ├── test_llamaindex_retrieval.py
│   └── results/
│       ├── answer-quality-review.md
│       ├── haystack-results.json
│       ├── langchain-results.json
│       ├── llamaindex-results.json
│       └── llamastack-results.json
│
└── reports/
    └── benchmark-results.md
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
- Production-scale concurrency, high availability, security, and disaster recovery were not tested.
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

- `feature-comparison-matrix.md` — framework capabilities, production readiness, and decision guide.
- `reports/benchmark-results.md` — benchmark findings.
- `evaluation/results/answer-quality-review.md` — manual answer-quality assessment.
- `the-process.md` — project implementation process.
- `configs/rag-config.json` — shared experiment configuration.
- `configs/framework-versions.json` — framework version information.

## 12. Conclusion

This project demonstrates that LlamaIndex, Haystack, LangChain, and LlamaStack can each support a functional RAG implementation using a shared corpus and evaluation setup.

Although their benchmark results were relatively close in answer quality, their architectures and operational approaches differ.

The experiment highlights the importance of evaluating RAG frameworks not only by their ability to generate answers but also by retrieval quality, integration flexibility, observability, execution behavior, and production requirements.
