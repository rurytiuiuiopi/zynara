import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "shatta_market.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'vendor',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            full_name TEXT NOT NULL,
            business_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            whatsapp TEXT,
            business_location TEXT NOT NULL,
            business_category TEXT NOT NULL,
            social_links TEXT DEFAULT '{}',
            id_card_path TEXT,
            selfie_path TEXT,
            momo_number TEXT,
            bank_details TEXT DEFAULT '{}',
            verified_status TEXT DEFAULT 'unverified',
            trust_badge TEXT DEFAULT 'none',
            is_suspended INTEGER DEFAULT 0,
            suspension_reason TEXT,
            admin_notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER REFERENCES vendors(id),
            plan TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT,
            payment_reference TEXT,
            payment_proof_path TEXT,
            status TEXT DEFAULT 'pending',
            approved_by INTEGER REFERENCES users(id),
            expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER REFERENCES vendors(id),
            flyer_path TEXT,
            video_path TEXT,
            product_images TEXT DEFAULT '[]',
            business_description TEXT NOT NULL,
            prices TEXT DEFAULT '{}',
            contact_details TEXT NOT NULL,
            promotion_date DATE,
            status TEXT DEFAULT 'pending',
            ai_risk_score INTEGER DEFAULT 0,
            ai_caption TEXT,
            ai_hashtags TEXT DEFAULT '[]',
            ai_warnings TEXT DEFAULT '[]',
            admin_notes TEXT,
            reviewed_by INTEGER REFERENCES users(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER REFERENCES vendors(id),
            reviewer_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            is_flagged INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            momo_number TEXT,
            email TEXT,
            business_name TEXT,
            reason TEXT NOT NULL,
            added_by INTEGER REFERENCES users(id),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customer_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER REFERENCES vendors(id),
            reporter_name TEXT,
            reporter_phone TEXT,
            report_reason TEXT NOT NULL,
            details TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()


def create_default_admin():
    from werkzeug.security import generate_password_hash
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@shattamarket.com")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "ShattaAdmin2024!")

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
            (admin_email, generate_password_hash(admin_pass), "super_admin")
        )
        conn.commit()
    conn.close()
