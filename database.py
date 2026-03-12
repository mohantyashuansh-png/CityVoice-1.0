"""
GovTech CRM - Database Layer
SQLite-based storage. Zero external dependencies beyond Python stdlib.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "govtech_complaints.db"


def get_connection():
    """Returns a SQLite connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
    return conn


def init_db():
    """Creates tables if they don't exist. Call once at startup."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id              TEXT PRIMARY KEY,
            submitted_at    TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'PENDING',

            -- Raw input
            original_text   TEXT NOT NULL,
            
            -- AI-processed fields
            detected_language   TEXT,
            language_code       TEXT,
            translated_text     TEXT,
            category            TEXT,
            department          TEXT,
            priority            TEXT,
            priority_reason     TEXT,
            summary             TEXT,
            location_hint       TEXT,
            keywords            TEXT,   -- stored as JSON array string
            acknowledgment_message TEXT,
            
            -- Tracking
            assigned_officer    TEXT,
            resolution_notes    TEXT,
            resolved_at         TEXT,
            
            -- Submitter (optional)
            submitter_name      TEXT,
            submitter_contact   TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS status_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id    TEXT NOT NULL,
            old_status      TEXT,
            new_status      TEXT NOT NULL,
            changed_at      TEXT NOT NULL,
            changed_by      TEXT,
            note            TEXT,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


# ─── CORE ENDPOINTS ──────────────────────────────────────────────────────────

def save_complaint(ai_result: dict, submitter_name: str = None, submitter_contact: str = None) -> str:
    """
    Saves a processed complaint to the database.
    Returns the complaint ID.
    """
    complaint_id = "CMP-" + str(uuid.uuid4()).upper()[:8]
    now = datetime.utcnow().isoformat() + "Z"
    
    conn = get_connection()
    conn.execute("""
        INSERT INTO complaints (
            id, submitted_at, updated_at, status,
            original_text, detected_language, language_code,
            translated_text, category, department, priority,
            priority_reason, summary, location_hint, keywords,
            acknowledgment_message, submitter_name, submitter_contact
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        complaint_id, now, now, "PENDING",
        ai_result.get("original_text", ""),
        ai_result.get("detected_language"),
        ai_result.get("language_code"),
        ai_result.get("translated_text"),
        ai_result.get("category"),
        ai_result.get("department"),
        ai_result.get("priority"),
        ai_result.get("priority_reason"),
        ai_result.get("summary"),
        ai_result.get("location_hint"),
        json.dumps(ai_result.get("keywords", [])),
        ai_result.get("acknowledgment_message"),
        submitter_name,
        submitter_contact
    ))
    
    # Log initial status
    conn.execute("""
        INSERT INTO status_history (complaint_id, old_status, new_status, changed_at, changed_by, note)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (complaint_id, None, "PENDING", now, "SYSTEM", "Complaint submitted and AI-processed"))
    
    conn.commit()
    conn.close()
    
    return complaint_id


def get_all_complaints(
    status_filter: str = None,
    category_filter: str = None,
    priority_filter: str = None,
    limit: int = 100,
    offset: int = 0
) -> list:
    """
    Returns all complaints as a list of dicts.
    Supports optional filtering by status, category, priority.
    """
    conn = get_connection()
    
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter.upper())
    if category_filter:
        query += " AND category = ?"
        params.append(category_filter.upper())
    if priority_filter:
        query += " AND priority = ?"
        params.append(priority_filter.upper())
    
    query += " ORDER BY submitted_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    result = []
    for row in rows:
        d = dict(row)
        # Parse keywords back to list
        try:
            d["keywords"] = json.loads(d["keywords"]) if d["keywords"] else []
        except Exception:
            d["keywords"] = []
        result.append(d)
    
    return result


def get_complaint_by_id(complaint_id: str) -> dict | None:
    """Returns a single complaint dict, or None if not found."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    
    if not row:
        conn.close()
        return None
    
    d = dict(row)
    try:
        d["keywords"] = json.loads(d["keywords"]) if d["keywords"] else []
    except Exception:
        d["keywords"] = []
    
    # Fetch status history
    history = conn.execute(
        "SELECT * FROM status_history WHERE complaint_id = ? ORDER BY changed_at ASC",
        (complaint_id,)
    ).fetchall()
    d["status_history"] = [dict(h) for h in history]
    
    conn.close()
    return d


def update_complaint_status(
    complaint_id: str,
    new_status: str,
    changed_by: str = "OFFICER",
    note: str = None,
    resolution_notes: str = None,
    assigned_officer: str = None
) -> bool:
    """
    Updates complaint status and logs to history.
    Valid statuses: PENDING → ASSIGNED → IN_PROGRESS → RESOLVED → REJECTED
    """
    valid_statuses = {"PENDING", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "REJECTED"}
    if new_status.upper() not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
    
    conn = get_connection()
    existing = conn.execute("SELECT status FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    
    if not existing:
        conn.close()
        return False
    
    old_status = existing["status"]
    now = datetime.utcnow().isoformat() + "Z"
    
    update_fields = ["status = ?", "updated_at = ?"]
    update_vals = [new_status.upper(), now]
    
    if resolution_notes:
        update_fields.append("resolution_notes = ?")
        update_vals.append(resolution_notes)
    if assigned_officer:
        update_fields.append("assigned_officer = ?")
        update_vals.append(assigned_officer)
    if new_status.upper() == "RESOLVED":
        update_fields.append("resolved_at = ?")
        update_vals.append(now)
    
    update_vals.append(complaint_id)
    conn.execute(f"UPDATE complaints SET {', '.join(update_fields)} WHERE id = ?", update_vals)
    
    conn.execute("""
        INSERT INTO status_history (complaint_id, old_status, new_status, changed_at, changed_by, note)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (complaint_id, old_status, new_status.upper(), now, changed_by, note))
    
    conn.commit()
    conn.close()
    return True


def get_analytics() -> dict:
    """Returns aggregated analytics for the dashboard."""
    conn = get_connection()
    
    total = conn.execute("SELECT COUNT(*) as c FROM complaints").fetchone()["c"]
    
    by_status = conn.execute("""
        SELECT status, COUNT(*) as count FROM complaints GROUP BY status
    """).fetchall()
    
    by_category = conn.execute("""
        SELECT category, COUNT(*) as count FROM complaints GROUP BY category ORDER BY count DESC
    """).fetchall()
    
    by_priority = conn.execute("""
        SELECT priority, COUNT(*) as count FROM complaints GROUP BY priority
    """).fetchall()
    
    by_language = conn.execute("""
        SELECT detected_language, COUNT(*) as count FROM complaints 
        GROUP BY detected_language ORDER BY count DESC LIMIT 10
    """).fetchall()
    
    avg_resolution = conn.execute("""
        SELECT AVG(
            (julianday(resolved_at) - julianday(submitted_at)) * 24
        ) as avg_hours
        FROM complaints WHERE resolved_at IS NOT NULL
    """).fetchone()["avg_hours"]
    
    conn.close()
    
    return {
        "total_complaints": total,
        "by_status": {row["status"]: row["count"] for row in by_status},
        "by_category": {row["category"]: row["count"] for row in by_category},
        "by_priority": {row["priority"]: row["count"] for row in by_priority},
        "by_language": {row["detected_language"]: row["count"] for row in by_language},
        "avg_resolution_hours": round(avg_resolution, 1) if avg_resolution else None
    }
