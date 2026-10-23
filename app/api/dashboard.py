"""
Full visual dashboard — complete single-page app at /dashboard
Shows: health, versions, document tree, search, test cases, staleness diff, ingestion
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return open("app/api/dashboard.html", encoding="utf-8").read()
