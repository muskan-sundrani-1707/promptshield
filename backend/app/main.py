from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect
from app.database.connection import init_db, engine
from app.routes import target ,  experiments,evaluation,metrics,defenses,history


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()          # runs once when the server starts
    yield


app = FastAPI(title="PromptShield API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(target.router)   # NEW in Step 3
app.include_router(experiments.router) 
app.include_router(evaluation.router)     
app.include_router(metrics.router)  
app.include_router(defenses.router) 

app.include_router(history.router)      
@app.get("/api/health")
def health():
    tables = sorted(inspect(engine).get_table_names())
    return {"status": "ok", "app": "PromptShield", "tables": tables}