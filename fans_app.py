import os
import time
import hmac
import hashlib
import secrets
import smtplib
import requests as _requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, Response, abort
)
from werkzeug.security import check_password_hash

from fans_db import get_db, init_db, generate_fan_number

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "shatta-fans-secret-2024")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
)

# ── CSRF ──────────────────────────────────────────────────────────
def _csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

def _check_csrf():
    token = request.form.get('_csrf', '')
    expected = session.get('_csrf_token', '')
    return bool(expected) and hmac.compare_digest(token, expected)

app.jinja_env.globals['csrf_token'] = _csrf_token

# ── RATE LIMITING ─────────────────────────────────────────────────
_login_attempts = defaultdict(list)

def _check_rate_limit(ip, max_attempts=10, window=600):
    now = time.time()
    attempts = [t for t in _login_attempts[ip] if now - t < window]
    _login_attempts[ip] = attempts
    if len(attempts) >= max_attempts:
        return False
    _login_attempts[ip].append(now)
    return True

# ── SECURITY HEADERS ──────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

CARD_PRICE = 100
UPLOAD_DIR = os.path.join("static", "fans", "proofs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _momo_number():
    return os.environ.get("MOMO_NUMBER", "")

def _send_email(to_email, subject, html_body):
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not gmail_user or not gmail_pass:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Shatta Movement <{gmail_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(gmail_user, gmail_pass)
            s.sendmail(gmail_user, to_email, msg.as_string())
    except Exception:
        pass

def _paystack_init(email, amount_ghs, reference, fan_id):
    secret = os.environ.get("PAYSTACK_SECRET_KEY", "")
    if not secret:
        return None
    try:
        resp = _requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers={"Authorization": f"Bearer {secret}"},
            json={
                "email": email,
                "amount": int(amount_ghs * 100),
                "currency": "GHS",
                "reference": reference,
                "callback_url": "https://shattamovementfanbase.com/gold-card/callback",
                "metadata": {"fan_id": fan_id}
            },
            timeout=10
        )
        data = resp.json()
        if data.get("status"):
            return data["data"]["authorization_url"]
    except Exception:
        pass
    return None

def _paystack_verify(reference):
    secret = os.environ.get("PAYSTACK_SECRET_KEY", "")
    if not secret:
        return False
    try:
        resp = _requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=10
        )
        data = resp.json()
        return data.get("status") and data["data"]["status"] == "success"
    except Exception:
        return False


COUNTRIES = [
    "Afghanistan","Albania","Algeria","Angola","Argentina","Armenia","Australia",
    "Austria","Azerbaijan","Bahrain","Bangladesh","Belarus","Belgium","Benin",
    "Bolivia","Bosnia","Botswana","Brazil","Bulgaria","Burkina Faso","Burundi",
    "Cambodia","Cameroon","Canada","Chad","Chile","China","Colombia","Congo",
    "Croatia","Cuba","Cyprus","Czech Republic","Denmark","Djibouti","Ecuador",
    "Egypt","El Salvador","Ethiopia","Finland","France","Gabon","Gambia",
    "Georgia","Germany","Ghana","Greece","Guatemala","Guinea","Haiti","Honduras",
    "Hungary","India","Indonesia","Iran","Iraq","Ireland","Israel","Italy",
    "Ivory Coast","Jamaica","Japan","Jordan","Kazakhstan","Kenya","Kuwait",
    "Lebanon","Liberia","Libya","Madagascar","Malawi","Malaysia","Mali","Malta",
    "Mauritania","Mexico","Moldova","Morocco","Mozambique","Myanmar","Namibia",
    "Nepal","Netherlands","New Zealand","Nicaragua","Niger","Nigeria","Norway",
    "Oman","Pakistan","Panama","Paraguay","Peru","Philippines","Poland",
    "Portugal","Qatar","Romania","Russia","Rwanda","Saudi Arabia","Senegal",
    "Serbia","Sierra Leone","Singapore","Somalia","South Africa","South Sudan",
    "Spain","Sri Lanka","Sudan","Sweden","Switzerland","Syria","Taiwan",
    "Tanzania","Thailand","Togo","Tunisia","Turkey","Uganda","Ukraine",
    "United Arab Emirates","United Kingdom","United States","Uruguay",
    "Uzbekistan","Venezuela","Vietnam","Yemen","Zambia","Zimbabwe"
]

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ── DECOY ROUTES — /admin returns 404 ────────────────────────────
@app.route("/admin", methods=["GET", "POST"])
@app.route("/admin/", methods=["GET", "POST"])
@app.route("/admin/login", methods=["GET", "POST"])
@app.route("/admin/dashboard", methods=["GET", "POST"])
@app.route("/admin/fans", methods=["GET", "POST"])
@app.route("/admin/gold-cards", methods=["GET", "POST"])
def admin_decoy():
    abort(404)


# ── PUBLIC ROUTES ──────────────────────────────────────────────────

@app.route("/")
def index():
    db = get_db()
    total_fans = db.execute("SELECT COUNT(*) FROM fans").fetchone()[0]
    total_countries = db.execute("SELECT COUNT(DISTINCT country) FROM fans").fetchone()[0]
    total_fanbases = db.execute("SELECT COUNT(*) FROM fanbases").fetchone()[0]
    announcements = db.execute(
        "SELECT * FROM announcements ORDER BY is_pinned DESC, created_at DESC LIMIT 3"
    ).fetchall()
    top_countries = db.execute(
        "SELECT country, COUNT(*) as cnt FROM fans GROUP BY country ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    recent_fans = db.execute(
        "SELECT full_name, country, city, registered_at FROM fans ORDER BY registered_at DESC LIMIT 8"
    ).fetchall()
    fanbases_by_continent = {}
    for row in db.execute("SELECT * FROM fanbases ORDER BY continent, country").fetchall():
        c = row["continent"]
        fanbases_by_continent.setdefault(c, []).append(row)
    db.close()
    return render_template("fans/index.html",
        total_fans=total_fans,
        total_countries=total_countries,
        total_fanbases=total_fanbases,
        announcements=announcements,
        top_countries=top_countries,
        recent_fans=recent_fans,
        fanbases_by_continent=fanbases_by_continent,
        countries=COUNTRIES,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    db = get_db()
    fanbases = db.execute("SELECT * FROM fanbases ORDER BY continent, country").fetchall()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip()
        country = request.form.get("country", "").strip()
        city = request.form.get("city", "").strip()
        instagram = request.form.get("instagram", "").strip()
        tiktok = request.form.get("tiktok", "").strip()
        twitter = request.form.get("twitter", "").strip()
        facebook = request.form.get("facebook", "").strip()
        favorite_songs = request.form.get("favorite_songs", "").strip()
        fan_since = request.form.get("fan_since", "").strip()
        fanbase_id = request.form.get("fanbase_id") or None

        errors = []
        if not full_name: errors.append("Full name is required.")
        if not email: errors.append("Email is required.")
        if not phone: errors.append("Phone is required.")
        if not country: errors.append("Country is required.")
        if not city: errors.append("City is required.")

        existing = db.execute("SELECT id FROM fans WHERE email = ?", (email,)).fetchone()
        if existing:
            errors.append("This email is already registered.")

        if errors:
            for e in errors:
                flash(e, "error")
            db.close()
            return render_template("fans/register.html", fanbases=fanbases, countries=COUNTRIES)

        fan_number = generate_fan_number()
        while db.execute("SELECT id FROM fans WHERE fan_number = ?", (fan_number,)).fetchone():
            fan_number = generate_fan_number()

        try:
            fan_since_int = int(fan_since) if fan_since else None
        except ValueError:
            fan_since_int = None

        db.execute("""
            INSERT INTO fans (fan_number, full_name, email, phone, whatsapp,
                country, city, instagram, tiktok, twitter, facebook,
                favorite_songs, fan_since, fanbase_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fan_number, full_name, email, phone, whatsapp,
              country, city, instagram, tiktok, twitter, facebook,
              favorite_songs, fan_since_int, fanbase_id))
        db.commit()

        fan_id = db.execute("SELECT id FROM fans WHERE fan_number = ?", (fan_number,)).fetchone()["id"]
        db.close()
        return redirect(url_for("fan_card", fan_id=fan_id))

    db.close()
    return render_template("fans/register.html", fanbases=fanbases, countries=COUNTRIES)


@app.route("/fan/<int:fan_id>")
def fan_card(fan_id):
    db = get_db()
    fan = db.execute("SELECT * FROM fans WHERE id = ?", (fan_id,)).fetchone()
    if not fan:
        db.close()
        return redirect(url_for("index"))
    fanbase = None
    if fan["fanbase_id"]:
        fanbase = db.execute("SELECT * FROM fanbases WHERE id = ?", (fan["fanbase_id"],)).fetchone()
    db.close()
    return render_template("fans/fan_card.html", fan=fan, fanbase=fanbase)


@app.route("/fans")
def fans_directory():
    db = get_db()
    country = request.args.get("country", "")
    search = request.args.get("q", "")
    query = "SELECT * FROM fans WHERE 1=1"
    params = []
    if country:
        query += " AND country = ?"
        params.append(country)
    if search:
        query += " AND (full_name ILIKE ? OR city ILIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    query += " ORDER BY registered_at DESC LIMIT 100"
    fans = db.execute(query, params).fetchall()
    countries_with_fans = db.execute(
        "SELECT country, COUNT(*) as cnt FROM fans GROUP BY country ORDER BY cnt DESC"
    ).fetchall()
    db.close()
    return render_template("fans/directory.html",
        fans=fans, countries_with_fans=countries_with_fans,
        selected_country=country, search=search
    )


@app.route("/fanbases")
def fanbases():
    db = get_db()
    fanbases_by_continent = {}
    for row in db.execute("SELECT * FROM fanbases ORDER BY continent, country").fetchall():
        c = row["continent"]
        fanbases_by_continent.setdefault(c, []).append(row)
    db.close()
    return render_template("fans/fanbases.html", fanbases_by_continent=fanbases_by_continent)


@app.route("/announcements")
def announcements():
    db = get_db()
    items = db.execute(
        "SELECT * FROM announcements ORDER BY is_pinned DESC, created_at DESC"
    ).fetchall()
    db.close()
    return render_template("fans/announcements.html", announcements=items)


# ── REAL ADMIN ROUTES at /smcp-9f4x/ ──────────────────────────────

@app.route("/smcp-9f4x/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
        if not _check_rate_limit(ip):
            flash("Too many login attempts. Try again in 10 minutes.", "error")
            return render_template("fans/admin/login.html")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        admin = db.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        db.close()
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials.", "error")
    return render_template("fans/admin/login.html")


@app.route("/smcp-9f4x/logout")
def admin_logout():
    session.pop("admin_id", None)
    return redirect(url_for("index"))


@app.route("/smcp-9f4x/")
@admin_required
def admin_dashboard():
    db = get_db()
    total_fans = db.execute("SELECT COUNT(*) FROM fans").fetchone()[0]
    fans_today = db.execute(
        "SELECT COUNT(*) FROM fans WHERE DATE(registered_at) = CURRENT_DATE"
    ).fetchone()[0]
    fans_this_week = db.execute(
        "SELECT COUNT(*) FROM fans WHERE registered_at >= NOW() - INTERVAL '7 days'"
    ).fetchone()[0]
    by_continent = db.execute("""
        SELECT f.continent, COUNT(fa.id) as cnt
        FROM fanbases f LEFT JOIN fans fa ON fa.fanbase_id = f.id
        GROUP BY f.continent
    """).fetchall()
    top_countries = db.execute(
        "SELECT country, COUNT(*) as cnt FROM fans GROUP BY country ORDER BY cnt DESC LIMIT 15"
    ).fetchall()
    recent = db.execute(
        "SELECT * FROM fans ORDER BY registered_at DESC LIMIT 20"
    ).fetchall()
    db.close()
    return render_template("fans/admin/dashboard.html",
        total_fans=total_fans,
        fans_today=fans_today,
        fans_this_week=fans_this_week,
        by_continent=by_continent,
        top_countries=top_countries,
        recent=recent,
    )


@app.route("/smcp-9f4x/fans")
@admin_required
def admin_fans():
    db = get_db()
    country = request.args.get("country", "")
    search = request.args.get("q", "")
    query = "SELECT * FROM fans WHERE 1=1"
    params = []
    if country:
        query += " AND country = ?"
        params.append(country)
    if search:
        query += " AND (full_name ILIKE ? OR email ILIKE ? OR city ILIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    query += " ORDER BY registered_at DESC"
    fans = db.execute(query, params).fetchall()
    countries = db.execute(
        "SELECT DISTINCT country FROM fans ORDER BY country"
    ).fetchall()
    db.close()
    return render_template("fans/admin/fans.html",
        fans=fans, countries=countries,
        selected_country=country, search=search
    )


@app.route("/smcp-9f4x/announce", methods=["GET", "POST"])
@admin_required
def admin_announce():
    db = get_db()
    if request.method == "POST":
        if not _check_csrf():
            abort(403)
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        category = request.form.get("category", "general")
        image_url = request.form.get("image_url", "").strip()
        link_url = request.form.get("link_url", "").strip()
        is_pinned = 1 if request.form.get("is_pinned") else 0
        if title and body:
            db.execute(
                "INSERT INTO announcements (title, body, category, image_url, link_url, is_pinned) VALUES (?, ?, ?, ?, ?, ?)",
                (title, body, category, image_url, link_url, is_pinned)
            )
            db.commit()
            flash("Announcement posted!", "success")
        db.close()
        return redirect(url_for("admin_announce"))
    items = db.execute("SELECT * FROM announcements ORDER BY created_at DESC").fetchall()
    db.close()
    return render_template("fans/admin/announce.html", announcements=items)


@app.route("/smcp-9f4x/announce/delete/<int:ann_id>", methods=["POST"])
@admin_required
def admin_announce_delete(ann_id):
    if not _check_csrf():
        abort(403)
    db = get_db()
    db.execute("DELETE FROM announcements WHERE id = ?", (ann_id,))
    db.commit()
    db.close()
    return redirect(url_for("admin_announce"))


@app.route("/smcp-9f4x/export")
@admin_required
def admin_export():
    db = get_db()
    fans = db.execute("SELECT * FROM fans ORDER BY country, full_name").fetchall()
    db.close()
    lines = ["Fan Number,Full Name,Email,Phone,WhatsApp,Country,City,Instagram,TikTok,Twitter,Facebook,Favorite Songs,Fan Since,Registered At"]
    for f in fans:
        lines.append(",".join([
            f["fan_number"], f["full_name"], f["email"], f["phone"] or "",
            f["whatsapp"] or "", f["country"], f["city"],
            f["instagram"] or "", f["tiktok"] or "", f["twitter"] or "",
            f["facebook"] or "", (f["favorite_songs"] or "").replace(",", ";"),
            str(f["fan_since"] or ""), f["registered_at"]
        ]))
    return Response(
        "\n".join(lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=shatta_fans.csv"}
    )


@app.route("/smcp-9f4x/fanbases", methods=["GET", "POST"])
@admin_required
def admin_fanbases():
    db = get_db()
    if request.method == "POST":
        if not _check_csrf():
            abort(403)
        name = request.form.get("name", "").strip()
        country = request.form.get("country", "").strip()
        city = request.form.get("city", "").strip()
        continent = request.form.get("continent", "").strip()
        leader_name = request.form.get("leader_name", "").strip()
        leader_contact = request.form.get("leader_contact", "").strip()
        if name and country and continent:
            db.execute(
                "INSERT INTO fanbases (name, country, city, continent, leader_name, leader_contact) VALUES (?, ?, ?, ?, ?, ?)",
                (name, country, city, continent, leader_name, leader_contact)
            )
            db.commit()
            flash("Fanbase added!", "success")
        db.close()
        return redirect(url_for("admin_fanbases"))
    fanbases = db.execute("SELECT * FROM fanbases ORDER BY continent, country").fetchall()
    db.close()
    return render_template("fans/admin/fanbases.html", fanbases=fanbases)


# ── GOLD CARD ROUTES ───────────────────────────────────────────────

@app.route("/gold-card")
def gold_card_info():
    return render_template("fans/gold_card_info.html", price=CARD_PRICE)


@app.route("/gold-card/apply/<int:fan_id>", methods=["GET", "POST"])
def gold_card_apply(fan_id):
    import random
    db = get_db()
    fan = db.execute("SELECT * FROM fans WHERE id = ?", (fan_id,)).fetchone()
    if not fan:
        db.close()
        return redirect(url_for("index"))

    existing = db.execute("SELECT * FROM gold_cards WHERE fan_id = ?", (fan_id,)).fetchone()
    if existing and existing["status"] == "active":
        db.close()
        return redirect(url_for("gold_card_status", fan_id=fan_id))

    if request.method == "POST":
        if existing and existing["status"] == "pending":
            db.close()
            return redirect(url_for("gold_card_status", fan_id=fan_id))

        reference = f"SMGC-{fan_id}-{int(time.time())}"

        if existing and existing["status"] == "rejected":
            db.execute("UPDATE gold_cards SET status='pending', proof_path=? WHERE fan_id=?",
                       (reference, fan_id))
        else:
            parts = [str(random.randint(1000, 9999)) for _ in range(4)]
            card_number = "SM " + " ".join(parts)
            while db.execute("SELECT id FROM gold_cards WHERE card_number = ?", (card_number,)).fetchone():
                parts = [str(random.randint(1000, 9999)) for _ in range(4)]
                card_number = "SM " + " ".join(parts)
            db.execute(
                "INSERT INTO gold_cards (fan_id, card_number, proof_path, amount_paid) VALUES (?, ?, ?, ?)",
                (fan_id, card_number, reference, CARD_PRICE)
            )
        db.commit()
        db.close()

        auth_url = _paystack_init(fan["email"], CARD_PRICE, reference, fan_id)
        if not auth_url:
            flash("Payment service unavailable. Please try again shortly.", "error")
            return redirect(url_for("gold_card_apply", fan_id=fan_id))
        return redirect(auth_url)

    db.close()
    return render_template("fans/gold_card_apply.html",
        fan=fan, existing=existing, price=CARD_PRICE
    )


@app.route("/gold-card/callback")
def gold_card_callback():
    reference = request.args.get("reference", "")
    if not reference.startswith("SMGC-"):
        return redirect(url_for("index"))
    try:
        fan_id = int(reference.split("-")[1])
    except (IndexError, ValueError):
        return redirect(url_for("index"))

    if _paystack_verify(reference):
        db = get_db()
        valid_until = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        db.execute("""
            UPDATE gold_cards SET status='active', valid_until=?, approved_at=NOW()
            WHERE fan_id=? AND proof_path=?
        """, (valid_until, fan_id, reference))
        db.commit()
        fan = db.execute("SELECT * FROM fans WHERE id = ?", (fan_id,)).fetchone()
        db.close()
        if fan and fan["email"]:
            _send_email(
                fan["email"],
                "🏆 Your SM Gold Card is Now Active!",
                f"""
                <div style="font-family:sans-serif;max-width:560px;margin:auto;background:#0a0a0a;color:#fff;padding:32px;border-radius:16px">
                  <div style="text-align:center;margin-bottom:24px">
                    <div style="background:linear-gradient(135deg,#b8860b,#f0c040);color:#000;font-weight:900;font-size:24px;letter-spacing:3px;padding:12px 24px;border-radius:12px;display:inline-block">SM</div>
                    <h2 style="color:#f0c040;margin-top:12px">Your Gold Card is Active!</h2>
                  </div>
                  <p>Hi <strong>{fan["full_name"]}</strong>,</p>
                  <p style="color:#aaa">Your MoMo payment has been confirmed. Your <strong style="color:#f0c040">SM Gold Membership Card</strong> is now active!</p>
                  <div style="text-align:center;margin-top:24px">
                    <a href="https://shattamovementfanbase.com/gold-card/status/{fan_id}" style="background:linear-gradient(135deg,#b8860b,#f0c040);color:#000;font-weight:800;padding:14px 28px;border-radius:10px;text-decoration:none;display:inline-block">View My Gold Card</a>
                  </div>
                  <p style="color:#555;font-size:12px;text-align:center;margin-top:24px">Shatta Movement Official Fan Platform</p>
                </div>
                """
            )
        flash("Payment confirmed! Your Gold Card is now active.", "success")
    else:
        flash("Payment not confirmed yet. If you paid, please check back in a few minutes.", "error")

    return redirect(url_for("gold_card_status", fan_id=fan_id))


@app.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    signature = request.headers.get("X-Paystack-Signature", "")
    payload = request.get_data()
    secret = os.environ.get("PAYSTACK_SECRET_KEY", "")
    computed = hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(computed, signature):
        abort(400)
    event = request.get_json(silent=True) or {}
    if event.get("event") == "charge.success":
        reference = event.get("data", {}).get("reference", "")
        if reference.startswith("SMGC-"):
            try:
                fan_id = int(reference.split("-")[1])
                db = get_db()
                valid_until = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
                db.execute("""
                    UPDATE gold_cards SET status='active', valid_until=?, approved_at=NOW()
                    WHERE fan_id=? AND proof_path=? AND status != 'active'
                """, (valid_until, fan_id, reference))
                db.commit()
                db.close()
            except Exception:
                pass
    return "", 200


@app.route("/gold-card/status/<int:fan_id>")
def gold_card_status(fan_id):
    db = get_db()
    fan = db.execute("SELECT * FROM fans WHERE id = ?", (fan_id,)).fetchone()
    if not fan:
        db.close()
        return redirect(url_for("index"))
    raw_card = db.execute("SELECT * FROM gold_cards WHERE fan_id = ?", (fan_id,)).fetchone()
    db.close()
    active_card = raw_card if (raw_card and raw_card["status"] == "active") else None
    pending = bool(raw_card and raw_card["status"] == "pending")
    rejected = bool(raw_card and raw_card["status"] == "rejected")
    return render_template("fans/gold_card_status.html",
        fan=fan, card=active_card, pending=pending, rejected=rejected)


@app.route("/smcp-9f4x/gold-cards")
@admin_required
def admin_gold_cards():
    db = get_db()
    cards = db.execute("""
        SELECT gc.id as gc_id, gc.fan_id, gc.card_number, gc.status,
               gc.valid_until, gc.created_at as gc_created_at,
               f.full_name, f.country, f.city, f.phone, f.email, f.fan_number
        FROM gold_cards gc
        JOIN fans f ON f.id = gc.fan_id
        ORDER BY gc.created_at DESC
    """).fetchall()
    db.close()
    return render_template("fans/admin/gold_cards.html", cards=cards)


@app.route("/smcp-9f4x/gold-cards/approve/<int:card_id>", methods=["POST"])
@admin_required
def admin_gold_card_approve(card_id):
    if not _check_csrf():
        abort(403)
    db = get_db()
    valid_until = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    db.execute("""
        UPDATE gold_cards SET status='active', valid_until=?, approved_at=NOW()
        WHERE id=?
    """, (valid_until, card_id))
    db.commit()
    db.close()
    flash("Gold Card approved!", "success")
    return redirect(url_for("admin_gold_cards"))


@app.route("/smcp-9f4x/gold-cards/reject/<int:card_id>", methods=["POST"])
@admin_required
def admin_gold_card_reject(card_id):
    if not _check_csrf():
        abort(403)
    db = get_db()
    card = db.execute("""
        SELECT gc.id, gc.fan_id, f.full_name, f.email, f.fan_number
        FROM gold_cards gc JOIN fans f ON f.id = gc.fan_id
        WHERE gc.id = ?
    """, (card_id,)).fetchone()
    db.execute("UPDATE gold_cards SET status='rejected' WHERE id=?", (card_id,))
    db.commit()
    db.close()
    if card and card["email"]:
        fan_link = f"https://shattamovementfanbase.com/gold-card/apply/{card['fan_id']}"
        _send_email(
            card["email"],
            "SM Gold Card Application — Action Required",
            f"""
            <div style="font-family:sans-serif;max-width:560px;margin:auto;background:#0a0a0a;color:#fff;padding:32px;border-radius:16px">
              <div style="text-align:center;margin-bottom:24px">
                <div style="background:linear-gradient(135deg,#b8860b,#f0c040);color:#000;font-weight:900;font-size:24px;letter-spacing:3px;padding:12px 24px;border-radius:12px;display:inline-block">SM</div>
                <h2 style="color:#fff;margin-top:12px">Gold Card Application Update</h2>
              </div>
              <p>Hi <strong>{card["full_name"]}</strong>,</p>
              <p style="color:#aaa">Your SM Gold Card application (<strong style="color:#f0c040">{card["fan_number"]}</strong>) could not be processed. Your payment was not confirmed.</p>
              <div style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:20px;margin:20px 0">
                <p style="margin:0;color:#eab308"><strong>To get your Gold Card:</strong></p>
                <ol style="color:#aaa;margin-top:8px">
                  <li>Click the button below to retry payment</li>
                  <li>Complete the GHS 100 MoMo payment on the secure Paystack page</li>
                  <li>Your card activates automatically once payment is confirmed</li>
                </ol>
              </div>
              <div style="text-align:center;margin-top:24px">
                <a href="{fan_link}" style="background:linear-gradient(135deg,#b8860b,#f0c040);color:#000;font-weight:800;padding:14px 28px;border-radius:10px;text-decoration:none;display:inline-block">Try Again — Pay GHS 100</a>
              </div>
              <p style="color:#555;font-size:12px;text-align:center;margin-top:24px">Shatta Movement Official Fan Platform</p>
            </div>
            """
        )
    flash("Gold Card rejected — fan notified by email.", "error")
    return redirect(url_for("admin_gold_cards"))


@app.route("/smcp-9f4x/gold-cards/reject-all", methods=["POST"])
@admin_required
def admin_gold_card_reject_all():
    if not _check_csrf():
        abort(403)
    db = get_db()
    pending = db.execute("""
        SELECT gc.id, gc.fan_id, f.full_name, f.email, f.fan_number
        FROM gold_cards gc JOIN fans f ON f.id = gc.fan_id
        WHERE gc.status = 'pending'
    """).fetchall()
    db.execute("UPDATE gold_cards SET status='rejected' WHERE status='pending'")
    db.commit()
    db.close()
    count = 0
    for p in pending:
        if p["email"]:
            fan_link = f"https://shattamovementfanbase.com/gold-card/apply/{p['fan_id']}"
            _send_email(
                p["email"],
                "SM Gold Card — Payment Not Confirmed",
                f"""
                <div style="font-family:sans-serif;max-width:560px;margin:auto;background:#0a0a0a;color:#fff;padding:32px;border-radius:16px">
                  <div style="text-align:center;margin-bottom:24px">
                    <div style="background:linear-gradient(135deg,#b8860b,#f0c040);color:#000;font-weight:900;font-size:24px;letter-spacing:3px;padding:12px 24px;border-radius:12px;display:inline-block">SM</div>
                    <h2 style="color:#fff;margin-top:12px">Gold Card Application Update</h2>
                  </div>
                  <p>Hi <strong>{p["full_name"]}</strong>,</p>
                  <p style="color:#aaa">Your SM Gold Card application (<strong style="color:#f0c040">{p["fan_number"]}</strong>) could not be confirmed. Your MoMo payment of <strong>GHS 100</strong> was not verified.</p>
                  <div style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:20px;margin:20px 0">
                    <p style="color:#eab308;margin:0"><strong>To get your Gold Card:</strong></p>
                    <ol style="color:#aaa;margin-top:8px">
                      <li>Click the button below to retry payment</li>
                      <li>Complete the GHS 100 MoMo payment on the secure Paystack page</li>
                      <li>Your card activates automatically — no waiting</li>
                    </ol>
                  </div>
                  <div style="text-align:center;margin-top:24px">
                    <a href="{fan_link}" style="background:linear-gradient(135deg,#b8860b,#f0c040);color:#000;font-weight:800;padding:14px 28px;border-radius:10px;text-decoration:none;display:inline-block">Retry Payment — GHS 100</a>
                  </div>
                  <p style="color:#555;font-size:12px;text-align:center;margin-top:24px">Shatta Movement Official Fan Platform</p>
                </div>
                """
            )
            count += 1
    flash(f"Rejected {len(pending)} pending applications. {count} email notifications sent.", "success")
    return redirect(url_for("admin_gold_cards"))


@app.route("/verify/<card_number>")
def verify_card(card_number):
    db = get_db()
    card = db.execute("""
        SELECT gc.*, f.full_name, f.country, f.fan_number
        FROM gold_cards gc JOIN fans f ON f.id = gc.fan_id
        WHERE gc.card_number = ?
    """, (card_number,)).fetchone()
    db.close()
    return render_template("fans/verify_card.html", card=card, card_number=card_number)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.static_folder, "shatta"),
        "favicon.ico", mimetype="image/vnd.microsoft.icon"
    )


@app.errorhandler(404)
def not_found(e):
    return render_template("fans/errors/404.html"), 404


def create_app():
    init_db()
    return app


application = create_app()

if __name__ == "__main__":
    application.run(debug=True, host="0.0.0.0", port=5000)
