import sqlite3
import os
import uuid
import hashlib
import time
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cortefy.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        name TEXT,
        plan TEXT DEFAULT 'free', -- 'free', 'creator', 'pro'
        monthly_credits INTEGER DEFAULT 3,
        credits_used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        expires_at REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS magic_links (
        token TEXT PRIMARY KEY,
        email TEXT NOT NULL,
        expires_at REAL NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        plan TEXT NOT NULL,
        amount_cents INTEGER NOT NULL,
        status TEXT DEFAULT 'pending', -- 'pending', 'paid', 'expired'
        pix_code TEXT,
        qr_code_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    conn.commit()

    # Cria usuário de demonstração se não existir
    demo_email = "demo@cortefy.com.br"
    cursor.execute("SELECT id FROM users WHERE email = ?", (demo_email,))
    if not cursor.fetchone():
        demo_id = "user_demo_01"
        pwd_hash = hash_password("cortefy123")
        cursor.execute("""
        INSERT INTO users (id, email, password_hash, name, plan, monthly_credits, credits_used)
        VALUES (?, ?, ?, ?, 'creator', 100, 18)
        """, (demo_id, demo_email, pwd_hash, "Criador Cortefy"))
        conn.commit()

    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def create_user(email: str, password: Optional[str] = None, name: Optional[str] = None, plan: str = "free") -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    pwd_hash = hash_password(password) if password else None
    display_name = name or email.split("@")[0].capitalize()
    credits = 100 if plan == "creator" else (999 if plan == "pro" else 5)
    
    try:
        cursor.execute("""
        INSERT INTO users (id, email, password_hash, name, plan, monthly_credits, credits_used)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (user_id, email.lower().strip(), pwd_hash, display_name, plan, credits))
        conn.commit()
        return get_user_by_id(user_id)
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE lower(email) = ?", (email.lower().strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_session(user_id: str, days: int = 30) -> str:
    conn = get_db()
    cursor = conn.cursor()
    token = f"sess_{uuid.uuid4().hex}"
    expires_at = time.time() + (days * 86400)
    try:
        cursor.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)", (token, user_id, expires_at))
        conn.commit()
        return token
    finally:
        conn.close()

def get_user_from_session(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT u.* FROM users u
        JOIN sessions s ON u.id = s.user_id
        WHERE s.token = ? AND s.expires_at > ?
        """, (token, time.time()))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def delete_session(token: str):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()

def create_magic_link(email: str) -> str:
    conn = get_db()
    cursor = conn.cursor()
    token = f"magic_{uuid.uuid4().hex}"
    expires_at = time.time() + 1800 # 30 minutos
    try:
        cursor.execute("INSERT INTO magic_links (token, email, expires_at) VALUES (?, ?, ?)", (token, email.lower().strip(), expires_at))
        conn.commit()
        return token
    finally:
        conn.close()

def verify_magic_link(token: str) -> Optional[str]:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT email FROM magic_links WHERE token = ? AND expires_at > ? AND used = 0", (token, time.time()))
        row = cursor.fetchone()
        if row:
            email = row["email"]
            cursor.execute("UPDATE magic_links SET used = 1 WHERE token = ?", (token,))
            conn.commit()
            return email
        return None
    finally:
        conn.close()

def update_user_plan(user_id: str, plan: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    credits = 100 if plan == "creator" else (999 if plan == "pro" else 5)
    try:
        cursor.execute("UPDATE users SET plan = ?, monthly_credits = ? WHERE id = ?", (plan, credits, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def increment_user_credits_used(user_id: str) -> int:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET credits_used = credits_used + 1 WHERE id = ?", (user_id,))
        conn.commit()
        cursor.execute("SELECT credits_used FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return row["credits_used"] if row else 1
    finally:
        conn.close()

# Inicializa banco de dados
init_db()
