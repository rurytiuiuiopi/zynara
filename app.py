import os
import json
import hashlib
import hmac
import time
import mimetypes
import uuid
from flask import Flask, jsonify, request, send_from_directory, Response, abort, render_template
from config import SECRET_KEY, MOMO_CURRENCY, DEBUG, MOMO_SUBSCRIPTION_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

SONGS_FILE = os.path.join(os.path.dirname(__file__), "songs.json")
SONGS_DIR  = os.path.join(os.path.dirname(__file__), "static", "songs")

# True when MoMo credentials have not been configured yet
DEMO_MODE = not MOMO_SUBSCRIPTION_KEY

# In-memory payment store  (swap for a database in production)
payments = {}   # reference_id -> { status, item_id, item_type, phone, ... }


def load_album():
    with open(SONGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Pages ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Album data ─────────────────────────────────────────────────────

@app.route("/api/album")
def api_album():
    data = load_album()
    data["demo_mode"] = DEMO_MODE
    return jsonify(data)


# ── Purchase ───────────────────────────────────────────────────────

@app.route("/api/purchase", methods=["POST"])
def api_purchase():
    body      = request.get_json(silent=True) or {}
    phone     = str(body.get("phone", "")).strip()
    item_id   = str(body.get("item_id", "")).strip()
    item_type = str(body.get("item_type", "song")).strip()
    item_name = str(body.get("item_name", "Music")).strip()

    if not phone or not item_id:
        return jsonify({"error": "Phone and item_id are required"}), 400

    album = load_album()

    if item_type == "album":
        amount = album["album_price"]
    else:
        song = next((s for s in album["songs"] if str(s["id"]) == item_id), None)
        if not song:
            return jsonify({"error": "Song not found"}), 404
        amount = song["price"]

    ref_id = str(uuid.uuid4())

    if DEMO_MODE:
        # No MoMo keys yet — simulate a pending payment that resolves quickly
        payments[ref_id] = {
            "status": "PENDING",
            "item_id": item_id,
            "item_type": item_type,
            "phone": phone,
            "amount": amount,
            "created_at": time.time(),
            "demo": True,
        }
        return jsonify({"reference_id": ref_id, "demo": True})

    try:
        from momo import request_to_pay
        ref_id = request_to_pay(
            phone=phone,
            amount=str(amount),
            currency=MOMO_CURRENCY,
            item_name=item_name,
            reference_id=ref_id,
        )
        payments[ref_id] = {
            "status": "PENDING",
            "item_id": item_id,
            "item_type": item_type,
            "phone": phone,
            "amount": amount,
            "created_at": time.time(),
            "demo": False,
        }
        return jsonify({"reference_id": ref_id})
    except Exception as e:
        app.logger.error(f"MoMo purchase error: {e}")
        return jsonify({"error": str(e)}), 502


# ── Verify payment status ──────────────────────────────────────────

@app.route("/api/verify/<reference_id>")
def api_verify(reference_id):
    if reference_id not in payments:
        return jsonify({"status": "NOT_FOUND", "message": "Unknown payment"}), 404

    cached = payments[reference_id]

    # Return cached result if already settled
    if cached["status"] in ("SUCCESSFUL", "FAILED"):
        token = _make_token(cached["item_id"], cached["item_type"]) if cached["status"] == "SUCCESSFUL" else None
        return jsonify({"status": cached["status"], "token": token, "message": cached.get("message", "")})

    # DEMO MODE: auto-approve after 3 seconds
    if cached.get("demo"):
        elapsed = time.time() - cached["created_at"]
        if elapsed >= 3:
            payments[reference_id]["status"] = "SUCCESSFUL"
            token = _make_token(cached["item_id"], cached["item_type"])
            return jsonify({"status": "SUCCESSFUL", "token": token, "message": "Payment approved! (demo mode)"})
        return jsonify({"status": "PENDING", "message": "Demo mode — approving in a moment..."})

    # Live MoMo polling
    try:
        from momo import get_payment_status
        result = get_payment_status(reference_id)
        status = result.get("status", "PENDING")
        payments[reference_id]["status"] = status
        payments[reference_id]["message"] = result.get("reason", "")

        if status == "SUCCESSFUL":
            token = _make_token(cached["item_id"], cached["item_type"])
            return jsonify({"status": "SUCCESSFUL", "token": token, "message": "Payment approved!"})
        elif status == "FAILED":
            return jsonify({"status": "FAILED", "message": result.get("reason", "Payment declined.")})
        else:
            return jsonify({"status": "PENDING", "message": "Waiting for approval on your phone..."})
    except Exception as e:
        app.logger.error(f"MoMo verify error: {e}")
        return jsonify({"status": "PENDING", "message": "Checking..."}), 200


# ── Protected audio streaming ──────────────────────────────────────

@app.route("/api/stream/<song_id>")
def api_stream(song_id):
    token = request.args.get("t", "")
    if not _verify_token(song_id, token):
        abort(403)

    album = load_album()
    song  = next((s for s in album["songs"] if str(s["id"]) == song_id), None)
    if not song:
        abort(404)

    filename = song.get("file", "")
    filepath  = os.path.join(SONGS_DIR, filename)
    if not os.path.isfile(filepath):
        # Return a short silent audio so the player doesn't crash in demo mode
        return _silent_audio_response()

    return _stream_audio(filepath)


def _silent_audio_response():
    """Tiny valid MP3 (0.1 s silence) returned when the real file isn't uploaded yet."""
    # Minimal valid MP3 frame (ID3v2 header + one silent MPEG frame)
    silent_mp3 = bytes([
        0xFF,0xFB,0x90,0x00,  # MPEG1 Layer3, 128kbps, 44100Hz, stereo
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    ])
    return Response(
        silent_mp3,
        status=200,
        headers={"Content-Type": "audio/mpeg", "Content-Length": str(len(silent_mp3))},
    )


def _stream_audio(filepath):
    """Stream audio with HTTP Range support so browsers can seek."""
    file_size = os.path.getsize(filepath)
    mime      = mimetypes.guess_type(filepath)[0] or "audio/mpeg"
    range_hdr = request.headers.get("Range")

    if range_hdr:
        byte_start, byte_end = 0, file_size - 1
        parts = range_hdr.replace("bytes=", "").split("-")
        if parts[0]:
            byte_start = int(parts[0])
        if len(parts) > 1 and parts[1]:
            byte_end = int(parts[1])
        length = byte_end - byte_start + 1

        def gen_range():
            with open(filepath, "rb") as f:
                f.seek(byte_start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return Response(gen_range(), status=206, headers={
            "Content-Range":  f"bytes {byte_start}-{byte_end}/{file_size}",
            "Accept-Ranges":  "bytes",
            "Content-Length": str(length),
            "Content-Type":   mime,
        })

    def gen_full():
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk

    return Response(gen_full(), status=200, headers={
        "Content-Length": str(file_size),
        "Accept-Ranges":  "bytes",
        "Content-Type":   mime,
    })


# ── Token helpers ──────────────────────────────────────────────────

def _make_token(item_id: str, item_type: str) -> str:
    expiry  = int(time.time()) + 86400          # valid 24 hours
    payload = f"{item_id}:{item_type}:{expiry}"
    sig     = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    import base64
    return base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()


def _verify_token(song_id: str, token: str) -> bool:
    if not token:
        return False
    try:
        import base64
        raw   = base64.urlsafe_b64decode(token.encode()).decode()
        parts = raw.rsplit(":", 1)
        if len(parts) != 2:
            return False
        payload, sig = parts
        expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        p = payload.split(":")
        if len(p) < 3:
            return False
        token_item_id, item_type, expiry_str = p[0], p[1], p[2]
        if int(expiry_str) < time.time():
            return False
        return item_type == "album" or token_item_id == song_id
    except Exception:
        return False


# ── Static files ───────────────────────────────────────────────────

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


if __name__ == "__main__":
    if DEMO_MODE:
        print("\n" + "="*58)
        print("  ZYNARA running in DEMO MODE")
        print("  MoMo keys not set — payments auto-approve instantly")
        print("  Open: http://localhost:5000")
        print("="*58 + "\n")
    else:
        print("\n  ZYNARA running — http://localhost:5000\n")
    app.run(debug=DEBUG, host="0.0.0.0", port=5000)
