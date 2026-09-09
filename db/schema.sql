-- BetShield database schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS accounts (
    account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type VARCHAR(30) NOT NULL,  -- 'normal_player', 'bettor', 'bot', 'mule'
    kyc_level VARCHAR(20) DEFAULT 'full',
    created_at TIMESTAMP DEFAULT now(),
    risk_score FLOAT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS merchants (
    merchant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_name TEXT NOT NULL,
    mcc_code VARCHAR(10),
    payment_gateway_id VARCHAR(50),
    is_blacklisted BOOLEAN DEFAULT FALSE,
    app_package_name TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_account UUID REFERENCES accounts(account_id),
    receiver_account UUID REFERENCES accounts(account_id),
    merchant_id UUID REFERENCES merchants(merchant_id),
    amount DECIMAL(12,2) NOT NULL,
    tick INT NOT NULL,
    timestamp TIMESTAMP,
    device_id VARCHAR(50),
    ip_address VARCHAR(45),
    channel VARCHAR(20) DEFAULT 'GameCoin'
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    txn_id UUID REFERENCES transactions(txn_id),
    alert_type VARCHAR(30),  -- 'betting', 'bot', 'aml'
    risk_score FLOAT,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_txn_sender ON transactions(sender_account);
CREATE INDEX IF NOT EXISTS idx_txn_receiver ON transactions(receiver_account);
CREATE INDEX IF NOT EXISTS idx_txn_tick ON transactions(tick);
