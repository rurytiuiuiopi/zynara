import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "fans.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS fans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        registered_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS fanbases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        country TEXT NOT NULL,
        city TEXT,
        continent TEXT NOT NULL,
        leader_name TEXT,
        leader_contact TEXT,
        member_count INTEGER DEFAULT 0,
        is_official INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        image_url TEXT,
        link_url TEXT,
        is_pinned INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS gold_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fan_id INTEGER UNIQUE NOT NULL,
        card_number TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'pending',
        proof_path TEXT,
        amount_paid INTEGER DEFAULT 100,
        valid_until TEXT,
        approved_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (fan_id) REFERENCES fans(id)
    );
    """)

    conn.commit()
    _seed_fanbases(c, conn)
    _create_admin(c, conn)
    conn.close()

def _seed_fanbases(c, conn):
    existing = c.execute("SELECT COUNT(*) FROM fanbases").fetchone()[0]
    if existing > 0:
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
        c.execute(
            "INSERT INTO fanbases (name, country, city, continent) VALUES (?, ?, ?, ?)",
            (name, country, city, continent)
        )
    conn.commit()

def _create_admin(c, conn):
    from werkzeug.security import generate_password_hash
    exists = c.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    if exists:
        return
    pw = os.environ.get("ADMIN_PASSWORD", "ShattaFans2024!")
    c.execute(
        "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
        ("admin", generate_password_hash(pw))
    )
    conn.commit()

def generate_fan_number():
    import random
    import string
    return "SM" + "".join(random.choices(string.digits, k=6))
