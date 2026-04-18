"""
FinGuard Audit & Compliance Module
===================================
Provides full audit trail for regulatory compliance.
Every transaction decision is logged with:
- Input features snapshot
- All model scores
- Decision explanation
- Analyst actions (if reviewed)
"""
from app.audit.service import AuditService

__all__ = ["AuditService"]

