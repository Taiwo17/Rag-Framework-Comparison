import asyncio
import os
import time
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
import logging
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


# Load production environment variables
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / "production" / ".env")


# Application configuration
APP_NAME = os.getenv("APP_NAME", "Springer Capital RAG API")
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
VECTOR_STORE_PATH = Path(
    os.getenv(
        "VECTOR_STORE_PATH",
        "evaluation/vector_stores/langchain",
    )
)

if not VECTOR_STORE_PATH.is_absolute():
    VECTOR_STORE_PATH = BASE_DIR / VECTOR_STORE_PATH

TOP_K = int(os.getenv("TOP_K", "4"))
LLM_SEMAPHORE = asyncio.Semaphore(1)

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise RuntimeError("API_KEY environment variable is not configured.")

API_KEY_HEADER = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)

def get_api_key_identifier(request: Request):
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return get_remote_address(request)

    return hashlib.sha256(
        api_key.encode()
    ).hexdigest()


REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

if not REDIS_PASSWORD:
    raise RuntimeError("REDIS_PASSWORD environment variable is not configured.")

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

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty.")
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
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": APP_NAME,
        "vector_store_loaded": hasattr(
            app.state, "vector_store"
        ),
        "llm_loaded": hasattr(app.state, "llm"),
    }

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
    retrieval_start = time.perf_counter()

    try:
        # Retrieve relevant documents
        retrieved_results = (
            app.state.vector_store.similarity_search_with_score(
                question,
                k=TOP_K,
            )
        )

        retrieval_time = time.perf_counter() - retrieval_start

        generation_start = time.perf_counter()

        

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

        # Generate an answer
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

        async with LLM_SEMAPHORE:
            response = await app.state.llm.ainvoke(messages)

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

    except Exception:
        logger.exception("Unexpected error during RAG query")

        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your request.",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "production.api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )