# GovTech CRM — Backend Engine

Multilingual AI-powered complaint processing backend. No external AI SDKs needed — uses only Python stdlib + SQLite.

---

## Architecture

```
Citizen Text (Any Language)
        │
        ▼
  [ ai_engine.py ]  ← "God Prompt" + Claude API
        │  translate → categorize → prioritize → route
        ▼
  [ database.py ]   ← SQLite (govtech_complaints.db)
        │  save → query → update
        ▼
  [ api.py ]        ← Clean functions for your frontend
        │
        ▼
  [ server.py ]     ← FastAPI REST server (optional)
```

---

## Setup

### 1. Set your API Key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 2. Install dependencies (only needed for the HTTP server)
```bash
pip install fastapi uvicorn
```

### 3. Run the demo
```bash
cd govtech_crm
python api.py
```

### 4. Start the HTTP server (for frontend)
```bash
uvicorn server:app --reload --port 8000
# Swagger docs → http://localhost:8000/docs
```

---

## API Reference

### `submit_complaint(text, submitter_name=None, submitter_contact=None)`

Takes raw text in **any language** → returns AI-processed complaint.

```python
from api import submit_complaint

result = submit_complaint("सड़क पर बड़ा गड्ढा है")
print(result["complaint_id"])           # CMP-ABC12345
print(result["category"])               # ROADS
print(result["priority"])               # HIGH
print(result["detected_language"])      # Hindi
print(result["acknowledgment_message"]) # Response IN HINDI
```

**Response shape:**
```json
{
  "success": true,
  "complaint_id": "CMP-A1B2C3D4",
  "category": "ROADS",
  "department": "Public Works Department (PWD)",
  "priority": "HIGH",
  "priority_reason": "Pothole causing injuries to road users",
  "detected_language": "Hindi",
  "language_code": "hi",
  "translated_text": "There is a large pothole on the road",
  "summary": "Large pothole on road causing injuries",
  "location_hint": null,
  "keywords": ["pothole", "road", "injury"],
  "acknowledgment_message": "आपकी शिकायत दर्ज हो गई है। हम 48 घंटों में इसे हल करेंगे।",
  "submitted_at": "2025-07-12T10:30:00Z"
}
```

---

### `get_all_complaints(status, category, priority, limit, offset)`

```python
from api import get_all_complaints

# All complaints
all_c = get_all_complaints()

# Only critical pending complaints
urgent = get_all_complaints(priority="CRITICAL", status="PENDING")

# Water complaints only
water = get_all_complaints(category="WATER")
```

---

### `track_complaint(complaint_id)`

```python
from api import track_complaint

result = track_complaint("CMP-A1B2C3D4")
print(result["complaint"]["status"])
print(result["complaint"]["status_history"])  # Full audit trail
```

---

### `update_status(complaint_id, new_status, officer_name, note, resolution_notes)`

```python
from api import update_status

# Assign
update_status("CMP-A1B2C3D4", "ASSIGNED", "Officer Priya", "Assigned to field team")

# Resolve
update_status("CMP-A1B2C3D4", "RESOLVED", "Officer Priya", 
              resolution_notes="Pothole filled with concrete. Job complete.")
```

**Valid statuses:** `PENDING → ASSIGNED → IN_PROGRESS → RESOLVED | REJECTED`

---

### `get_analytics()`

```python
from api import get_analytics

result = get_analytics()
a = result["analytics"]
# {
#   "total_complaints": 87,
#   "by_status": {"PENDING": 23, "RESOLVED": 51, ...},
#   "by_category": {"ROADS": 30, "WATER": 22, ...},
#   "by_priority": {"HIGH": 40, "CRITICAL": 5, ...},
#   "by_language": {"Hindi": 35, "English": 28, "Tamil": 12, ...},
#   "avg_resolution_hours": 36.5
# }
```

---

## REST Endpoints (server.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/complaints` | Submit complaint |
| `GET`  | `/complaints` | List all (filterable) |
| `GET`  | `/complaints/{id}` | Track complaint |
| `PATCH`| `/complaints/{id}/status` | Update status |
| `GET`  | `/analytics` | Dashboard stats |

---

## Supported Languages

The AI handles **any language** automatically, including (but not limited to):

| Language | Code | Language | Code |
|----------|------|----------|------|
| English | en | Hindi | hi |
| Tamil | ta | Telugu | te |
| French | fr | Spanish | es |
| Arabic | ar | Bengali | bn |
| Marathi | mr | Gujarati | gu |
| Urdu | ur | Punjabi | pa |
| German | de | Portuguese | pt |
| + 100s more | — | — | — |

---

## Categories & Routing

| Category | Routes To |
|----------|-----------|
| WATER | Water Supply & Sewerage Board |
| ROADS | Public Works Department (PWD) |
| WASTE | Municipal Solid Waste Management |
| ELECTRICITY | State Electricity Distribution Company |
| HEALTH | District Health Officer |
| PARKS | Horticulture & Parks Department |
| NOISE | Environmental Control Cell |
| SAFETY | Local Police Station / Municipal Safety Wing |
| GENERAL | Municipal Commissioner's Office |

---

## File Structure

```
govtech_crm/
├── ai_engine.py          ← AI translation + categorization + routing
├── database.py           ← SQLite CRUD operations  
├── api.py                ← Public API functions (call these!)
├── server.py             ← FastAPI HTTP server
├── README.md             ← This file
└── govtech_complaints.db ← Auto-created SQLite database
```
