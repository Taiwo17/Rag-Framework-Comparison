import asyncio
import os
import time
import math
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import json
from urllib.request import Request as URLRequest, urlopen
from urllib.error import URLError
from fastapi.responses import JSONResponse
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from secrets import compare_digest
from pydantic import BaseModel, Field
from pydantic import field_validator


from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from urllib.parse import urlsplit


# Load production environment variables
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / "production" / ".env")


# Application configuration
def get_required_secret(name: str) -> str:
    value = os.getenv(name)

    if not value or not value.strip():
        raise RuntimeError(
            f"Required environment variable {name} is not configured."
        )

    return value


def get_positive_int(name: str, default: str) -> int:
    value = os.getenv(name, default)

    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"{name} must be a valid integer. Received: {value!r}"
        ) from exc

    if result <= 0:
        raise RuntimeError(
            f"{name} must be greater than zero. Received: {result}"
        )

    return result

def get_positive_float(name: str, default: str) -> float:
    value = os.getenv(name, default)

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"{name} must be a valid number. Received: {value!r}"
        ) from exc

    if not math.isfinite(result) or result <= 0:
        raise RuntimeError(
            f"{name} must be a finite number greater than zero. "
            f"Received: {result}"
        )

    return result


def validate_http_url(name: str, value: str) -> str:
    try:
        parsed = urlsplit(value)
        valid_url = (
            parsed.scheme in {"http", "https"}
            and parsed.hostname is not None
        )

        # Accessing port also detects malformed port values.
        if parsed.port is not None:
            valid_url = valid_url and 1 <= parsed.port <= 65535

    except ValueError as exc:
        raise RuntimeError(
            f"{name} contains an invalid URL: {value!r}"
        ) from exc

    if not valid_url:
        raise RuntimeError(
            f"{name} must be a valid HTTP or HTTPS URL. "
            f"Received: {value!r}"
        )

    return value


APP_NAME = os.getenv(
    "APP_NAME",
    "Springer Capital RAG API",
).strip()

if not APP_NAME:
    raise RuntimeError("APP_NAME cannot be empty.")

OLLAMA_BASE_URL = validate_http_url(
    "OLLAMA_BASE_URL",
    os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip(),
)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip()
if not OLLAMA_MODEL:
    raise RuntimeError("OLLAMA_MODEL cannot be empty.")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
).strip()

if not EMBEDDING_MODEL:
    raise RuntimeError("EMBEDDING_MODEL cannot be empty.")

VECTOR_STORE_PATH = Path(
    os.getenv(
        "VECTOR_STORE_PATH",
        "evaluation/vector_stores/langchain",
    )
)

if not VECTOR_STORE_PATH.is_absolute():
    VECTOR_STORE_PATH = BASE_DIR / VECTOR_STORE_PATH

TOP_K = get_positive_int("TOP_K", "4")

LLM_GENERATION_TIMEOUT_SECONDS = get_positive_float(
    "LLM_GENERATION_TIMEOUT_SECONDS",
    "360",
)

MAX_ADMITTED_LLM_REQUESTS = get_positive_int(
    "MAX_ADMITTED_LLM_REQUESTS",
    "3",
)

LLM_ADMISSION_TIMEOUT_SECONDS = get_positive_float(
    "LLM_ADMISSION_TIMEOUT_SECONDS",
    "0.1",
)

LLM_QUEUE_WAIT_TIMEOUT_SECONDS = get_positive_float(
    "LLM_QUEUE_WAIT_TIMEOUT_SECONDS",
    "30",
)

HOST = os.getenv("HOST", "0.0.0.0").strip()
if not HOST:
    raise RuntimeError("HOST cannot be empty.")

PORT = get_positive_int("PORT", "8000")
if PORT > 65535:
    raise RuntimeError("PORT must not exceed 65535.")

API_KEY = get_required_secret("API_KEY")
REDIS_PASSWORD = get_required_secret("REDIS_PASSWORD")

# Limits the total number of requests admitted into RAG processing.
# This includes the request generating and requests waiting.
LLM_ADMISSION_SEMAPHORE = asyncio.BoundedSemaphore(
    MAX_ADMITTED_LLM_REQUESTS
)

# Only one request can generate an answer at a time.
LLM_SEMAPHORE = asyncio.BoundedSemaphore(1)

API_KEY_HEADER = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def get_api_key_identifier(request: Request):
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return get_remote_address(request)

    return hashlib.sha256(api_key.encode()).hexdigest()


REDIS_URL = f"redis://:{REDIS_PASSWORD}@redis:6379/0"

limiter = Limiter(
    key_func=get_api_key_identifier,
    default_limits=[],
    storage_uri=REDIS_URL,
)


async def verify_api_key(api_key: str | None = Security(API_KEY_HEADER)):
    if not api_key or not compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key.",
        )

    return api_key


SYSTEM_PROMPT = """You are a technical assistant answering questions about DevOps.

Answer the user's question using only the supplied context.

Instructions:
- Give a clear, accurate, and direct answer.
- Do not introduce facts that are not supported by the context.
- If the context does not contain enough information, state that clearly.
- Do not invent details or assumptions.
- Keep the answer concise and relevant.
"""

# API request model
class QueryRequest(BaseModel):
    model_config = {"extra": "forbid"}

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Question to ask the RAG system",
    )

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value



# API response model
class SourceDocument(BaseModel):
    chunk_id: str | None = None
    source: str
    page: int | None = None
    score: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceDocument]
    retrieved_chunks: int
    retrieval_time_seconds: float
    generation_time_seconds: float
    execution_time_seconds: float

# Shared application state
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading RAG components...")

    if not VECTOR_STORE_PATH.exists():
        raise RuntimeError(
            f"Vector store not found: {VECTOR_STORE_PATH}"
        )

    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        vector_store = FAISS.load_local(
            str(VECTOR_STORE_PATH),
            embeddings,
            allow_dangerous_deserialization=True,
        )

        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_predict=200,
            num_ctx=4096,
            keep_alive="30m",
        )

        app.state.vector_store = vector_store
        app.state.llm = llm

        print("RAG components loaded successfully.")

    except Exception as exc:
        raise RuntimeError(
            f"Failed to initialise RAG components: {exc}"
        ) from exc

    yield

    print("Shutting down RAG API...")


# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    description="Production-ready RAG API powered by LangChain.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# Health-check endpoint
# Health-check endpoints

@app.get("/health/live")
async def liveness_check():
    """Check whether the API process is running."""
    return {
        "status": "alive",
        "service": APP_NAME,
    }


def check_ollama():
    """Check Ollama connectivity and configured model availability."""
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags"

    request = URLRequest(
        url,
        headers={"Accept": "application/json"},
    )

    try:
        with urlopen(request, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))

        models = data.get("models", [])

        available_models = {
            model.get("name")
            for model in models
            if isinstance(model, dict)
        }

        return True, OLLAMA_MODEL in available_models

    except (URLError, TimeoutError, OSError, ValueError):
        return False, False


@app.get("/health/ready")
@app.get("/health")
async def readiness_check():
    """Check whether the API is ready to process RAG requests."""

    vector_store_loaded = hasattr(
        app.state, "vector_store"
    )

    llm_loaded = hasattr(
        app.state, "llm"
    )

    ollama_reachable, ollama_model_available = await asyncio.to_thread(
        check_ollama
    )

    ready = all([
        vector_store_loaded,
        llm_loaded,
        ollama_reachable,
        ollama_model_available,
    ])

    result = {
        "status": "ready" if ready else "not_ready",
        "service": APP_NAME,
        "checks": {
            "vector_store_loaded": vector_store_loaded,
            "llm_client_initialized": llm_loaded,
            "ollama_reachable": ollama_reachable,
            "ollama_model_available": ollama_model_available,
        },
    }

    return JSONResponse(
        content=result,
        status_code=200 if ready else 503,
    )

# RAG query endpoint
@app.post("/api/v1/query", response_model=QueryResponse)
@limiter.limit("5/minute")
async def query_rag(
    request: Request,
    payload: QueryRequest,
    _: str = Security(verify_api_key),
):
    question = payload.question.strip()

    start_time = time.perf_counter()
    # retrieval_start = time.perf_counter()

    admission_acquired = False
    generation_acquired = False

    try:
        # Admit the request before starting retrieval.
        try:
            await asyncio.wait_for(
                LLM_ADMISSION_SEMAPHORE.acquire(),
                timeout=LLM_ADMISSION_TIMEOUT_SECONDS,
            )
            admission_acquired = True

        except TimeoutError:
            logger.warning(
                "Request rejected: LLM admission capacity reached"
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "The RAG service is currently busy. "
                    "Please retry shortly."
                ),
            )

        # Start retrieval timing after admission.
        retrieval_start = time.perf_counter()

        # Retrieve relevant documents.
        retrieved_results = (
            app.state.vector_store.similarity_search_with_score(
                question,
                k=TOP_K,
            )
        )

        retrieval_time = time.perf_counter() - retrieval_start

        if not retrieved_results:
            raise HTTPException(
                status_code=404,
                detail="No relevant documents were found.",
            )

        context_parts = []
        sources = []

        for document, score in retrieved_results:
            page = document.metadata.get("page")
            source = document.metadata.get(
                "source",
                "devops-rag-corpus.pdf",
            )

            context_parts.append(
                f"[Source: {source}, page {page}]\n"
                f"{document.page_content}"
            )

            sources.append(
                SourceDocument(
                    chunk_id=document.id,
                    source=source,
                    page=page,
                    score=float(score),
                )
            )

        context = "\n\n".join(context_parts)

        # Prepare the LLM prompt.
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"""Context:

{context}

Question:
{question}

Answer:"""
            ),
        ]

        # Wait for the single available generation slot.
        try:
            await asyncio.wait_for(
                LLM_SEMAPHORE.acquire(),
                timeout=LLM_QUEUE_WAIT_TIMEOUT_SECONDS,
            )
            generation_acquired = True

        except TimeoutError:
            logger.warning(
                "Request rejected after waiting %s seconds "
                "for the LLM generation slot",
                LLM_QUEUE_WAIT_TIMEOUT_SECONDS,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "The language model is currently busy. "
                    "Please retry shortly."
                ),
            )

        # Measure generation after obtaining the slot.
        generation_start = time.perf_counter()

        try:
            response = await asyncio.wait_for(
                app.state.llm.ainvoke(messages),
                timeout=LLM_GENERATION_TIMEOUT_SECONDS,
            )
        finally:
            LLM_SEMAPHORE.release()
            generation_acquired = False

        generation_time = time.perf_counter() - generation_start
        execution_time = time.perf_counter() - start_time

        return QueryResponse(
            question=question,
            answer=response.content,
            sources=sources,
            retrieved_chunks=len(retrieved_results),
            retrieval_time_seconds=round(retrieval_time, 2),
            generation_time_seconds=round(generation_time, 2),
            execution_time_seconds=round(execution_time, 2),
        )

    except HTTPException:
        raise

    except TimeoutError:
        logger.warning(
            "LLM generation timed out after %s seconds",
            LLM_GENERATION_TIMEOUT_SECONDS,
        )

        raise HTTPException(
            status_code=504,
            detail=(
                "The language model took too long to generate "
                "a response. Please try again."
            ),
        )

    except Exception:
        logger.exception("Unexpected error during RAG query")

        raise HTTPException(
            status_code=500,
            detail=(
                "An internal error occurred while processing "
                "your request."
            ),
        )

    finally:
        # Release permits even if retrieval, generation or response
        # construction raises an exception.
        if generation_acquired:
            LLM_SEMAPHORE.release()

        if admission_acquired:
            LLM_ADMISSION_SEMAPHORE.release() 

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "production.api.main:app",
        host=HOST,
        port=PORT,
        reload=False,
    )