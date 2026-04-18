-- FinGuard AI 2.0 - Immutable Audit & Calibration Schema
-- Compliance: FCA PS21/4, RBI Master Directions 2023, PMLA

-- 1. Create the Immutable Audit Table
CREATE TABLE IF NOT EXISTS sovereign_audit_log (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Evidence Pack (Lossy JSONB)
    evidence_pack JSONB NOT NULL,
    
    -- Reproducibility & Lineage (FCA PS21/4)
    model_version VARCHAR(50) NOT NULL,
    ae_model_sha256 VARCHAR(64),
    gnn_model_sha256 VARCHAR(64),
    prompt_sha256 VARCHAR(64) NOT NULL, -- Lineage of the narrative generation prompt
    
    -- Calibrated Probabilities
    raw_anomaly_score FLOAT,
    raw_gnn_score FLOAT,
    calibrated_risk_probability FLOAT, -- Post Platt Scaling / Isotonic Regression
    expected_calibration_error FLOAT DEFAULT 0.05,
    
    -- Validation Results
    validation_gate_meta JSONB, -- Stores the results of the 8-Check Gate
    
    -- Metadata
    correlation_id UUID DEFAULT gen_random_uuid()
);

-- 2. Performance Indexes
CREATE INDEX idx_audit_tx_id ON sovereign_audit_log(transaction_id);
CREATE INDEX idx_audit_timestamp ON sovereign_audit_log(timestamp);

-- 3. ENFORCE IMMUTABILITY (Zero-Trust Architectural Boundary)
-- Revoke update and delete to ensure the audit trail remains sovereign and tamper-proof.

-- Define specific role for the app but limit permissions
-- DO NOT TOUCH existing tables, only new audit orchestration layer.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'finguard_app') THEN
        CREATE ROLE finguard_app;
    END IF;
END
$$;

GRANT INSERT, SELECT ON sovereign_audit_log TO finguard_app;
REVOKE UPDATE, DELETE ON sovereign_audit_log FROM finguard_app;

-- 4. Trigger-based immutability as a second layer of defense
CREATE OR REPLACE FUNCTION prevent_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit Log is Immutable. UPDATE/DELETE operations are strictly prohibited for regulatory compliance.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_audit_update
BEFORE UPDATE ON sovereign_audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_tampering();

CREATE TRIGGER trg_prevent_audit_delete
BEFORE DELETE ON sovereign_audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_tampering();

COMMENT ON TABLE sovereign_audit_log IS 'Immutable audit trail for FinGuard AI 2.0. Required for regulatory compliance and dispute resolution.';
