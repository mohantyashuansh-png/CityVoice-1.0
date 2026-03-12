"""
GovTech CRM - Public API Endpoints
Architecture: Cloud-to-Edge AI (Gemini → Local Qwen Fallback)
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime
from ai_engine import process_complaint
from database import (
    init_db,
    save_complaint,
    get_all_complaints as db_get_all,
    get_complaint_by_id,
    update_complaint_status,
    get_analytics as db_get_analytics,
)

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut


# ─── INIT ────────────────────────────────────────────────────────────────────

init_db()


# ─── GEOLOCATION HELPER ──────────────────────────────────────────────────────

def get_coordinates(location_hint):
    try:
        # User agent is required by Nominatim
        geolocator = Nominatim(user_agent="nagpur_govtech_ashutosh")
        query = f"{location_hint}, Nagpur, Maharashtra, India"
        location = geolocator.geocode(query, timeout=5)
        if location:
            return location.latitude, location.longitude
        return 21.1458, 79.0882  # Default to Nagpur Center
    except:
        return 21.1458, 79.0882


# ─── THE TWO CORE ENDPOINTS YOUR FRONTEND CALLS ──────────────────────────────

def submit_complaint(text):
    # 1. Get AI Response
    ai_raw = process_complaint(text) 
    
    # THE FIX: Check if it's already a dictionary. If it is, use it directly!
    if isinstance(ai_raw, dict):
        result = ai_raw
    else:
        # If it's a string, then decode it
        import json
        result = json.loads(ai_raw)
    
    # 2. Get Geolocation
    loc_hint = result.get("location_hint", "Nagpur")
    lat, lon = get_coordinates(loc_hint)
    
    # ... KEEP THE REST OF YOUR DATABASE INSERTION CODE EXACTLY THE SAME ...
    
    # 3. Database Insertion
    conn = sqlite3.connect("govtech_complaints.db")
    cursor = conn.cursor()
    
    comp_id = f"CMP-{str(uuid.uuid4())[:8].upper()}"
    now = datetime.utcnow().isoformat() + "Z"
    
# !!! Added updated_at to satisfy the strict database schema !!!
    cursor.execute("""
        INSERT INTO complaints 
        (id, original_text, translated_text, category, priority, status, summary, submitted_at, updated_at, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        comp_id,
        text,
        result['translated_text'],
        result['category'],
        result['priority'],
        "PENDING",
        result['translated_text'][:50],
        now,
        now, # This is for updated_at
        lat,
        lon
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "complaint_id": comp_id,
        "department": result['category'],
        "latitude": lat,
        "longitude": lon,
        "detected_language": result.get("detected_language", "Unknown"),
        "translated_text": result['translated_text'],
        "category": result['category'],
        "priority": result['priority'],
        "acknowledgment_message": "Complaint received and mapped successfully."
    }


def get_all_complaints(
    status: str = None,
    category: str = None,
    priority: str = None,
    limit: int = 100,
    offset: int = 0
) -> dict:
    """
    PRIMARY ENDPOINT: Fetch all complaints with optional filters.
    """
    try:
        complaints = db_get_all(
            status_filter=status,
            category_filter=category,
            priority_filter=priority,
            limit=limit,
            offset=offset
        )
        return {
            "success": True,
            "count": len(complaints),
            "complaints": complaints
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "complaints": []
        }


# ─── ADDITIONAL ENDPOINTS ─────────────────────────────────────────────────────

def track_complaint(complaint_id: str) -> dict:
    """
    Citizen-facing: Track a complaint's current status and history.
    """
    try:
        complaint = get_complaint_by_id(complaint_id)
        if not complaint:
            return {"success": False, "error": f"Complaint '{complaint_id}' not found"}
        return {"success": True, "complaint": complaint}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_status(
    complaint_id: str,
    new_status: str,
    officer_name: str = "Officer",
    note: str = None,
    resolution_notes: str = None
) -> dict:
    """
    Officer-facing: Update complaint status.
    Valid transitions: PENDING → ASSIGNED → IN_PROGRESS → RESOLVED | REJECTED
    """
    try:
        success = update_complaint_status(
            complaint_id=complaint_id,
            new_status=new_status,
            changed_by=officer_name,
            note=note,
            resolution_notes=resolution_notes,
            assigned_officer=officer_name if new_status == "ASSIGNED" else None
        )
        if not success:
            return {"success": False, "error": f"Complaint '{complaint_id}' not found"}
        return {"success": True, "complaint_id": complaint_id, "new_status": new_status}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_analytics() -> dict:
    """
    Dashboard endpoint: Returns aggregated stats, City Health Score, and Overload Warnings.
    """
    try:
        base_stats = db_get_analytics()
        
        total = base_stats.get("total_complaints", 0)
        resolved = base_stats.get("by_status", {}).get("RESOLVED", 0)
        
        if total > 0:
            health_score = int((resolved / total) * 100)
        else:
            health_score = 45
            
        overloaded_depts = []
        dept_stats = base_stats.get("by_category", {})
        for dept, count in dept_stats.items():
            if count >= 10:
                overloaded_depts.append(dept)

        enriched_analytics = {
            **base_stats,
            "city_health_score": f"{health_score}/100",
            "health_status": "Good" if health_score > 70 else "Needs Attention" if health_score > 40 else "Critical",
            "overloaded_departments": overloaded_depts,
            "overload_warning_active": len(overloaded_depts) > 0
        }
        
        return {"success": True, "analytics": enriched_analytics}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── DEMO / SMOKE TEST ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("GovTech CRM - Backend Demo (Cloud+Edge)")
    print("=" * 60)
    
    test_complaints = [
        "सड़क पर बड़ा गड्ढा है जिससे दो लोग घायल हो गए हैं",
        "Il y a une fuite d'eau massive dans ma rue depuis 3 jours",
        "The garbage has not been collected for 2 weeks in Block C sector 4",
        "நீர் விநியோகம் 5 நாட்களாக இல்லை, குழந்தைகள் கஷ்டப்படுகிறார்கள்",
        "Broken street light near hospital causing safety risk at night",
    ]
    
    for text in test_complaints:
        print(f"\n📝 Submitting: {text[:50]}...")
        result = submit_complaint(text)
        
        if result["success"]:
            print(f"    ID: {result['complaint_id']}")
            print(f"    Category: {result.get('category')}")
            print(f"    Priority: {result.get('priority')}")
            print(f"    Coordinates: {result.get('latitude')}, {result.get('longitude')}")
        else:
            print(f"   ❌ Error: {result['error']}")