# Ollama and Model Setup

This project uses Ollama to run a local large language model (LLM) for RAG answer generation. Ollama runs on the Windows host, while the production API runs inside Docker.

This setup allows the API container to communicate with Ollama without running a second Ollama server inside the container.

## 1. Install Ollama on Windows

Download and install Ollama for Windows from the official website:

https://ollama.com/download

After installation, open Windows PowerShell and verify the installation:

```powershell
ollama --version
```

The version used during this project's verification was:

```text
ollama version is 0.5.11
```

## 2. Download the required models

The project uses Qwen 2.5 3B for LLM generation.

Download it using:

```powershell
ollama pull qwen2.5:3b
```

The project also has an Ollama embedding model available:

```powershell
ollama pull all-minilm:l6-v2
```

Check the installed models:

```powershell
ollama list
```

The verified environment contained:

| Model              | Purpose                | Approximate size |
| ------------------ | ---------------------- | ---------------: |
| `qwen2.5:3b`       | LLM answer generation  |           1.9 GB |
| `all-minilm:l6-v2` | Ollama embedding model |            45 MB |

Inspect the Qwen model:

```powershell
ollama show qwen2.5:3b
```

The verified model uses Q4_K_M quantization, has approximately 3.1 billion parameters, and supports a context length of 32,768 tokens.

**Important:** The production API's configured embedding model is `sentence-transformers/all-MiniLM-L6-v2`. The separately installed Ollama model `all-minilm:l6-v2` is not the configured production embedding model.

## 3. Configure the production API

The production API reads its Ollama configuration from environment variables in `production/.env`.

Configure these values:

```dotenv
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:3b
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

The API source reads these settings:

```python
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
```

The default Ollama URL is suitable when the API runs directly on the same machine as Ollama.

When the API runs inside Docker Desktop, `host.docker.internal` allows the container to reach a service running on the Windows host.

The Docker Compose configuration overrides the Ollama URL:

```yaml
environment:
  OLLAMA_BASE_URL: http://host.docker.internal:11434
```

## 4. Verify Docker-to-Ollama connectivity

Start the production services:

```bash
docker compose -f production/docker-compose.yml up -d
```

Check the running containers:

```bash
docker compose -f production/docker-compose.yml ps
```

Test whether the API container can reach Ollama:

```bash
docker compose -f production/docker-compose.yml exec rag-api \
  python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags', timeout=10).read().decode())"
```

A successful response contains a JSON object listing the models available on the Ollama server.

For example:

```json
{
  "models": [
    {
      "name": "qwen2.5:3b"
    }
  ]
}
```

The actual response may contain additional model metadata.

## 5. Test LLM generation from the API container

Connectivity alone does not prove that the model can generate responses. Send a generation request to Ollama:

```bash
docker compose -f production/docker-compose.yml exec rag-api \
  python -c "import json, urllib.request; data=json.dumps({'model':'qwen2.5:3b','prompt':'Reply with exactly: Ollama inference works.','stream':False}).encode(); req=urllib.request.Request('http://host.docker.internal:11434/api/generate', data=data, headers={'Content-Type':'application/json'}); print(urllib.request.urlopen(req, timeout=120).read().decode())"
```

A successful inference response contains fields such as:

- `model`: the model used.
- `response`: the generated text.
- `done`: whether generation completed.
- `total_duration`: total generation duration in nanoseconds.

The model may not follow the prompt exactly. For this project, the important checks are that the endpoint returns successfully, the response contains generated text, and `done` is `true`.

## 6. Troubleshooting

### Ollama command not found in WSL

If you installed Ollama on Windows, the `ollama` command may not be available inside your WSL distribution.

Run Ollama commands in Windows PowerShell instead. You do not need to install another Ollama instance in WSL when the Docker container can already reach the Windows host.

### Connection refused or timeout

Check that:

1. Ollama is installed and running on Windows.
2. The Ollama service is listening on port `11434`.
3. The container uses `http://host.docker.internal:11434`.
4. Windows firewall settings allow the Docker-to-host connection.

Test connectivity again using the `/api/tags` endpoint.

### Model not found

Check the available models:

```powershell
ollama list
```

If Qwen is missing, download it:

```powershell
ollama pull qwen2.5:3b
```

### Model generation takes too long

The first request may take longer because Ollama needs to load the model into memory. Subsequent requests may be faster while the model remains loaded.

## 7. Verified environment

The following configuration was verified during development:

| Component                  | Verified configuration                   |
| -------------------------- | ---------------------------------------- |
| Host operating system      | Windows                                  |
| Ollama version             | 0.5.11                                   |
| API runtime                | Docker container                         |
| Docker-to-host address     | `host.docker.internal:11434`             |
| Generation model           | `qwen2.5:3b`                             |
| Model quantization         | Q4_K_M                                   |
| Configured embedding model | `sentence-transformers/all-MiniLM-L6-v2` |

The Docker container successfully retrieved the Ollama model list and completed a direct generation request using Qwen 2.5 3B.

These checks verify host connectivity and model inference. They do not, by themselves, verify the complete RAG query workflow through the FastAPI endpoint.
