Create a virtual environment:

```python
python -m venv venv
```

Activate it on Git Bash:

```bash
source venv/Scripts/activate
```

Upgrade pip

```bash
python -m pip install --upgrade
```

We create 10 pages of data that will answer some following questions and we save it in a pdf file
and we verify it's up to 10 pages

Next: Build the evaluation dataset
Before installing the four frameworks, let's create the same 15 questions that every framework will answer.

We'll use three questions per technical topic:

- Docker: 3 questions
- Kubernetes: 3 questions
- Terraform: 3 questions
- AWS: 3 questions
- CI/CD: 3 questions

Step 1: Create evaluation/questions.json
Step 2: Validate the JSON file

```bash
python -m json.tool evaluation/questions.json
```

We make use of our local LLM provider so all the four framework can make use of the same model

Chekc if Ollama is installed, we check the list as well,

```bash
ollama --version
ollama list
```

We also check the computer RAM

```bash
wmic computersystem get TotalPhysicalMemory
```

If it's unavailable we make use of PowerShell

```powershell
(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB
```

We download the model we want to make use of after comfirming that ollama has been succesfully installed

```bash
ollama pull qwen2.5:3b
```

After the download, we confirm it if it's in the list

```bash
ollama list
```

The run the ollama

```bash
ollama run qwen2.5:3b
```

What comes after this?
Our next stages will be:

1. Establish shared document extraction and chunking.
2. Configure the embedding model.
3. Set up independent vector stores for each framework.
4. Implement the four RAG pipelines.
5. Run the same 15 questions against all four implementations.
6. Compare retrieval quality, response accuracy, latency, and resource usage.

One important distinction for our experiment:

- LLM: qwen2.5:3b through Ollama.
- Embeddings: sentence-transformers/all-MiniLM-L6-v2.
- Vector retrieval: Same normalized corpus chunks and top_k = 4.
- Evaluation: Same 15 questions for every framework.

We create the shared configuration file
Inside your configs folder, create: rag-config.json
And we input the json data structure

Next step: Prepare the shared ingestion environment
Before implementing each framework, we'll create one common preprocessing pipeline. This ensures all four frameworks receive identical document chunks rather than using different native chunking defaults.

We install the required base packages:
With your virtual environment activated, run:

```bash
python -m pip install pypdf transformers sentence-transformers
```

These packages will handle:

- pypdf: Extract text from your 10-page PDF.
- transformers: Load the embedding model's tokenizer for consistent 500-token chunks.
- sentence-transformers: Generate document embeddings using the same embedding model.

After the installation of the packages, we create a `shared_ingestion.py` file, and this output to `evaluation/shared_chunks.json`

We generate shared embeddings
We'll generate embeddings once and reuse the same vectors across all four frameworks. This improves experimental consistency.

First, create `evaluation/generate_embeddings.py`.

We'll continue to make the comparison

Our comparison will remain:

1. LlamaIndex
2. Haystack
3. LangChain
4. LlamaStack (original project)

We'll keep the same Ollama model, embedding model, corpus, chunks, and evaluation questions across all four.

For each of the framework dependencies, we isolated each of it preprocessing environment using for llamastack, we use this:

```bash
py -3.12 -m venv .venvs/llamastack # Using this to create the environment
```

We activate this:
`source .venvs/llamastack/Scripts/activate`

We upgrade the pip
`python -m pip install --upgrade pip`

We install the pip release
`python -m pip install llama-stack==0.2.19`

We also install ollama
`python -m pip install ollama`

We viewed the installation
`python -m pip show ollama`

The Ollama Python client (0.6.3) is now installed in your LlamaStack environment.

We create the LlamaStack build configuration

We used this for the build configuration to get some information from it

```yaml
version: '2'
image_name: local-ollama

apis:
  - inference
  - agents
  - vector_io
  - telemetry

providers:
  inference:
    - provider_id: ollama
      provider_type: remote::ollama
      config:
        url: http://localhost:11434
        model: qwen2.5:3b
```

We run this command to inspect the available distribution templates:

```bash
llama stack build --list-distros
```

The starter distribution is the best starting point for your setup because it is intended for CPU-only environments. We can use it as the base and configure Ollama for inference.

Before editing the YAML, let's inspect the actual starter configuration shipped with your installed LlamaStack 0.2.19. This avoids using a configuration format from a newer release.

We locate the starter configuration and run:

```bash
python -c "import llama_stack, pathlib; p=pathlib.Path(llama_stack.__file__).parent; print('Package:', p); print('\n'.join(str(f) for f in p.rglob('build.yaml') if 'starter' in str(f).lower()))"
```

We display the starter configuration and and run this command

```bash
python -c "from pathlib import Path; import llama_stack; p=Path(llama_stack.__file__).parent/'distributions'/'starter'/'build.yaml'; print(p.read_text())"
```

Now, we have gotten the Llama Stack 0.2.19 configuration, then we use this out of it

```bash
remote::ollama for LLM inference.
inline::sentence-transformers for embeddings.
inline::faiss and inline::sqlite-vec for vector storage.
inline::meta-reference for agents and telemetry.
inline::rag-runtime for RAG tools.
```

We'll keep these components so the LlamaStack implementation can cover the required RAG features.

We open `configs/llamastack-build.yaml` and replace its contents

Before we replace it, this is the initial content we used in getting the configuration

```yaml
version: '2'
image_name: local-ollama

apis:
  - inference
  - agents
  - vector_io
  - telemetry

providers:
  inference:
    - provider_id: ollama
      provider_type: remote::ollama
      config:
        url: http://localhost:11434
        model: qwen2.5:3b
```

After the replacement of the content, we used this to validate it

```bash
python -c "import yaml; print(yaml.safe_load(open('configs/llamastack-build.yaml')))"
```

Use this in activating the llamastack environment

```bash
source ~/.venvs/llamastack/bin/activate
```

Make use of this to start the ollama

```powershell
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

Start this in Ubuntu server

```bash
curl --connect-timeout 5 http://172.27.224.1:11434/api/tags
```

Set the Ollama URL in Ubuntu
In your active llamastack environment, run:

```bash
export OLLAMA_URL="http://172.27.224.1:11434"
```

We want to impelement the second one which is llamastack-rag with it environment

Created the environment of llamastack-rag
`uv venv --python 3.12 llamaindex-rag`

We install this packages to make use of

```bash
uv pip install --python ./llamaindex-rag/bin/python \
  llama-index-core \
  llama-index-vector-stores-faiss \
  llama-index-llms-ollama \
  llama-index-embeddings-huggingface \
  faiss-cpu
```

We verify what we have installed

```bash
 python -c "import numpy, faiss, llama_index.core; import llama_index.vector_stores.faiss; import llama_index.llms.ollama; import llama_index.embeddings.huggingface; print('NumPy:', numpy.__version__); print('FAISS:', faiss.__version__); print('LlamaIndex imports successful.')"
```

Working on the third framework for the RAG pipelines

Created the environment first
`uv venv --python 3.12 haystack-rag`

Activate the environment
`source haystack-rag/bin/activate`

Install the packags that will be used

```bash
uv pip install --python ./haystack-rag/bin/python \
    haystack-ai \
    ollama-haystack \
    sentence-transformers \
    faiss-cpu
```


We want to work on the productionn aspect, we first create numbers of folders using this command
`mkdir -p production/api production/tests production/load-testing production/nginx production/monitoring production/backup`

We install `pip` in the langchain environment
`python -m ensurepip --upgrade`

Check if the `pip` has been installed 
`python -m pip --version`

Check if the required packages is used
`python -m pip show fastapi uvicorn langchain langchain-community langchain-huggingface langchain-ollama`

We installed the ones that are not found
`python -m pip install fastapi "uvicorn[standard]"`

And we check it out, if it has been installed 
`python -m pip show fastapi uvicorn`

Activate the environment
`source langchain-rag/bin/activate`



# RAG Framework Comparison – Project Process

## Objective

Compare LlamaIndex, Haystack, LangChain, and LlamaStack
through practical implementations of Retrieval-Augmented
Generation (RAG).

## Development Environment

- Operating System: Windows
- Terminal: Git Bash
- Programming Language: Python
- Python Version: 3.12.10

## Experimental Configuration

- Corpus: 10-page DevOps documentation
- Embedding Model: all-MiniLM-L6-v2
- Chunk Size: 500 tokens
- Chunk Overlap: 50 tokens
- Retrieval Top-K: 4

## Evaluation Criteria

- Document ingestion
- Retrieval quality
- Answer correctness
- Agent and tool support
- Observability
- Production readiness
- Performance and latency

## Implementation Strategy

Each framework will have an independent implementation
using the same source documents and experimental settings.

## Benchmarking Methodology

All four frameworks will use the same source documents,
embedding model, chunking configuration, and evaluation
questions.

Each implementation will use an independent vector
store collection to prevent cross-framework contamination.

## Expected Deliverables

- Four working RAG implementations
- Feature comparison matrix
- Benchmark results
- Production readiness assessment
- Framework selection guide
- Final Markdown research report
