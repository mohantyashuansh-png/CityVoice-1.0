"""
GovTech CRM - AI Engine (Fault-Tolerant Cloud + Local Fallback)

Architecture:
1️⃣ Primary  → Gemini API (fast cloud inference ~1s)
2️⃣ Fallback → Local Ollama Qwen (offline safe ~4-8s)
3️⃣ Safety   → JSON repair + schema validation
"""

import json
import urllib.request
import urllib.error
import google.generativeai as genai

genai.configure(api_key="AIzaSyBYrPqMGKqzbSGn9r2Nf1MVo7zDLoqxxdU")


# ─────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
Analyze the civic complaint and output ONLY a JSON object.

Categories: WATER, ROADS, WASTE, ELECTRICITY, HEALTH, PARKS, NOISE, SAFETY, GENERAL.
Priorities: CRITICAL, HIGH, MEDIUM, LOW.

Example 1
Input: "Pani nahi aa raha"
Output: {"detected_language": "Hindi", "translated_text": "Water is not coming", "category": "WATER", "priority": "HIGH", "location_hint": "Nagpur"}

Example 2
Input: "Wardha road var khadda ahe"
Output: {"detected_language": "Marathi", "translated_text": "There is a pothole on Wardha road", "category": "ROADS", "priority": "HIGH", "location_hint": "Wardha road"}

Example 3
Input: "Garbage truck didn't come to Dharampeth"
Output: {"detected_language": "English", "translated_text": "Garbage truck didn't come to Dharampeth", "category": "WASTE", "priority": "MEDIUM", "location_hint": "Dharampeth"}

Analyze the user's input based on the pattern above. Return ONLY the JSON object. Do not copy the examples.
"""

# ─────────────────────────────────────────────────────────────
# JSON SAFETY PARSER
# ─────────────────────────────────────────────────────────────

def safe_json_parse(text: str) -> dict:
    """
    Ensures malformed AI responses never crash backend.
    """
    try:
        return json.loads(text)
    except:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except:
            return {}


# ─────────────────────────────────────────────────────────────
# PRIMARY ENGINE: GEMINI CLOUD
# ─────────────────────────────────────────────────────────────

def call_gemini_api(user_text: str, api_key: str) -> dict:
    """
    Ultra-fast cloud AI processing.
    """

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )

    response = model.generate_content(
        f"Process this citizen complaint:\n\n{user_text}",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )

    return safe_json_parse(response.text)


# ─────────────────────────────────────────────────────────────
# FALLBACK ENGINE: LOCAL OLLAMA
# ─────────────────────────────────────────────────────────────

def call_ollama_local(user_text: str) -> dict:
    """
    Local offline inference via Ollama + Qwen.
    """

    url = "http://localhost:11434/api/generate"

    full_prompt = f"{SYSTEM_PROMPT}\n\nProcess this citizen complaint:\n\n{user_text}"

    payload = {
        "model": "qwen",
        "prompt": full_prompt,
        "stream": False,
        "format": "json"
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    return safe_json_parse(result.get("response", "{}"))


# ─────────────────────────────────────────────────────────────
# RESULT VALIDATION
# ─────────────────────────────────────────────────────────────

def validate_ai_result(ai_result: dict, original_text: str) -> dict:
    """
    Ensures the frontend NEVER crashes due to missing fields.
    """

    required_fields = {
        "detected_language": "Unknown",
        "language_code": "und",
        "original_text": original_text,
        "translated_text": original_text,
        "category": "GENERAL",
        "department": "Municipal Commissioner's Office",
        "priority": "LOW",
        "priority_reason": "Default fallback classification",
        "summary": original_text[:120],
        "location_hint": None,
        "keywords": [],
        "acknowledgment_message": "Your complaint has been received and will be reviewed."
    }

    for field, default in required_fields.items():
        if field not in ai_result or ai_result[field] is None:
            ai_result[field] = default

    return ai_result


# ─────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────

def process_complaint(raw_text: str, gemini_api_key: str = None) -> dict:
    """
    Main router used by your backend API.

    Flow:
    Cloud AI → fallback to Local AI → safe output
    """

    if not raw_text or not raw_text.strip():
        raise ValueError("Complaint text cannot be empty")

    raw_text = raw_text.strip()
    ai_result = None

    # ─────────────── TRY CLOUD FIRST ───────────────

    if gemini_api_key:

        try:
            print("🌐 [AI ROUTER] Trying Gemini Cloud Engine...")
            ai_result = call_gemini_api(raw_text, gemini_api_key)
            print("✅ [AI ROUTER] Cloud processing successful.")

        except Exception as e:

            print("⚠️ [AI ROUTER] Cloud AI failed.")
            print(f"Reason: {e}")
            print("🔄 Switching to local edge AI...")

    else:

        print("⚠️ [AI ROUTER] No API key provided. Using local AI.")

    # ─────────────── LOCAL FALLBACK ───────────────

    if not ai_result:

        try:
            ai_result = call_ollama_local(raw_text)
            print("✅ [AI ROUTER] Local AI processing successful.")

        except Exception as e:

            print("❌ [AI ROUTER] CRITICAL FAILURE")
            print("Both cloud and local AI engines failed.")
            print(e)

            ai_result = {
                "summary": raw_text[:120],
                "category": "GENERAL",
                "priority": "LOW"
            }

    # ─────────────── VALIDATE RESULT ───────────────

    ai_result = validate_ai_result(ai_result, raw_text)

    return ai_result