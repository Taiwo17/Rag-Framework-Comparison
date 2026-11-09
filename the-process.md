# RAG Framework Comparison — Implementation Process

## 1. Project Setup and Experimental Design

### 1.1 Project Objective

The project compares four Retrieval-Augmented Generation (RAG) frameworks:

1. LlamaIndex
2. Haystack
3. LangChain
4. LlamaStack

The objective is to implement a working RAG pipeline with each framework and compare their document processing, retrieval, answer generation, and evaluation capabilities.

The experiment uses a shared corpus and evaluation configuration to maintain consistency across the implementations.

### 1.2 Experimental Environment

The final implementation environment was:

| Component | Configuration |
|---|---|
| Operating system | Ubuntu 26.04.1 LTS through WSL2 |
| Python | 3.12.16 |
| Environment manager | uv 0.13.7 |
| LLM provider | Ollama |
| Language model | qwen2.5:3b |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Embedding dimensions | 384 |
| Corpus | 10-page DevOps PDF |

Python 3.12.16 was installed through uv and used for the framework-specific environments.

Each framework was isolated in its own virtual environment to reduce dependency conflicts.

### 1.3 Framework Versions

The experiment used the following versions:

| Framework | Version |
|---|---|
| LlamaIndex Core | 0.14.25 |
| Haystack | 3.4.1 |
| LangChain | 1.4.9 |
| LlamaStack | 0.2.19 |

The LlamaStack version was explicitly pinned to 0.2.19 to preserve the original LlamaStack implementation used in the experiment.

### 1.4 Shared Experimental Configuration

The following settings were used across the four implementations:

| Parameter | Value |
|---|---|
| Chunk size | 500 tokens |
| Chunk overlap | 50 tokens |
| Retrieval top-k | 4 |
| Evaluation questions | 15 |
| LLM temperature | 0 |
| Maximum generated tokens | 500 |
| Embedding dimensions | 384 |

The same corpus, normalized chunks, embeddings, and evaluation questions were reused across the four frameworks.

This approach reduced differences caused by framework-specific preprocessing defaults and made the retrieval comparison more controlled.

### 1.5 Project Structure

The project was organized into the following main directories:

- `configs/` — shared experiment and framework configuration.
- `corpus/` — the DevOps knowledge corpus.
- `evaluation/` — ingestion, indexing, retrieval, RAG, and evaluation scripts.
- `evaluation/results/` — generated benchmark results and answer-quality review.
- `reports/` — benchmark documentation.
- `feature-comparison-matrix.md` — framework feature and production-readiness comparison.

### 1.6 Local Model Setup

Ollama was used as the local model provider so that all four frameworks could use the same language model.

The model used for generation was:

```bash
ollama pull qwen2.5:3b
```

The embedding model was:

```text
sentence-transformers/all-MiniLM-L6-v2
```

The embedding model was used to generate shared normalized document embeddings and query embeddings for the experiment.

## 2. Corpus Preparation and Shared Preprocessing

### 2.1 Creating the DevOps Corpus

A 10-page DevOps knowledge corpus was created as the common document source for all four RAG implementations.

The corpus covered five technical topics:

| Pages | Topic |
|---|---|
| 1–2 | Docker |
| 3–4 | Kubernetes |
| 5–6 | Terraform |
| 7–8 | AWS |
| 9–10 | CI/CD |

The corpus was saved as:

```text
corpus/devops-rag-corpus.pdf
```

The PDF was verified to contain exactly 10 pages and extractable text.

### 2.2 Creating the Evaluation Dataset

Before implementing the frameworks, a shared evaluation dataset was created.

The dataset contained 15 questions, with three questions for each technical topic:

- Docker: 3 questions.
- Kubernetes: 3 questions.
- Terraform: 3 questions.
- AWS: 3 questions.
- CI/CD: 3 questions.

The questions were stored in:

```text
evaluation/questions.json
```

The JSON structure included question IDs, topics, questions, expected answers, and source-section references.

The file was validated using:

```bash
python -m json.tool evaluation/questions.json
```

This ensured that every framework would be evaluated using the same questions.

### 2.3 Shared RAG Configuration

A shared configuration file was created:

```text
configs/rag-config.json
```

It defined the language model, embedding model, chunking settings, retrieval configuration, evaluation dataset, and corpus location.

The configuration included:

- Language model: `qwen2.5:3b`.
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`.
- Chunk size: 500 tokens.
- Chunk overlap: 50 tokens.
- Retrieval top-k: 4.
- Evaluation questions: 15.
- Expected corpus pages: 10.

### 2.4 Creating the Shared Ingestion Pipeline

A common preprocessing pipeline was implemented in:

```text
shared_ingestion.py
```

The script used:

- `pypdf` to extract text from the PDF.
- `transformers` to load the embedding model tokenizer.
- The embedding model tokenizer to split the extracted text into consistent token-based chunks.

Each chunk preserved metadata, including:

- Source document.
- Page number.
- Chunk index.
- Unique chunk ID.

The generated chunks were saved to:

```text
evaluation/shared_chunks.json
```

### 2.5 Chunk Validation

The shared chunks were validated to confirm that:

- All 10 PDF pages were represented.
- The chunk IDs were unique.
- No chunk exceeded 500 tokens.
- The 50-token overlap was applied during chunking.
- Source and page metadata were preserved.

The preprocessing stage generated 20 chunks.

The observed chunk statistics were:

| Metric | Result |
|---|---:|
| Total chunks | 20 |
| Smallest chunk | 104 tokens |
| Largest chunk | 500 tokens |
| Average chunk size | 341.90 tokens |
| Unique chunk IDs | Yes |

### 2.6 Generating Shared Embeddings

After validating the chunks, a shared embedding generation script was created:

```text
evaluation/generate_embeddings.py
```

The script used:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Each chunk was converted into a normalized 384-dimensional embedding.

The resulting embeddings were saved to:

```text
evaluation/shared_embeddings.json
```

Validation confirmed:

- 20 embedding records.
- 384 dimensions per embedding.
- Normalized vectors.
- Finite numerical values.
- Unique chunk IDs.
- Preserved source and page metadata.

### 2.7 Why Shared Preprocessing Was Used

Each framework has its own document ingestion, chunking, and embedding abstractions.

However, allowing every framework to independently process the corpus could introduce differences in chunk boundaries, embedding generation, and metadata.

To reduce these differences, the experiment reused the same preprocessed chunks and embeddings.

This allowed the practical comparison to focus more closely on framework-specific indexing, retrieval, and generation behavior.

Native ingestion and chunking capabilities were considered separately in the feature comparison.

## 3. LlamaStack Implementation

### 3.1 Why LlamaStack Was Implemented First

LlamaStack was selected as the first framework for implementation because its provider-based architecture required additional configuration compared with the other frameworks.

The experiment retained the original LlamaStack project rather than replacing it with another implementation.

The version used was:

```text
llama-stack==0.2.19
```

### 3.2 Initial Environment Challenges

The initial attempt to build LlamaStack on Windows encountered a platform compatibility issue.

The build process attempted to execute a shell script using a Windows environment, resulting in a `WinError 193` error.

To resolve this, the implementation was moved to Ubuntu through WSL2.

Python 3.12.16 was installed using uv, and a dedicated LlamaStack environment was created.

### 3.3 Building the LlamaStack Environment

The LlamaStack build configuration was created at:

```text
configs/llamastack-build.yaml
```

The configuration included the required providers:

| API area | Provider |
|---|---|
| Inference | `remote::ollama` |
| Vector storage | `inline::faiss` |
| Files | `inline::localfs` |
| Agents | `inline::meta-reference` |
| Telemetry | `inline::meta-reference` |
| Tool runtime | `inline::rag-runtime` |

Additional packages were included to support the runtime.

The environment was built using:

```bash
llama stack build \
  --config configs/llamastack-build.yaml \
  --image-type venv \
  --image-name llamastack-rag
```

### 3.4 Resolving the LlamaStack Version Mismatch

The initial build installed LlamaStack 0.7.3 instead of the required 0.2.19.

To preserve the selected experimental version, the environment was corrected using:

```bash
uv pip install \
  --python ./llamastack-rag/bin/python \
  "llama-stack==0.2.19"
```

The installed version was verified using:

```bash
uv pip show \
  --python ./llamastack-rag/bin/python \
  llama-stack
```

The CLI version was also checked:

```bash
./llamastack-rag/bin/llama stack --version
```

The environment successfully reported version 0.2.19.

### 3.5 Configuring Ollama Across Windows and WSL2

Ollama was installed on Windows, while LlamaStack ran inside Ubuntu through WSL2.

This created a networking requirement because the Ubuntu environment could not access the Windows-hosted Ollama service through `localhost`.

Ollama was started in Windows PowerShell using:

```powershell
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

The WSL2 gateway address was identified as:

```text
172.27.224.1
```

The Ollama endpoint was then configured in Ubuntu:

```bash
export OLLAMA_URL="http://172.27.224.1:11434"
```

Connectivity was verified using:

```bash
curl --connect-timeout 5 "$OLLAMA_URL/api/tags"
```

The endpoint successfully returned the available Ollama models.

The models used were:

- `qwen2.5:3b` for answer generation.
- `all-minilm:l6-v2` for embeddings through the LlamaStack Ollama provider.

### 3.6 Resolving LlamaStack Runtime Configuration Issues

During startup, the runtime encountered a missing safety API configuration.

The runtime YAML was updated to include the safety API and its corresponding `inline::llama-guard` provider configuration.

This resolved the startup error.

Another issue occurred when the Ollama provider attempted to register `nomic-embed-text` automatically and pull the model from the Ollama registry.

The pull failed because the environment could not resolve the registry hostname.

As a local workaround, the automatic `nomic-embed-text` model registration was commented out in the project-local Ollama provider implementation.

The original file was backed up as:

```text
ollama.py.bak
```

This was a local package modification, not a general LlamaStack configuration requirement. It should be considered when reproducing the exact environment.

### 3.7 Starting and Verifying the LlamaStack Server

The runtime configuration was stored at:

```text
~/.llama/distributions/llamastack-rag/llamastack-rag-run.yaml
```

The server was started using:

```bash
export OLLAMA_URL="http://172.27.224.1:11434"

./llamastack-rag/bin/llama stack run \
  ~/.llama/distributions/llamastack-rag/llamastack-rag-run.yaml
```

The health endpoint was checked using:

```bash
curl http://localhost:8321/v1/health
```

The server returned:

```json
{
  "status": "OK"
}
```

The available models were verified through:

```bash
curl http://localhost:8321/v1/models
```

The runtime exposed the configured embedding and language models.

### 3.8 Registering the Vector Database

A FAISS-backed vector database was registered with the LlamaStack vector I/O API.

The configured vector database ID was:

```text
llamastack_devops_rag
```

Its embedding configuration used:

```text
ollama/all-minilm:l6-v2
```

with 384 embedding dimensions.

The shared embeddings were inserted using:

```text
evaluation/insert_llamastack.py
```

The script loaded the records from:

```text
evaluation/shared_embeddings.json
```

It validated the chunk IDs and embedding dimensions before inserting the records.

All 20 chunks were successfully inserted.

A retrieval test returned relevant Docker chunks, confirming that the vector database was operational.

### 3.9 Implementing the LlamaStack RAG Pipeline

The individual RAG pipeline was implemented in:

```text
evaluation/run_llamastack_rag.py
```

The implementation performed the following operations:

1. Received a user question.
2. Generated a query embedding through the LlamaStack inference API.
3. Retrieved relevant chunks from the registered FAISS vector database.
4. Constructed a context from the retrieved chunks.
5. Sent the question and context to the Ollama language model through LlamaStack.
6. Returned the generated answer and retrieved source information.

The implementation used the shared retrieval configuration and generation settings.

### 3.10 Running the LlamaStack Evaluation

The batch evaluation script was created at:

```text
evaluation/evaluate_llamastack.py
```

It processed the 15 evaluation questions and saved results incrementally to:

```text
evaluation/results/llamastack-results.json
```

Incremental saving allowed the evaluation to resume without repeating questions that had already completed successfully.

The evaluation completed with:

| Metric | Result |
|---|---:|
| Total questions | 15 |
| Successful | 15 |
| Failed | 0 |
| Missing answers | 0 |
| Missing retrieval records | 0 |
| Average execution time | 194.87 seconds |
| Total execution time | 48.72 minutes |

The evaluation confirmed that the LlamaStack implementation could successfully retrieve context and generate answers for all 15 questions.

## 4. Implementing LlamaIndex, Haystack, and LangChain

After completing the LlamaStack implementation, the remaining three frameworks were configured in separate Python environments.

Each implementation reused the shared corpus chunks and embeddings to maintain consistency.

### 4.1 LlamaIndex Implementation

#### Environment Setup

A dedicated environment was created for LlamaIndex:

```bash
uv venv --python 3.12 llamaindex-rag
```

The required packages were installed:

```bash
uv pip install --python ./llamaindex-rag/bin/python \
  llama-index-core \
  llama-index-vector-stores-faiss \
  llama-index-llms-ollama \
  llama-index-embeddings-huggingface \
  faiss-cpu
```

The installed LlamaIndex Core version was 0.14.25.

#### Building the Vector Index

The indexing script was created at:

```text
evaluation/build_llamaindex_index.py
```

It performed the following operations:

1. Loaded the shared records from `evaluation/shared_embeddings.json`.
2. Created LlamaIndex `TextNode` objects.
3. Preserved chunk IDs and source metadata.
4. Attached the existing 384-dimensional embeddings to the nodes.
5. Created a FAISS index using inner-product similarity.
6. Persisted the index to `evaluation/vector_stores/llamaindex`.

The index was built using 20 precomputed vectors. The framework did not need to regenerate document embeddings.

#### Retrieval Testing

The retrieval test was implemented in:

```text
evaluation/test_llamaindex_retrieval.py
```

The test loaded the persisted index and used LlamaIndex's retriever with `similarity_top_k=4`.

A Docker-related test question successfully returned four chunks, including relevant Docker content from pages 1 and 2.

#### RAG Pipeline

The RAG implementation was created at:

```text
evaluation/run_llamaindex_rag.py
```

The pipeline used:

- The persisted FAISS index.
- Hugging Face embeddings for query embedding.
- Ollama `qwen2.5:3b` for answer generation.
- The shared retrieval configuration.
- The common answer-generation prompt.

#### Batch Evaluation

The batch evaluation script was:

```text
evaluation/evaluate_llamaindex.py
```

Results were saved to:

```text
evaluation/results/llamaindex-results.json
```

The evaluation completed successfully:

| Metric | Result |
|---|---:|
| Total questions | 15 |
| Successful | 15 |
| Failed | 0 |
| Missing answers | 0 |
| Missing retrieval records | 0 |
| Average execution time | 343.56 seconds |
| Total execution time | 85.89 minutes |

### 4.2 Haystack Implementation

#### Environment Setup

A separate environment was created:

```bash
uv venv --python 3.12 haystack-rag
```

The core dependencies were installed:

```bash
uv pip install --python ./haystack-rag/bin/python \
  haystack-ai \
  ollama-haystack \
  sentence-transformers \
  faiss-cpu
```

The Sentence Transformers integration was installed separately:

```bash
uv pip install --python ./haystack-rag/bin/python \
  sentence-transformers-haystack
```

The installed Haystack version was 3.4.1.

#### Building the Document Store

The setup script was created at:

```text
evaluation/build_haystack_store.py
```

It loaded the shared embedding records and converted them into Haystack `Document` objects.

Each document preserved:

- Original chunk ID.
- Text content.
- Precomputed embedding.
- Source metadata.
- Page number.
- Chunk index.

The implementation used Haystack's `InMemoryDocumentStore` with cosine similarity.

The setup processed all 20 documents and confirmed the 384-dimensional embedding configuration.

The script also generated:

```text
evaluation/haystack_store.json
```

This file served as a store summary; the actual Haystack document store was reconstructed in memory by the scripts.

#### Retrieval Testing

The retrieval test was implemented in:

```text
evaluation/test_haystack_retrieval.py
```

It used:

- `SentenceTransformersTextEmbedder` to generate query embeddings.
- `InMemoryEmbeddingRetriever` to retrieve documents.
- Cosine similarity for retrieval ranking.

A Docker-related question successfully returned four chunks, with the first three containing Docker-related information.

#### RAG Pipeline

The pipeline was implemented in:

```text
evaluation/run_haystack_rag.py
```

It combined query embedding, document retrieval, context construction, and answer generation using `OllamaChatGenerator`.

The generation model was `qwen2.5:3b`, using the shared prompt and generation settings.

#### Batch Evaluation

The batch evaluation script was:

```text
evaluation/evaluate_haystack.py
```

Results were saved to:

```text
evaluation/results/haystack-results.json
```

The evaluation completed successfully:

| Metric | Result |
|---|---:|
| Total questions | 15 |
| Successful | 15 |
| Failed | 0 |
| Missing answers | 0 |
| Missing retrieval records | 0 |
| Average execution time | 292.28 seconds |
| Total execution time | 73.07 minutes |

### 4.3 LangChain Implementation

#### Environment Setup

A separate environment was created:

```bash
uv venv --python 3.12 langchain-rag
```

The required packages were installed:

```bash
uv pip install --python ./langchain-rag/bin/python \
  langchain \
  langchain-community \
  langchain-ollama \
  langchain-huggingface \
  faiss-cpu \
  sentence-transformers
```

The installed LangChain version was 1.4.9.

The FAISS integration from `langchain-community` was used for vector storage and retrieval.

#### Building the Vector Store

The indexing script was created at:

```text
evaluation/build_langchain_store.py
```

It loaded the shared embedding records and constructed a FAISS vector store using:

- The existing chunk text.
- Precomputed 384-dimensional embeddings.
- Preserved metadata.
- Inner-product similarity.

The vector store was persisted to:

```text
evaluation/vector_stores/langchain
```

All 20 documents were indexed successfully.

#### Retrieval Testing

The retrieval test was created at:

```text
evaluation/test_langchain_retrieval.py
```

It loaded the persisted FAISS index and used similarity search with the configured top-k value of four.

A Docker-related test question returned four chunks, with the first three containing relevant Docker information.

#### RAG Pipeline

The implementation was created at:

```text
evaluation/run_langchain_rag.py
```

It used:

- LangChain's FAISS vector-store integration.
- `HuggingFaceEmbeddings` for query embeddings.
- `ChatOllama` for answer generation.
- The shared prompt and retrieval settings.

The language model was `qwen2.5:3b`.

#### Batch Evaluation

The batch evaluation script was:

```text
evaluation/evaluate_langchain.py
```

Results were saved to:

```text
evaluation/results/langchain-results.json
```

The evaluation completed successfully:

| Metric | Result |
|---|---:|
| Total questions | 15 |
| Successful | 15 |
| Failed | 0 |
| Missing answers | 0 |
| Missing retrieval records | 0 |
| Average execution time | 272.69 seconds |
| Total execution time | 68.17 minutes |

### 4.4 Implementation Comparison

All three frameworks successfully indexed or loaded the shared embeddings, retrieved context, and generated answers for the 15 evaluation questions.

The implementations differed in their storage abstractions:

| Framework | Retrieval and storage approach |
|---|---|
| LlamaIndex | VectorStoreIndex with FAISS |
| Haystack | InMemoryDocumentStore with cosine similarity |
| LangChain | FAISS vector store with inner-product similarity |

The shared preprocessing stage ensured that each framework received the same document chunks and embedding vectors.

However, differences in framework-specific retrieval implementations and returned similarity scores mean that raw similarity scores should not be compared directly across frameworks.

## 5. Evaluation, Validation, and Final Findings

### 5.1 Running the Four Evaluations

After completing the four RAG implementations, each framework was evaluated using the same 15 questions.

The evaluation scripts were:

| Framework | Evaluation script |
|---|---|
| LlamaIndex | `evaluation/evaluate_llamaindex.py` |
| Haystack | `evaluation/evaluate_haystack.py` |
| LangChain | `evaluation/evaluate_langchain.py` |
| LlamaStack | `evaluation/evaluate_llamastack.py` |

Each script performed retrieval and answer generation, then saved the results in JSON format.

The results were stored in:

```text
evaluation/results/
```

The evaluation scripts also supported incremental saving, allowing completed questions to be retained if an evaluation was interrupted.

### 5.2 Validating Evaluation Results

After the four evaluation runs, the generated JSON files were checked for completeness.

The validation covered:

- Total number of evaluation records.
- Unique question IDs.
- Successful and failed evaluations.
- Missing generated answers.
- Missing retrieval records.

The validation confirmed:

| Framework | Records | Successful | Failed |
|---|---:|---:|---:|
| LlamaIndex | 15 | 15 | 0 |
| Haystack | 15 | 15 | 0 |
| LangChain | 15 | 15 | 0 |
| LlamaStack | 15 | 15 | 0 |

All four frameworks produced complete evaluation records with no missing answers or retrieval records.

### 5.3 Measuring Retrieval Relevance

Retrieval relevance was assessed using the source-page allocation of the corpus.

The evaluation compared retrieved chunk pages against the expected topic-page ranges for each question.

The results were:

| Framework | Relevant chunks | Topic-page precision | Topic-page hit rate |
|---|---:|---:|---:|
| LlamaIndex | 33/60 | 55.00% | 100% |
| Haystack | 33/60 | 55.00% | 100% |
| LangChain | 33/60 | 55.00% | 100% |
| LlamaStack | 28/45 | 62.22% | 93.33% |

LlamaIndex, Haystack, and LangChain retrieved at least one chunk from the expected topic pages for all 15 questions.

LlamaStack returned three chunks per question rather than the configured top four. This difference was considered when interpreting its precision result.

### 5.4 Manual Answer-Quality Assessment

Retrieval success alone does not establish that a generated answer is technically correct.

A separate answer-quality review was therefore conducted.

The review covered all 15 questions and compared the generated answers from the four frameworks against the expected answers.

Four dimensions were assessed:

1. Correctness.
2. Completeness.
3. Context grounding.
4. Relevance.

Each dimension received a score between 0 and 2.

The maximum score was 120 points per framework.

The assessment was documented in:

```text
evaluation/results/answer-quality-review.md
```

The final scores were:

| Framework | Score | Percentage |
|---|---:|---:|
| LlamaStack | 101/120 | 84.17% |
| LlamaIndex | 100/120 | 83.33% |
| Haystack | 100/120 | 83.33% |
| LangChain | 100/120 | 83.33% |

The results showed relatively small differences in answer quality across the four implementations.

The manual assessment also identified examples of technically inaccurate statements, incomplete explanations, and details that were not adequately supported by retrieved context.

### 5.5 Comparing Execution Time

The average execution times were calculated from the completed evaluation records.

| Framework | Average execution time | Total execution time |
|---|---:|---:|
| LlamaIndex | 343.56 seconds | 85.89 minutes |
| Haystack | 292.28 seconds | 73.07 minutes |
| LangChain | 272.69 seconds | 68.17 minutes |
| LlamaStack | 194.87 seconds | 48.72 minutes |

LlamaStack recorded the lowest average execution time in the experiment.

However, the measurements represent end-to-end retrieval and generation time. They do not isolate framework overhead or establish that one framework will always be faster.

The measurements came from individual local evaluation runs and may have been affected by model warmup, CPU utilization, and server conditions.

### 5.6 Preparing the Benchmark Report

The benchmark findings were consolidated into:

```text
reports/benchmark-results.md
```

The report included:

- Experimental configuration.
- Evaluation methodology.
- Execution results.
- Retrieval relevance.
- Manual answer-quality scores.
- Overall comparison.
- Experiment limitations.
- Final observations.

The feature comparison and production-readiness assessment were documented separately in:

```text
feature-comparison-matrix.md
```

This document also included a framework decision guide based on the architectural differences and observed experiment results.

### 5.7 Final Project Deliverables

The completed project contains the following major deliverables:

| Deliverable | Location |
|---|---|
| DevOps knowledge corpus | `corpus/devops-rag-corpus.pdf` |
| Shared RAG configuration | `configs/rag-config.json` |
| Framework versions | `configs/framework-versions.json` |
| Evaluation questions | `evaluation/questions.json` |
| Shared chunks | `evaluation/shared_chunks.json` |
| Shared embeddings | `evaluation/shared_embeddings.json` |
| LlamaIndex implementation | `evaluation/` |
| Haystack implementation | `evaluation/` |
| LangChain implementation | `evaluation/` |
| LlamaStack implementation | `evaluation/` |
| Framework evaluation results | `evaluation/results/` |
| Answer-quality review | `evaluation/results/answer-quality-review.md` |
| Benchmark report | `reports/benchmark-results.md` |
| Feature comparison and decision guide | `feature-comparison-matrix.md` |
| Project overview | `README.md` |

### 5.8 Final Observations

The project demonstrated that all four frameworks could support a functional RAG pipeline using the same corpus, embedding model, language model, and evaluation questions.

The experiment highlighted differences in their retrieval abstractions, vector-store integrations, application architectures, and operational approaches.

LlamaStack recorded the lowest average execution time and highest manual answer-quality score in this particular experiment. LlamaIndex, Haystack, and LangChain achieved a higher topic-page hit rate.

These findings provide a practical comparison of the four frameworks, but they do not establish a universal ranking.

Further testing with larger corpora, repeated evaluations, semantic retrieval metrics, concurrent workloads, and production deployment scenarios would be necessary for a more comprehensive assessment.