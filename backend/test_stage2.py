"""
Stage 2 end-to-end verification script.

Tests every endpoint with real payloads and validates:
  - Happy paths create DB rows
  - Validation errors return structured 400s, not 500s

Run with:
  python test_stage2.py
"""

import json
import sys
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000/api"
PASS = "[PASS]"
FAIL = "[FAIL]"
errors = []


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def req(method, path, body=None, *, label):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def multipart_req(path, fields, file_content, filename, *, label):
    """Send a multipart/form-data POST."""
    boundary = "----PythonTestBoundary99"
    parts = []
    for key, val in fields.items():
        parts.append(
            f"------PythonTestBoundary99\r\n"
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
            f"{val}\r\n"
        )
    if filename:
        parts.append(
            f"------PythonTestBoundary99\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        )
        raw = "".join(parts).encode() + file_content + b"\r\n------PythonTestBoundary99--\r\n"
    else:
        raw = "".join(parts).encode() + b"------PythonTestBoundary99--\r\n"

    url = f"{BASE}{path}"
    request = urllib.request.Request(
        url, data=raw, method="POST",
        headers={"Content-Type": "multipart/form-data; boundary=----PythonTestBoundary99"},
    )
    try:
        with urllib.request.urlopen(request) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def check(label, code, body, expected_status, *assertions):
    icon = PASS if code == expected_status else FAIL
    print(f"  {icon} [{code}] {label}")
    if code != expected_status:
        errors.append(f"{label}: expected HTTP {expected_status}, got {code}. Body: {body}")
    for key, expected_val in assertions:
        actual = body.get(key)
        ok = actual == expected_val if expected_val is not None else actual is not None
        icon2 = PASS if ok else FAIL
        print(f"       {icon2} {key} = {repr(actual)}")
        if not ok:
            errors.append(f"{label}: {key} expected {expected_val!r}, got {actual!r}")


# ── Tests ─────────────────────────────────────────────────────────────────────

print("\n=== Stage 2 Verification ===\n")

# ─────────────────────────────────────────────────────────────────────────────
print("--- POST /api/chat/ : happy paths")

# 1. New conversation
code, body = req("POST", "/chat/", {"message": "My car makes a rattling noise."}, label="new convo")
check("New conversation created", code, body, 200, ("message_saved", True))
convo_id = body.get("conversation_id")
print(f"       -> conversation_id = {convo_id}")

# 2. Resume existing conversation
code, body = req("POST", "/chat/", {"message": "It gets worse at high speed.", "conversation_id": convo_id}, label="resume")
check("Resume existing conversation", code, body, 200, ("message_saved", True), ("conversation_id", convo_id))

# 3. Missing message -> 400
code, body = req("POST", "/chat/", {}, label="missing message")
check("Missing message -> 400", code, body, 400)

# 4. Non-existent conversation_id -> 400
code, body = req("POST", "/chat/", {"message": "hello", "conversation_id": 99999}, label="bad convo id")
check("Non-existent conversation_id -> 400", code, body, 400)

# ─────────────────────────────────────────────────────────────────────────────
print("\n--- GET /api/chat/<id>/history/")

code, body = req("GET", f"/chat/{convo_id}/history/", label="history")
check("Conversation history returned", code, body, 200, ("conversation_id", convo_id))
msgs = body.get("messages", [])
print(f"       -> {len(msgs)} message(s) in history")
if len(msgs) == 2:
    print(f"  {PASS} Correct message count: 2")
else:
    print(f"  {FAIL} Expected 2 messages, got {len(msgs)}")
    errors.append(f"History: expected 2 messages, got {len(msgs)}")

# Non-existent -> 404
code, body = req("GET", "/chat/99999/history/", label="bad history")
check("Non-existent conversation history -> 404", code, body, 404)

# ─────────────────────────────────────────────────────────────────────────────
print("\n--- POST /api/upload/ : validation + happy path")

# 5. Missing conversation_id (multipart)
code, body = multipart_req(
    "/upload/",
    {"media_type": "image"},
    b"fake",
    "photo.jpg",
    label="no conversation_id",
)
check("Missing conversation_id -> 400", code, body, 400)

# 6. Bad media_type (multipart)
code, body = multipart_req(
    "/upload/",
    {"conversation_id": str(convo_id), "media_type": "document"},
    b"fake",
    "file.pdf",
    label="bad media_type",
)
check("Invalid media_type -> 400", code, body, 400)

# 7. Happy path: valid image (minimal JPEG bytes)
tiny_jpeg = bytes([
    0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01,
    0x01,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0xFF,0xDB,0x00,0x43,
    0x00,0x08,0x06,0x06,0x07,0x06,0x05,0x08,0x07,0x07,0x07,0x09,
    0x09,0x08,0x0A,0x0C,0x14,0x0D,0x0C,0x0B,0x0B,0x0C,0x19,0x12,
    0x13,0x0F,0x14,0x1D,0x1A,0x1F,0x1E,0x1D,0x1A,0x1C,0x1C,0x20,
    0x24,0x2E,0x27,0x20,0x22,0x2C,0x23,0x1C,0x1C,0x28,0x37,0x29,
    0x2C,0x30,0x31,0x34,0x34,0x34,0x1F,0x27,0x39,0x3D,0x38,0x32,
    0x3C,0x2E,0x33,0x34,0x32,0xFF,0xC0,0x00,0x0B,0x08,0x00,0x01,
    0x00,0x01,0x01,0x01,0x11,0x00,0xFF,0xC4,0x00,0x1F,0x00,0x00,
    0x01,0x05,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
    0x09,0x0A,0x0B,0xFF,0xDA,0x00,0x08,0x01,0x01,0x00,0x00,0x3F,
    0x00,0xFB,0xFF,0xD9,
])
code, body = multipart_req(
    "/upload/",
    {"conversation_id": str(convo_id), "media_type": "image"},
    tiny_jpeg,
    "test_photo.jpg",
    label="valid image",
)
check("Valid image upload -> 201", code, body, 201, ("media_type", "image"), ("role", "user"))
print(f"       -> Message id = {body.get('id')}, media_url = {body.get('media_url')}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n--- POST /api/diagnosis/ : stub")

code, body = req("POST", "/diagnosis/", {"conversation_id": convo_id}, label="diagnosis stub")
check("Diagnosis stub -> 200", code, body, 200, ("status", "stub"))

code, body = req("POST", "/diagnosis/", {}, label="diagnosis missing convo")
check("Diagnosis missing conversation_id -> 400", code, body, 400)

# ─────────────────────────────────────────────────────────────────────────────
print("\n--- POST /api/booking/ : happy path + validation")

booking_payload = {
    "conversation_id": convo_id,
    "customer_name": "Arya Chakraborty",
    "customer_contact": "+91-9876543210",
    "car_model": "Toyota Innova 2022",
    "issue_summary": "Rattling noise at high speed, suspected loose exhaust mount.",
    "service": "Full inspection + exhaust repair",
}

code, body = req("POST", "/booking/", booking_payload, label="create booking")
check("Booking created -> 201", code, body, 201,
      ("customer_name", "Arya Chakraborty"), ("status", "pending"))
booking_id = body.get("id")
print(f"       -> Booking id = {booking_id}, diagnosis = {body.get('diagnosis')}")

# Missing required fields
code, body = req("POST", "/booking/", {"conversation_id": convo_id, "customer_name": "A"}, label="missing fields")
check("Missing required booking fields -> 400", code, body, 400)

# Bad conversation_id
code, body = req("POST", "/booking/", {**booking_payload, "conversation_id": 99999}, label="bad convo")
check("Non-existent conversation_id in booking -> 400", code, body, 400)

# ─────────────────────────────────────────────────────────────────────────────
print("\n--- GET /api/booking/<id>/")

code, body = req("GET", f"/booking/{booking_id}/", label="booking detail")
check("Booking detail -> 200", code, body, 200, ("status", "pending"))
convo_nested = body.get("conversation", {})
print(f"       -> conversation.id = {convo_nested.get('id')}, message_count = {convo_nested.get('message_count')}")

code, body = req("GET", "/booking/99999/", label="bad booking")
check("Non-existent booking -> 404", code, body, 404)

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 40)
if errors:
    print(f"\n{FAIL} {len(errors)} test(s) FAILED:\n")
    for e in errors:
        print(f"  * {e}")
    sys.exit(1)
else:
    print(f"\n{PASS} All tests passed!\n")
