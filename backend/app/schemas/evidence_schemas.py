from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class FactBlock(BaseModel):
    """
    Determinism requirement: Sentences generation constrained by rules and verifiable metrics.
    """
    rule_id: str = Field(..., description="The internal identifier of the triggered rule (e.g., VEL-001)")
    description: str = Field(..., description="Factual representation, e.g., '23 transactions in 6h'")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Model confidence level")
    
class MotifBlock(BaseModel):
    """
    GNN Motif information, structurally representing fraud rings without revealing endpoints.
    """
    motif_type: str = Field(..., description="E.g., 'Circular Transaction Ring'")
    node_count: int = Field(..., description="Number of anonymous nodes involved")
    edge_weight_sum: float = Field(..., description="Total aggregated value traversed in ring")

class EvidenceBlock(BaseModel):
    """
    Aggregates individual facts and motifs into a cohesive array of evidence.
    """
    facts: List[FactBlock]
    motifs: Optional[List[MotifBlock]] = []
    
    @field_validator("facts")
    def at_least_one_fact(cls, v):
        if not v:
            raise ValueError("EvidenceBlock must contain at least one verifiable fact.")
        return v

class LossyEvidencePack(BaseModel):
    """
    A one-way, lossy transformation module.
    It strips all PII and generates an Anonymized Evidence Pack.
    The narrative layer receives ZERO access to raw data.
    """
    transaction_reference_hash: str = Field(..., description="SHA-256 hash representation of transaction ID")
    synthetic_identity_id: str = Field(..., description="Resolved graph node ID, devoid of PII")
    evidence: EvidenceBlock
    overall_anomaly_score: float = Field(..., description="Combined ML anomaly score")
    
    # Deterministic generation target
    temperature: float = Field(0.2, frozen=True, description="Enforced temperature for LLM deterministic explanation")
