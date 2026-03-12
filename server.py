"""
GovTech CRM - FastAPI HTTP Server
Wraps the api.py endpoints as REST endpoints for frontend consumption.

INSTALL:  pip install fastapi uvicorn
RUN:      uvicorn server:app --reload --port 8000

SWAGGER DOCS: http://localhost:8000/docs
"""

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("FastAPI not installed. Run: pip install fastapi uvicorn")

from typing import Optional
from api import (
    submit_complaint,
    get_all_complaints,
    track_complaint,
    update_status,
    get_analytics,
)

if HAS_FASTAPI:
    app = FastAPI(
        title="GovTech CRM API",
        description="Multilingual Citizen Complaint & Governance CRM Backend",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── REQUEST MODELS ──────────────────────────────────────────────────────

    class ComplaintRequest(BaseModel):
        text: str
        submitter_name: Optional[str] = None
        submitter_contact: Optional[str] = None

    class StatusUpdateRequest(BaseModel):
        new_status: str
        officer_name: Optional[str] = "Officer"
        note: Optional[str] = None
        resolution_notes: Optional[str] = None

    # ─── ROUTES ──────────────────────────────────────────────────────────────

    @app.get("/")
    def root():
        return {
            "service": "GovTech CRM API",
            "status": "running",
            "endpoints": {
                "POST /complaints": "Submit a new complaint (any language)",
                "GET /complaints": "List all complaints (with filters)",
                "GET /complaints/{id}": "Track a specific complaint",
                "PATCH /complaints/{id}/status": "Update complaint status",
                "GET /analytics": "Get dashboard analytics"
            }
        }

    @app.post("/complaints")
    def api_submit_complaint(request: ComplaintRequest):
        """Submit a new citizen complaint in any language."""
        result = submit_complaint(
            text=request.text,
            submitter_name=request.submitter_name,
            submitter_contact=request.submitter_contact
        )
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        return result

    @app.get("/complaints")
    def api_get_complaints(
        status: Optional[str] = Query(None, description="PENDING | ASSIGNED | IN_PROGRESS | RESOLVED | REJECTED"),
        category: Optional[str] = Query(None, description="WATER | ROADS | WASTE | ELECTRICITY | HEALTH | PARKS | NOISE | SAFETY | GENERAL"),
        priority: Optional[str] = Query(None, description="CRITICAL | HIGH | MEDIUM | LOW"),
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0)
    ):
        """List all complaints with optional filters."""
        return get_all_complaints(status=status, category=category, priority=priority, limit=limit, offset=offset)

    @app.get("/complaints/{complaint_id}")
    def api_track_complaint(complaint_id: str):
        """Track a specific complaint by ID."""
        result = track_complaint(complaint_id)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @app.patch("/complaints/{complaint_id}/status")
    def api_update_status(complaint_id: str, request: StatusUpdateRequest):
        """Update a complaint's status (officer-facing)."""
        result = update_status(
            complaint_id=complaint_id,
            new_status=request.new_status,
            officer_name=request.officer_name,
            note=request.note,
            resolution_notes=request.resolution_notes
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    @app.get("/analytics")
    def api_analytics():
        """Get aggregated analytics for the dashboard."""
        result = get_analytics()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
