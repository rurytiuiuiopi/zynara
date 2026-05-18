import os
import json
import uuid
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from shatta_db import get_db, init_db, create_default_admin
from shatta_ai import run_full_analysis, BUSINESS_CATEGORIES

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "shatta-tuesday-market-secret-2024")

# Custom Jinja2 filter: parse JSON strings in templates
@app.template_filter("from_json")
def from_json_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []

UPLOAD_BASE = os.path.join(os.path.dirname(__file__), "static", "shatta", "uploads")
ALLOWED_IMAGE = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_VIDEO = {"mp4", "mov", "avi", "webm"}
ALLOWED_DOC = {"jpg", "jpeg", "png", "pdf"}
MAX_FILE_MB = 50

PLANS = {
    "basic":    {"name": "Basic",    "amount": 300,   "promotions": 3,  "description": "3 promotions/month"},
    "standard": {"name": "Standard", "amount": 600,   "promotions": 10, "description": "10 promotions/month"},
    "premium":  {"name": "Premium",  "amount": 1200,  "promotions": 999,"description": "Unlimited promotions/month"},
}


# ── Helpers ────────────────────────────────────────────────────────

def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


def save_upload(file, subfolder, allowed_set):
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename, allowed_set):
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    save_dir = os.path.join(UPLOAD_BASE, subfolder)
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, filename))
    return f"shatta/uploads/{subfolder}/{filename}"


def get_file_size(file):
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    return size


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return user


def get_vendor(user_id):
    conn = get_db()
    v = conn.execute("SELECT * FROM vendors WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return v


def get_active_subscription(vendor_id):
    conn = get_db()
    sub = conn.execute(
        "SELECT * FROM subscriptions WHERE vendor_id = ? AND status = 'approved' AND expires_at > datetime('now') ORDER BY expires_at DESC LIMIT 1",
        (vendor_id,)
    ).fetchone()
    conn.close()
    return sub


# ── Auth decorators ────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def vendor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        user = current_user()
        if user and user["role"] not in ("vendor",):
            flash("Access denied.", "danger")
            return redirect(url_for("index"))
        vendor = get_vendor(user["id"])
        if not vendor:
            return redirect(url_for("register"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = current_user()
        if not user or user["role"] not in ("admin", "super_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Public routes ──────────────────────────────────────────────────

@app.route("/")
def index():
    conn = get_db()
    approved = conn.execute(
        """SELECT p.*, v.business_name, v.business_category, v.trust_badge, v.full_name
           FROM promotions p JOIN vendors v ON p.vendor_id = v.id
           WHERE p.status = 'approved' ORDER BY p.created_at DESC LIMIT 12"""
    ).fetchall()
    stats = {
        "vendors": conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0],
        "promotions": conn.execute("SELECT COUNT(*) FROM promotions WHERE status='approved'").fetchone()[0],
    }
    conn.close()
    return render_template("shatta/index.html", promotions=approved, stats=stats, plans=PLANS)


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("vendor_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        business_name = request.form.get("business_name", "").strip()
        phone = request.form.get("phone", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip()
        location = request.form.get("business_location", "").strip()
        category = request.form.get("business_category", "").strip()
        momo_number = request.form.get("momo_number", "").strip()
        bank_name = request.form.get("bank_name", "").strip()
        bank_account = request.form.get("bank_account", "").strip()

        social_links = json.dumps({
            "facebook": request.form.get("facebook", ""),
            "instagram": request.form.get("instagram", ""),
            "twitter": request.form.get("twitter", ""),
            "tiktok": request.form.get("tiktok", ""),
        })
        bank_details = json.dumps({"bank_name": bank_name, "account_number": bank_account})

        if not all([email, password, full_name, business_name, phone, location, category]):
            flash("Please fill in all required fields.", "danger")
            return render_template("shatta/auth/register.html", categories=BUSINESS_CATEGORIES)

        conn = get_db()
        if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            conn.close()
            flash("Email already registered. Please log in.", "warning")
            return render_template("shatta/auth/register.html", categories=BUSINESS_CATEGORIES)

        # Handle file uploads
        id_card_path = None
        selfie_path = None

        if "id_card" in request.files:
            id_card_path = save_upload(request.files["id_card"], "ids", ALLOWED_DOC)
        if "selfie" in request.files:
            selfie_path = save_upload(request.files["selfie"], "selfies", ALLOWED_IMAGE)

        try:
            cursor = conn.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (?, ?, 'vendor')",
                (email, generate_password_hash(password))
            )
            user_id = cursor.lastrowid

            conn.execute(
                """INSERT INTO vendors
                   (user_id, full_name, business_name, phone, whatsapp,
                    business_location, business_category, social_links,
                    id_card_path, selfie_path, momo_number, bank_details)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, full_name, business_name, phone, whatsapp,
                 location, category, social_links,
                 id_card_path, selfie_path, momo_number, bank_details)
            )
            conn.commit()
            conn.close()

            session["user_id"] = user_id
            session["role"] = "vendor"
            flash(f"Welcome, {full_name}! Your account is created. Subscribe to start promoting.", "success")
            return redirect(url_for("vendor_subscription"))
        except Exception as e:
            conn.close()
            flash("Registration failed. Please try again.", "danger")
            return render_template("shatta/auth/register.html", categories=BUSINESS_CATEGORIES)

    return render_template("shatta/auth/register.html", categories=BUSINESS_CATEGORIES)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        user = current_user()
        if user and user["role"] in ("admin", "super_admin"):
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("vendor_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            flash(f"Welcome back!", "success")
            if user["role"] in ("admin", "super_admin"):
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("vendor_dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("shatta/auth/login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ── Vendor routes ──────────────────────────────────────────────────

@app.route("/vendor/dashboard")
@login_required
def vendor_dashboard():
    user = current_user()
    if user["role"] in ("admin", "super_admin"):
        return redirect(url_for("admin_dashboard"))

    vendor = get_vendor(user["id"])
    if not vendor:
        return redirect(url_for("register"))

    conn = get_db()
    promotions = conn.execute(
        "SELECT * FROM promotions WHERE vendor_id = ? ORDER BY created_at DESC",
        (vendor["id"],)
    ).fetchall()
    sub = get_active_subscription(vendor["id"])
    pending_sub = conn.execute(
        "SELECT * FROM subscriptions WHERE vendor_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
        (vendor["id"],)
    ).fetchone()
    avg_rating = conn.execute(
        "SELECT AVG(rating) FROM reviews WHERE vendor_id = ?", (vendor["id"],)
    ).fetchone()[0]
    reviews = conn.execute(
        "SELECT * FROM reviews WHERE vendor_id = ? ORDER BY created_at DESC LIMIT 5",
        (vendor["id"],)
    ).fetchall()
    conn.close()

    promo_this_month = sum(
        1 for p in promotions
        if p["created_at"] and p["created_at"][:7] == datetime.now().strftime("%Y-%m")
    )

    return render_template(
        "shatta/vendor/dashboard.html",
        vendor=vendor,
        promotions=promotions,
        subscription=sub,
        pending_sub=pending_sub,
        avg_rating=round(avg_rating, 1) if avg_rating else None,
        reviews=reviews,
        plans=PLANS,
        promo_this_month=promo_this_month,
    )


@app.route("/vendor/subscription", methods=["GET", "POST"])
@login_required
def vendor_subscription():
    user = current_user()
    vendor = get_vendor(user["id"])
    if not vendor:
        return redirect(url_for("register"))

    active_sub = get_active_subscription(vendor["id"])

    if request.method == "POST":
        plan = request.form.get("plan", "").lower()
        payment_method = request.form.get("payment_method", "")
        payment_reference = request.form.get("payment_reference", "").strip()

        if plan not in PLANS:
            flash("Invalid plan selected.", "danger")
            return redirect(url_for("vendor_subscription"))

        proof_path = None
        if "payment_proof" in request.files:
            proof_path = save_upload(request.files["payment_proof"], "proofs", ALLOWED_DOC)

        conn = get_db()
        conn.execute(
            """INSERT INTO subscriptions
               (vendor_id, plan, amount, payment_method, payment_reference, payment_proof_path, status)
               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (vendor["id"], plan, PLANS[plan]["amount"], payment_method, payment_reference, proof_path)
        )
        conn.commit()
        conn.close()

        flash("Subscription request submitted! Admin will review and approve within 24 hours.", "success")
        return redirect(url_for("vendor_dashboard"))

    return render_template(
        "shatta/vendor/subscription.html",
        vendor=vendor,
        plans=PLANS,
        active_sub=active_sub,
    )


@app.route("/vendor/upload", methods=["GET", "POST"])
@login_required
def vendor_upload():
    user = current_user()
    vendor = get_vendor(user["id"])
    if not vendor:
        return redirect(url_for("register"))

    sub = get_active_subscription(vendor["id"])
    if not sub:
        flash("You need an active subscription to upload promotions.", "warning")
        return redirect(url_for("vendor_subscription"))

    # Check monthly promotion limit
    plan_key = sub["plan"]
    limit = PLANS.get(plan_key, {}).get("promotions", 3)
    conn = get_db()
    this_month = conn.execute(
        "SELECT COUNT(*) FROM promotions WHERE vendor_id = ? AND strftime('%Y-%m', created_at) = ?",
        (vendor["id"], datetime.now().strftime("%Y-%m"))
    ).fetchone()[0]
    conn.close()

    if this_month >= limit:
        flash(f"You've reached your monthly limit of {limit} promotions for your {plan_key.title()} plan.", "warning")
        return redirect(url_for("vendor_dashboard"))

    if request.method == "POST":
        description = request.form.get("business_description", "").strip()
        contact_details = request.form.get("contact_details", "").strip()
        prices_text = request.form.get("prices", "").strip()
        promotion_date = request.form.get("promotion_date", "")

        if not description or not contact_details:
            flash("Description and contact details are required.", "danger")
            return render_template("shatta/vendor/upload.html", vendor=vendor, sub=sub)

        flyer_path = None
        video_path = None
        flyer_size = 0

        if "flyer" in request.files and request.files["flyer"].filename:
            f = request.files["flyer"]
            flyer_size = get_file_size(f)
            flyer_path = save_upload(f, "flyers", ALLOWED_IMAGE)

        if "video" in request.files and request.files["video"].filename:
            video_path = save_upload(request.files["video"], "videos", ALLOWED_VIDEO)

        product_images = []
        for img_file in request.files.getlist("product_images"):
            if img_file and img_file.filename:
                path = save_upload(img_file, "products", ALLOWED_IMAGE)
                if path:
                    product_images.append(path)

        # Run AI moderation
        ai_result = run_full_analysis(
            vendor_id=vendor["id"],
            description=description,
            contact_details=contact_details,
            prices_text=prices_text,
            flyer_size=flyer_size,
            vendor_phone=vendor["phone"],
            vendor_momo=vendor["momo_number"] or "",
            vendor_email=user["email"],
            business_name=vendor["business_name"],
            vendor_name=vendor["full_name"],
            category=vendor["business_category"],
            location=vendor["business_location"],
            id_verified=vendor["verified_status"] == "verified",
        )

        conn = get_db()
        conn.execute(
            """INSERT INTO promotions
               (vendor_id, flyer_path, video_path, product_images, business_description,
                prices, contact_details, promotion_date, status,
                ai_risk_score, ai_caption, ai_hashtags, ai_warnings)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
            (
                vendor["id"], flyer_path, video_path,
                json.dumps(product_images), description,
                json.dumps({"text": prices_text}), contact_details, promotion_date,
                ai_result["risk_score"],
                ai_result["caption"],
                json.dumps(ai_result["hashtags"]),
                json.dumps(ai_result["warnings"]),
            )
        )
        conn.commit()
        conn.close()

        flash("Promotion submitted for review! You'll be notified once approved.", "success")
        return redirect(url_for("vendor_dashboard"))

    return render_template("shatta/vendor/upload.html", vendor=vendor, sub=sub)


@app.route("/vendor/review/<int:vendor_id>", methods=["POST"])
def submit_review(vendor_id):
    reviewer_name = request.form.get("reviewer_name", "Anonymous").strip()
    rating = int(request.form.get("rating", 5))
    comment = request.form.get("comment", "").strip()

    if not 1 <= rating <= 5:
        flash("Invalid rating.", "danger")
        return redirect(url_for("index"))

    conn = get_db()
    conn.execute(
        "INSERT INTO reviews (vendor_id, reviewer_name, rating, comment) VALUES (?, ?, ?, ?)",
        (vendor_id, reviewer_name, rating, comment)
    )
    conn.commit()
    conn.close()
    flash("Thank you for your review!", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/report/<int:vendor_id>", methods=["POST"])
def report_vendor(vendor_id):
    reporter_name = request.form.get("reporter_name", "").strip()
    reporter_phone = request.form.get("reporter_phone", "").strip()
    reason = request.form.get("reason", "").strip()
    details = request.form.get("details", "").strip()

    if not reason:
        flash("Please provide a reason for the report.", "danger")
        return redirect(request.referrer or url_for("index"))

    conn = get_db()
    conn.execute(
        "INSERT INTO customer_reports (vendor_id, reporter_name, reporter_phone, report_reason, details) VALUES (?, ?, ?, ?, ?)",
        (vendor_id, reporter_name, reporter_phone, reason, details)
    )
    conn.commit()
    conn.close()
    flash("Report submitted. Thank you for helping keep the market safe.", "success")
    return redirect(request.referrer or url_for("index"))


# ── Admin routes ───────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()
    stats = {
        "total_vendors": conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0],
        "pending_subs": conn.execute("SELECT COUNT(*) FROM subscriptions WHERE status='pending'").fetchone()[0],
        "pending_promos": conn.execute("SELECT COUNT(*) FROM promotions WHERE status='pending'").fetchone()[0],
        "approved_promos": conn.execute("SELECT COUNT(*) FROM promotions WHERE status='approved'").fetchone()[0],
        "total_reports": conn.execute("SELECT COUNT(*) FROM customer_reports WHERE status='pending'").fetchone()[0],
        "blacklisted": conn.execute("SELECT COUNT(*) FROM blacklist").fetchone()[0],
    }
    recent_submissions = conn.execute(
        """SELECT p.*, v.full_name, v.business_name, v.business_category,
                  v.verified_status, v.trust_badge
           FROM promotions p JOIN vendors v ON p.vendor_id = v.id
           WHERE p.status = 'pending'
           ORDER BY p.ai_risk_score DESC, p.created_at DESC LIMIT 10"""
    ).fetchall()
    recent_subs = conn.execute(
        """SELECT s.*, v.full_name, v.business_name
           FROM subscriptions s JOIN vendors v ON s.vendor_id = v.id
           WHERE s.status = 'pending' ORDER BY s.created_at DESC LIMIT 5"""
    ).fetchall()
    conn.close()
    return render_template(
        "shatta/admin/dashboard.html",
        stats=stats,
        recent_submissions=recent_submissions,
        recent_subs=recent_subs,
    )


@app.route("/admin/submissions")
@admin_required
def admin_submissions():
    status_filter = request.args.get("status", "pending")
    conn = get_db()
    query = """
        SELECT p.*, v.full_name, v.business_name, v.business_category,
               v.verified_status, v.trust_badge, v.phone, v.momo_number,
               u.email
        FROM promotions p
        JOIN vendors v ON p.vendor_id = v.id
        JOIN users u ON v.user_id = u.id
    """
    if status_filter != "all":
        rows = conn.execute(query + " WHERE p.status = ? ORDER BY p.ai_risk_score DESC, p.created_at DESC", (status_filter,)).fetchall()
    else:
        rows = conn.execute(query + " ORDER BY p.created_at DESC").fetchall()
    conn.close()
    return render_template(
        "shatta/admin/submissions.html",
        submissions=rows,
        status_filter=status_filter,
    )


@app.route("/admin/submissions/<int:promo_id>/<action>", methods=["POST"])
@admin_required
def admin_review_submission(promo_id, action):
    if action not in ("approve", "reject", "hold"):
        abort(400)

    user = current_user()
    notes = request.form.get("notes", "")
    conn = get_db()
    conn.execute(
        "UPDATE promotions SET status = ?, admin_notes = ?, reviewed_by = ? WHERE id = ?",
        (action + "d" if action != "hold" else "held", notes, user["id"], promo_id)
    )
    conn.commit()
    conn.close()
    flash(f"Promotion {action}d successfully.", "success")
    return redirect(url_for("admin_submissions"))


@app.route("/admin/subscriptions")
@admin_required
def admin_subscriptions():
    conn = get_db()
    subs = conn.execute(
        """SELECT s.*, v.full_name, v.business_name, v.phone
           FROM subscriptions s JOIN vendors v ON s.vendor_id = v.id
           ORDER BY CASE s.status WHEN 'pending' THEN 0 ELSE 1 END, s.created_at DESC"""
    ).fetchall()
    conn.close()
    return render_template("shatta/admin/subscriptions.html", subscriptions=subs, plans=PLANS)


@app.route("/admin/subscriptions/<int:sub_id>/<action>", methods=["POST"])
@admin_required
def admin_review_subscription(sub_id, action):
    if action not in ("approve", "reject"):
        abort(400)

    user = current_user()
    conn = get_db()
    sub = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
    if not sub:
        conn.close()
        abort(404)

    if action == "approve":
        expires = datetime.now() + timedelta(days=365)
        conn.execute(
            "UPDATE subscriptions SET status='approved', approved_by=?, expires_at=? WHERE id=?",
            (user["id"], expires.isoformat(), sub_id)
        )
    else:
        conn.execute("UPDATE subscriptions SET status='rejected', approved_by=? WHERE id=?", (user["id"], sub_id))

    conn.commit()
    conn.close()
    flash(f"Subscription {action}d.", "success")
    return redirect(url_for("admin_subscriptions"))


@app.route("/admin/vendors")
@admin_required
def admin_vendors():
    conn = get_db()
    vendors = conn.execute(
        """SELECT v.*, u.email,
                  (SELECT status FROM subscriptions WHERE vendor_id = v.id AND status='approved'
                   AND expires_at > datetime('now') LIMIT 1) as active_sub,
                  (SELECT COUNT(*) FROM promotions WHERE vendor_id = v.id AND status='approved') as approved_promos,
                  (SELECT AVG(rating) FROM reviews WHERE vendor_id = v.id) as avg_rating
           FROM vendors v JOIN users u ON v.user_id = u.id
           ORDER BY v.created_at DESC"""
    ).fetchall()
    conn.close()
    return render_template("shatta/admin/vendors.html", vendors=vendors)


@app.route("/admin/vendors/<int:vendor_id>/<action>", methods=["POST"])
@admin_required
def admin_vendor_action(vendor_id, action):
    conn = get_db()
    user = current_user()

    if action == "verify":
        conn.execute("UPDATE vendors SET verified_status='verified' WHERE id=?", (vendor_id,))
        flash("Vendor verified.", "success")

    elif action == "unverify":
        conn.execute("UPDATE vendors SET verified_status='unverified' WHERE id=?", (vendor_id,))
        flash("Vendor unverified.", "info")

    elif action == "suspend":
        reason = request.form.get("reason", "Policy violation")
        conn.execute("UPDATE vendors SET is_suspended=1, suspension_reason=? WHERE id=?", (reason, vendor_id))
        flash("Vendor suspended.", "warning")

    elif action == "unsuspend":
        conn.execute("UPDATE vendors SET is_suspended=0, suspension_reason=NULL WHERE id=?", (vendor_id,))
        flash("Vendor reinstated.", "success")

    elif action in ("verified_badge", "trusted_badge", "no_badge"):
        badge = action.replace("_badge", "").replace("no", "none")
        conn.execute("UPDATE vendors SET trust_badge=? WHERE id=?", (badge, vendor_id))
        flash("Badge updated.", "success")

    elif action == "note":
        note = request.form.get("note", "")
        conn.execute("UPDATE vendors SET admin_notes=? WHERE id=?", (note, vendor_id))
        flash("Note saved.", "success")

    elif action == "blacklist":
        vendor = conn.execute("SELECT * FROM vendors WHERE id=?", (vendor_id,)).fetchone()
        v_user = conn.execute("SELECT * FROM users WHERE id=?", (vendor["user_id"],)).fetchone()
        reason = request.form.get("reason", "Fraud / Policy violation")
        conn.execute(
            "INSERT INTO blacklist (phone, momo_number, email, business_name, reason, added_by) VALUES (?,?,?,?,?,?)",
            (vendor["phone"], vendor["momo_number"], v_user["email"], vendor["business_name"], reason, user["id"])
        )
        conn.execute("UPDATE vendors SET is_suspended=1, suspension_reason=? WHERE id=?", (reason, vendor_id))
        flash("Vendor added to blacklist and suspended.", "danger")

    conn.commit()
    conn.close()
    return redirect(url_for("admin_vendors"))


@app.route("/admin/blacklist", methods=["GET", "POST"])
@admin_required
def admin_blacklist():
    conn = get_db()
    if request.method == "POST":
        user = current_user()
        conn.execute(
            "INSERT INTO blacklist (phone, momo_number, email, business_name, reason, added_by) VALUES (?,?,?,?,?,?)",
            (
                request.form.get("phone", ""),
                request.form.get("momo_number", ""),
                request.form.get("email", ""),
                request.form.get("business_name", ""),
                request.form.get("reason", ""),
                user["id"],
            )
        )
        conn.commit()
        flash("Added to blacklist.", "success")

    entries = conn.execute(
        "SELECT bl.*, u.email as added_by_email FROM blacklist bl LEFT JOIN users u ON bl.added_by = u.id ORDER BY bl.created_at DESC"
    ).fetchall()
    conn.close()
    return render_template("shatta/admin/blacklist.html", entries=entries)


@app.route("/admin/blacklist/<int:entry_id>/remove", methods=["POST"])
@admin_required
def remove_blacklist(entry_id):
    conn = get_db()
    conn.execute("DELETE FROM blacklist WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()
    flash("Removed from blacklist.", "success")
    return redirect(url_for("admin_blacklist"))


@app.route("/admin/reports")
@admin_required
def admin_reports():
    conn = get_db()
    reports = conn.execute(
        """SELECT cr.*, v.business_name, v.full_name
           FROM customer_reports cr JOIN vendors v ON cr.vendor_id = v.id
           ORDER BY CASE cr.status WHEN 'pending' THEN 0 ELSE 1 END, cr.created_at DESC"""
    ).fetchall()
    conn.close()
    return render_template("shatta/admin/reports.html", reports=reports)


@app.route("/admin/reports/<int:report_id>/resolve", methods=["POST"])
@admin_required
def resolve_report(report_id):
    conn = get_db()
    conn.execute("UPDATE customer_reports SET status='resolved' WHERE id=?", (report_id,))
    conn.commit()
    conn.close()
    flash("Report marked as resolved.", "success")
    return redirect(url_for("admin_reports"))


# ── API endpoints ──────────────────────────────────────────────────

@app.route("/api/promotion/<int:promo_id>/post-data")
@admin_required
def get_post_data(promo_id):
    """Return caption, hashtags, and media URL for social media posting."""
    conn = get_db()
    promo = conn.execute(
        """SELECT p.*, v.business_name, v.full_name, v.business_location, v.business_category
           FROM promotions p JOIN vendors v ON p.vendor_id = v.id
           WHERE p.id = ?""",
        (promo_id,)
    ).fetchone()
    conn.close()

    if not promo:
        return jsonify({"error": "Not found"}), 404

    hashtags = json.loads(promo["ai_hashtags"] or "[]")
    return jsonify({
        "caption": promo["ai_caption"],
        "hashtags": " ".join(hashtags),
        "full_post": f"{promo['ai_caption']}\n\n{' '.join(hashtags)}",
        "flyer_url": f"/static/{promo['flyer_path']}" if promo["flyer_path"] else None,
        "video_url": f"/static/{promo['video_path']}" if promo["video_path"] else None,
    })


@app.route("/api/vendor/<int:vendor_id>/public")
def vendor_public(vendor_id):
    conn = get_db()
    vendor = conn.execute(
        """SELECT v.business_name, v.full_name, v.business_category, v.business_location,
                  v.trust_badge, v.verified_status, v.social_links,
                  AVG(r.rating) as avg_rating, COUNT(r.id) as review_count
           FROM vendors v
           LEFT JOIN reviews r ON r.vendor_id = v.id
           WHERE v.id = ? AND v.is_suspended = 0
           GROUP BY v.id""",
        (vendor_id,)
    ).fetchone()
    if not vendor:
        return jsonify({"error": "Not found"}), 404
    promos = conn.execute(
        "SELECT * FROM promotions WHERE vendor_id = ? AND status = 'approved' ORDER BY created_at DESC LIMIT 6",
        (vendor_id,)
    ).fetchall()
    conn.close()
    return jsonify({
        "vendor": dict(vendor),
        "promotions": [dict(p) for p in promos],
    })


# ── Static uploads ─────────────────────────────────────────────────

@app.route("/static/shatta/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(os.path.join(UPLOAD_BASE), filename)


# ── Startup ────────────────────────────────────────────────────────

def create_app():
    init_db()
    create_default_admin()
    os.makedirs(UPLOAD_BASE, exist_ok=True)
    for sub in ["ids", "selfies", "flyers", "videos", "products", "proofs"]:
        os.makedirs(os.path.join(UPLOAD_BASE, sub), exist_ok=True)
    return app


application = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SHATTA TUESDAY MARKET")
    print("  Promoting Ghanaian Businesses. Supporting The People.")
    print(f"  Admin: {os.environ.get('ADMIN_EMAIL', 'admin@shattamarket.com')}")
    print("  Open: http://localhost:5000")
    print("=" * 60 + "\n")
    application.run(debug=True, host="0.0.0.0", port=5000)
