import os
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse
from datetime import datetime as _dt, date as _date
from werkzeug.security import generate_password_hash

# Try each variable in order — Railway injects DATABASE_URL with internal socket,
# so we prefer DATABASE_PUBLIC_URL or DB_URL if available.
DATABASE_URL = (
    os.environ.get("DB_URL") or
    os.environ.get("DATABASE_PUBLIC_URL") or
    os.environ.get("DATABASE_URL", "")
)


def _conn_kwargs():
    """Parse DATABASE_URL into individual psycopg2 connect kwargs."""
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    p = urlparse(url)
    return {
        "host":     p.hostname,
        "port":     p.port or 5432,
        "dbname":   p.path.lstrip("/"),
        "user":     p.username,
        "password": p.password,
        "sslmode":  "require",
        "connect_timeout": 10,
    }


class _Row:
    """Wraps a psycopg2 RealDictRow so templates can use row.col and row["col"] and row[0]."""

    def __init__(self, d):
        processed = {}
        if d:
            for k, v in d.items():
                if isinstance(v, _dt):
                    processed[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(v, _date):
                    processed[k] = v.strftime('%Y-%m-%d')
                else:
                    processed[k] = v
        object.__setattr__(self, '_d', processed)
        object.__setattr__(self, '_vals', list(processed.values()))

    def __getitem__(self, key):
        if isinstance(key, int):
            return object.__getattribute__(self, '_vals')[key]
        return object.__getattribute__(self, '_d')[key]

    def __getattr__(self, key):
        d = object.__getattribute__(self, '_d')
        try:
            return d[key]
        except KeyError:
            raise AttributeError(key)

    def __bool__(self):
        return bool(object.__getattribute__(self, '_d'))

    def get(self, key, default=None):
        return object.__getattribute__(self, '_d').get(key, default)

    def keys(self):
        return object.__getattribute__(self, '_d').keys()

    def __iter__(self):
        return iter(object.__getattribute__(self, '_d'))


class _Cursor:
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        row = self._cur.fetchone()
        return _Row(row) if row is not None else None

    def fetchall(self):
        return [_Row(r) for r in self._cur.fetchall()]

    def __iter__(self):
        return (_Row(r) for r in self._cur)


class _Conn:
    """Thin psycopg2 wrapper that accepts SQLite-style ? placeholders."""

    def __init__(self, conn):
        self._conn = conn
        self._cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, sql, params=()):
        self._cur.execute(sql.replace("?", "%s"), params)
        return _Cursor(self._cur)

    def commit(self):
        self._conn.commit()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def get_db():
    conn = psycopg2.connect(**_conn_kwargs())
    return _Conn(conn)


def init_db():
    conn = psycopg2.connect(**_conn_kwargs())
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fans (
            id SERIAL PRIMARY KEY,
            fan_number TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            whatsapp TEXT,
            country TEXT NOT NULL,
            city TEXT NOT NULL,
            instagram TEXT,
            tiktok TEXT,
            twitter TEXT,
            facebook TEXT,
            favorite_songs TEXT,
            fan_since INTEGER,
            fanbase_id INTEGER,
            is_verified INTEGER DEFAULT 0,
            registered_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fanbases (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            city TEXT,
            continent TEXT NOT NULL,
            leader_name TEXT,
            leader_contact TEXT,
            member_count INTEGER DEFAULT 0,
            is_official INTEGER DEFAULT 1,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            image_url TEXT,
            link_url TEXT,
            is_pinned INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS gold_cards (
            id SERIAL PRIMARY KEY,
            fan_id INTEGER UNIQUE NOT NULL REFERENCES fans(id),
            card_number TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            proof_path TEXT,
            amount_paid INTEGER DEFAULT 100,
            valid_until TEXT,
            approved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    conn.commit()
    _seed_fanbases(cur, conn)
    _create_admin(cur, conn)
    conn.close()


def _seed_fanbases(cur, conn):
    cur.execute("SELECT COUNT(*) FROM fanbases")
    if cur.fetchone()[0] > 0:
        return

    fanbases = [
        ("SM Ghana", "Ghana", "Accra", "Africa"),
        ("SM Nigeria", "Nigeria", "Lagos", "Africa"),
        ("SM South Africa", "South Africa", "Johannesburg", "Africa"),
        ("SM Ivory Coast", "Ivory Coast", "Abidjan", "Africa"),
        ("SM Togo", "Togo", "Lomé", "Africa"),
        ("SM Burkina Faso", "Burkina Faso", "Ouagadougou", "Africa"),
        ("SM Senegal", "Senegal", "Dakar", "Africa"),
        ("SM Cameroon", "Cameroon", "Douala", "Africa"),
        ("SM UK", "United Kingdom", "London", "Europe"),
        ("SM Germany", "Germany", "Berlin", "Europe"),
        ("SM Italy", "Italy", "Rome", "Europe"),
        ("SM Netherlands", "Netherlands", "Amsterdam", "Europe"),
        ("SM France", "France", "Paris", "Europe"),
        ("SM Spain", "Spain", "Madrid", "Europe"),
        ("SM USA", "United States", "New York", "Americas"),
        ("SM Canada", "Canada", "Toronto", "Americas"),
        ("SM Brazil", "Brazil", "São Paulo", "Americas"),
        ("SM Australia", "Australia", "Sydney", "Asia Pacific"),
        ("SM Japan", "Japan", "Tokyo", "Asia Pacific"),
        ("SM UAE", "United Arab Emirates", "Dubai", "Middle East"),
    ]

    for name, country, city, continent in fanbases:
        cur.execute(
            "INSERT INTO fanbases (name, country, city, continent) VALUES (%s, %s, %s, %s)",
            (name, country, city, continent)
        )
    conn.commit()


def _create_admin(cur, conn):
    cur.execute("SELECT COUNT(*) FROM admins")
    if cur.fetchone()[0] > 0:
        return
    pw = os.environ.get("ADMIN_PASSWORD", "ShattaFans2024!")
    cur.execute(
        "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
        ("admin", generate_password_hash(pw))
    )
    conn.commit()


def generate_fan_number():
    import random
    import string
    return "SM" + "".join(random.choices(string.digits, k=6))
