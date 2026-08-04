import os
import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes
from dotenv import load_dotenv

from app.db import init_db, FDS_DB_PATH
from app.mcp_client import login_as_admin
from app.consumer import start_stream_consumer, stop_stream_consumer
from app.agent import fds_process_chain

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    print("FDS Agent Server: Initializing FDS database...")
    init_db()
    
    # Establish connection and log in as admin to the MCP server
    print("FDS Agent Server: Logging in to MCP server...")
    await login_as_admin()
    
    # Start the Snowflake stream consumer
    print("FDS Agent Server: Starting Snowflake stream consumer...")
    start_stream_consumer()
    
    yield
    
    # Shutdown tasks
    print("FDS Agent Server: Stopping Snowflake stream consumer...")
    stop_stream_consumer()

app = FastAPI(
    title="FDS Agent Server",
    version="1.0",
    description="Fraud Detection System (FDS) Agent using LangServe with Snowflake Cortex",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/")
async def redirect_to_docs():
    return {"message": "FDS Agent Server is running. Access LangServe playground at /fds/playground"}

@app.get("/fds/history")
async def get_fds_history(limit: int = 50):
    """Retrieve FDS fraud analysis history from the local SQLite database."""
    if not os.path.exists(FDS_DB_PATH):
        return []
    try:
        conn = sqlite3.connect(FDS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions_analysis ORDER BY analyzed_at DESC LIMIT ?", 
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Register LangServe routes for the FDS process chain
add_routes(
    app,
    fds_process_chain,
    path="/fds",
)
