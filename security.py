import os
import time
import secrets
import hmac
import logging
from collections import defaultdict
from functools import wraps
from flask import request, session, abort

_audit = logging.getLogger("sm.audit")
if not _audit.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[AUDIT] %(asctime)s %(message)s"))
    _audit.addHandler(_h)
_audit.setLevel(logging.INFO)


def audit(status, note=""):
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
    admin = session.get("admin_id", "-")
    _audit.info("ip=%-15s admin=%-3s %-5s %-42s %s %s", ip, admin, request.method, request.path[:42], status, note)


_rl = defaultdict(list)


def _rl_ok(key, limit, window):
    now = time.time()
    _rl[key] = [t for t in _rl[key] if now - t < window]
    if len(_rl[key]) >= limit:
        return False
    _rl[key].append(now)
    return True


def rate_limit(limit=30, window=60):
    def dec(f):
        @wraps(f)
        def inner(*a, **kw):
            ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
            if not _rl_ok(f"{f.__name__}:{ip}", limit, window):
                audit(429, "rate_limited")
                abort(429)
            return f(*a, **kw)
        return inner
    return dec


_fail_counts: dict = defaultdict(int)
_blocked_ips: set = set()


def record_auth_failure(ip: str):
    _fail_counts[ip] += 1
    if _fail_counts[ip] >= 15:
        _blocked_ips.add(ip)
        _audit.warning("AUTO-BLOCKED ip=%s (failures=%d)", ip, _fail_counts[ip])


def ip_guard():
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
    if ip in _blocked_ips:
        audit(403, "blocked_ip")
        abort(403)


def is_lockdown() -> bool:
    return os.environ.get("LOCKDOWN_MODE", "").lower() in ("1", "true", "yes")


def _allowed_ips() -> set:
    raw = os.environ.get("ALLOWED_IPS", "")
    return {s.strip() for s in raw.split(",") if s.strip()}


def lockdown_guard():
    if not is_lockdown():
        return
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
    allowed = _allowed_ips()
    if allowed and ip not in allowed:
        audit(403, f"lockdown ip={ip}")
        abort(403)


def csrf_token() -> str:
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(32)
    return session["_csrf"]


def validate_csrf():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    provided = request.form.get("_csrf") or request.headers.get("X-CSRF-Token", "")
    expected = session.get("_csrf", "")
    if not (provided and expected and hmac.compare_digest(str(provided), str(expected))):
        audit(403, "csrf_fail")
        abort(403)
