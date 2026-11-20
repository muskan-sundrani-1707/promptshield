from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect
from app.database.connection import init_db, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()          # runs once when the server starts
    yield


app = FastAPI(title="PromptShield API", version="0.1.0", lifespan=lifespan)

# Allow the React dev server (Vite, port 5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Frontend uses this to check that the backend is alive."""
    tables = sorted(inspect(engine).get_table_names())
    return {"status": "ok", "app": "PromptShield", "tables": tables}