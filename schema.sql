-- Cortefy SaaS Database Schema (Cloudflare D1 SQL)

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    plan TEXT DEFAULT 'free', -- 'free', 'pro', 'creator'
    monthly_credits INTEGER DEFAULT 3,
    credits_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    video_title TEXT,
    source_url TEXT,
    broll_mode TEXT DEFAULT 'auto_extract',
    broll_url TEXT,
    duration REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS cuts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT,
    hook TEXT,
    start_time REAL,
    end_time REAL,
    virality_score INTEGER,
    tag TEXT,
    video_url TEXT, -- URL pública no Cloudflare R2
    status TEXT DEFAULT 'pending', -- 'pending', 'ready', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    plan_tier TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    current_period_end TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
