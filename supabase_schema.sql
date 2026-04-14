-- Run this in your Supabase SQL Editor to create the jobs table

CREATE TABLE jobs (
    id          TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'processing',  -- processing | complete | failed
    summary     TEXT,
    issues      JSONB,
    fixes       JSONB,
    error       TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
