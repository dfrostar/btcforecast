-- Initialize BTC Forecast Database Schema
-- This script creates all necessary tables for the application

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'free',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    api_key VARCHAR(255) UNIQUE,
    subscription_expires TIMESTAMP WITH TIME ZONE,
    stripe_customer_id VARCHAR(255),
    CONSTRAINT valid_role CHECK (role IN ('free', 'premium', 'professional', 'enterprise', 'admin'))
);

-- Create subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    tier_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_tier CHECK (tier_name IN ('premium', 'professional', 'enterprise')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'canceled', 'past_due', 'unpaid', 'trialing'))
);

-- Create usage tracking table
CREATE TABLE IF NOT EXISTS usage_tracking (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    api_calls INTEGER DEFAULT 0,
    predictions INTEGER DEFAULT 0,
    portfolios_count INTEGER DEFAULT 0,
    storage_used_mb REAL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

-- Create billing history table
CREATE TABLE IF NOT EXISTS billing_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stripe_invoice_id VARCHAR(255) UNIQUE,
    amount REAL NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(20) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_currency CHECK (currency IN ('USD', 'EUR', 'GBP')),
    CONSTRAINT valid_billing_status CHECK (status IN ('paid', 'open', 'void', 'uncollectible'))
);

-- Create API audit log table
CREATE TABLE IF NOT EXISTS api_audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    request_data JSONB,
    response_status INTEGER,
    response_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_method CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')),
    CONSTRAINT valid_status_code CHECK (response_status >= 100 AND response_status < 600)
);

-- Create predictions log table
CREATE TABLE IF NOT EXISTS predictions_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    prediction_type VARCHAR(50) NOT NULL,
    input_data JSONB,
    prediction_result JSONB,
    confidence_score REAL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- Create model training history table
CREATE TABLE IF NOT EXISTS model_training_history (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    training_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    r2_score REAL,
    mae_score REAL,
    rmse_score REAL,
    training_time_seconds REAL,
    model_size_kb INTEGER,
    features_used JSONB,
    hyperparameters JSONB,
    CONSTRAINT valid_scores CHECK (r2_score >= -1 AND r2_score <= 1 AND mae_score >= 0 AND rmse_score >= 0)
);

-- Create system metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    cpu_usage REAL,
    memory_usage REAL,
    disk_usage REAL,
    active_connections INTEGER,
    requests_per_minute REAL,
    CONSTRAINT valid_usage CHECK (cpu_usage >= 0 AND cpu_usage <= 100 AND memory_usage >= 0 AND memory_usage <= 100 AND disk_usage >= 0 AND disk_usage <= 100)
);

-- Create rate limiting data table
CREATE TABLE IF NOT EXISTS rate_limit_data (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    requests_count INTEGER DEFAULT 0,
    window_start TIMESTAMP WITH TIME ZONE,
    window_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_role_limit CHECK (role IN ('free', 'premium', 'professional', 'enterprise', 'admin'))
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_id ON subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_date ON usage_tracking(user_id, date);
CREATE INDEX IF NOT EXISTS idx_api_audit_user_timestamp ON api_audit_log(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_api_audit_timestamp ON api_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_predictions_user_timestamp ON predictions_log(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_rate_limit_identifier ON rate_limit_data(identifier);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for subscriptions table
CREATE TRIGGER update_subscriptions_updated_at 
    BEFORE UPDATE ON subscriptions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, hashed_password, role, is_active) 
VALUES ('admin', 'admin@btcforecast.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK8.', 'admin', true)
ON CONFLICT (username) DO NOTHING;

-- Insert demo user (password: demo123)
INSERT INTO users (username, email, hashed_password, role, is_active) 
VALUES ('demo', 'demo@btcforecast.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK8.', 'premium', true)
ON CONFLICT (username) DO NOTHING; 