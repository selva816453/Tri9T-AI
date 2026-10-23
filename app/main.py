"""
FastAPI application entry point.
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.api import documents, generations, selections, dashboard
from app.core.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

app = FastAPI(
    title="CT-200 QA Document System",
    description=(
        "Backend API for ingesting, versioning, and querying the CardioTrack CT-200 "
        "manual, with LLM-powered QA test case generation and staleness detection."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(selections.router)
app.include_router(generations.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def startup() -> None:
    os.makedirs("data", exist_ok=True)
    init_db()
    logging.getLogger(__name__).info("Database initialised.")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "CT-200 QA System"}


@app.get("/", response_class=HTMLResponse, tags=["system"], include_in_schema=False)
def homepage():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>CT-200 QA System</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #0f3460 0%, #16213e 50%, #1a1a2e 100%);
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      color: #e0e0e0;
    }
    .card {
      background: rgba(255,255,255,0.07);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 20px;
      padding: 48px 56px;
      max-width: 700px;
      width: 100%;
      box-shadow: 0 25px 60px rgba(0,0,0,0.5);
    }
    .badge {
      display: inline-block;
      background: #e94560;
      color: white;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 20px;
      letter-spacing: 1px;
      margin-bottom: 16px;
    }
    h1 { font-size: 28px; font-weight: 700; color: #ffffff; margin-bottom: 6px; }
    .subtitle { color: #a0aec0; font-size: 14px; margin-bottom: 32px; }
    .status {
      display: flex; align-items: center; gap: 8px;
      background: rgba(72,199,116,0.12);
      border: 1px solid rgba(72,199,116,0.3);
      border-radius: 8px; padding: 10px 16px;
      font-size: 13px; color: #48c774; margin-bottom: 28px;
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: #48c774;
           animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }
    h2 { font-size: 13px; font-weight: 600; color: #718096;
         text-transform: uppercase; letter-spacing: 1px; margin-bottom: 14px; }
    .links { display: grid; gap: 10px; margin-bottom: 28px; }
    a.link-btn {
      display: flex; justify-content: space-between; align-items: center;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 10px; padding: 14px 18px;
      color: #e2e8f0; text-decoration: none; font-size: 14px;
      transition: all 0.2s;
    }
    a.link-btn:hover {
      background: rgba(255,255,255,0.1);
      border-color: rgba(255,255,255,0.25);
      transform: translateX(4px);
      color: #ffffff;
    }
    .link-btn span.icon { font-size: 18px; margin-right: 12px; }
    .link-btn span.arrow { color: #4a5568; font-size: 18px; }
    .link-btn:hover .arrow { color: #e94560; }
    .tag {
      font-size: 11px; padding: 2px 8px; border-radius: 4px;
      font-weight: 600;
    }
    .tag-blue { background: rgba(66,153,225,0.2); color: #63b3ed; }
    .tag-green { background: rgba(72,199,116,0.2); color: #48c774; }
    .tag-purple { background: rgba(159,122,234,0.2); color: #b794f4; }
    .footer { color: #4a5568; font-size: 12px; text-align: center; margin-top: 24px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">TRI9T AI · INTERNSHIP</div>
    <h1>CardioTrack CT-200 QA System</h1>
    <p class="subtitle">Document versioning · LLM test case generation · Staleness detection</p>

    <div class="status">
      <div class="dot"></div>
      API server is running — all systems operational
    </div>

    <h2>Quick Access</h2>
    <div class="links">
      <a class="link-btn" href="/docs">
        <span><span class="icon">📘</span>Interactive API Docs (Swagger UI)</span>
        <span class="arrow">→</span>
      </a>
      <a class="link-btn" href="/redoc">
        <span><span class="icon">📄</span>ReDoc Documentation</span>
        <span class="arrow">→</span>
      </a>
      <a class="link-btn" href="/health">
        <span><span class="icon">💚</span>Health Check</span>
        <span class="arrow">→</span>
      </a>
      <a class="link-btn" href="/api/versions?document_id=CT200-MAN-001">
        <span><span class="icon">📦</span>Document Versions (CT200-MAN-001)</span>
        <span class="arrow">→</span>
      </a>
      <a class="link-btn" href="/api/nodes?document_id=CT200-MAN-001">
        <span><span class="icon">🌲</span>Parsed Document Tree (latest)</span>
        <span class="arrow">→</span>
      </a>
      <a class="link-btn" href="/api/search?q=pressurisation&document_id=CT200-MAN-001">
        <span><span class="icon">🔍</span>Search: "pressurisation"</span>
        <span class="arrow">→</span>
      </a>
      <a class="link-btn" href="/api/generations">
        <span><span class="icon">🤖</span>Generated Test Cases</span>
        <span class="arrow">→</span>
      </a>
    </div>

    <div class="footer">CT-200 QA System · FastAPI + SQLAlchemy + MongoDB · Tri9T AI Assignment</div>
  </div>
</body>
</html>
"""
