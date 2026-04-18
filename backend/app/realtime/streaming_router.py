"""Server-Sent Events (SSE) streaming router for real-time updates."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import AsyncGenerator
import asyncio
import json
from datetime import datetime

from app.core.dependencies import get_db, require_analyst_or_admin
from app.db.models import Transaction
from app.auth.models import User

router = APIRouter()


async def transaction_stream(
    db: Session,
    request: Request,
    min_risk_score: float = 0.0
) -> AsyncGenerator[str, None]:
    """
    Stream transactions as Server-Sent Events.
    
    Args:
        db: Database session
        request: FastAPI request (to detect client disconnect)
        min_risk_score: Minimum risk score to stream
        
    Yields:
        SSE formatted transaction data
    """
    last_id = 0
    
    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            # Query new transactions since last check
            new_txs = db.query(Transaction).filter(
                Transaction.id > last_id,
                Transaction.final_risk_score >= min_risk_score
            ).order_by(Transaction.id).limit(10).all()
            
            for tx in new_txs:
                data = {
                    "id": tx.id,
                    "user_id": tx.user_id,
                    "amount": tx.amount,
                    "merchant": tx.merchant.merchant_name if tx.merchant else "Unknown",
                    "final_risk_score": round(tx.final_risk_score, 4),
                    "decision": tx.decision,
                    "timestamp": tx.timestamp.isoformat()
                }
                
                # SSE format: data: {json}\n\n
                yield f"data: {json.dumps(data)}\n\n"
                last_id = max(last_id, tx.id)
            
            # Sleep before next check
            await asyncio.sleep(1.0)
            
    except asyncio.CancelledError:
        # Client disconnected
        pass


async def alert_stream(
    db: Session,
    request: Request
) -> AsyncGenerator[str, None]:
    """
    Stream fraud alerts (flagged/blocked transactions).
    
    Yields:
        SSE formatted fraud alerts
    """
    last_id = 0
    
    try:
        while True:
            if await request.is_disconnected():
                break
            
            # Query new flagged/blocked transactions
            new_alerts = db.query(Transaction).filter(
                Transaction.id > last_id,
                Transaction.decision.in_(["FLAGGED", "BLOCKED"])
            ).order_by(Transaction.id).limit(10).all()
            
            for tx in new_alerts:
                alert = {
                    "type": "fraud_alert",
                    "severity": "high" if tx.decision == "BLOCKED" else "medium",
                    "transaction_id": tx.id,
                    "user_id": tx.user_id,
                    "amount": tx.amount,
                    "risk_score": round(tx.final_risk_score, 4),
                    "decision": tx.decision,
                    "explanation": tx.explanation,
                    "timestamp": tx.timestamp.isoformat()
                }
                
                yield f"data: {json.dumps(alert)}\n\n"
                last_id = max(last_id, tx.id)
            
            await asyncio.sleep(2.0)
            
    except asyncio.CancelledError:
        pass


async def metrics_stream(
    db: Session,
    request: Request
) -> AsyncGenerator[str, None]:
    """
    Stream system metrics.
    
    Yields:
        SSE formatted metrics updates
    """
    try:
        while True:
            if await request.is_disconnected():
                break
            
            # Calculate metrics
            from sqlalchemy import func
            from datetime import timedelta
            
            now = datetime.utcnow()
            last_hour = now - timedelta(hours=1)
            
            total_txs = db.query(func.count(Transaction.id)).filter(
                Transaction.timestamp >= last_hour
            ).scalar()
            
            flagged = db.query(func.count(Transaction.id)).filter(
                Transaction.timestamp >= last_hour,
                Transaction.decision == "FLAGGED"
            ).scalar()
            
            blocked = db.query(func.count(Transaction.id)).filter(
                Transaction.timestamp >= last_hour,
                Transaction.decision == "BLOCKED"
            ).scalar()
            
            avg_risk = db.query(func.avg(Transaction.final_risk_score)).filter(
                Transaction.timestamp >= last_hour
            ).scalar()
            
            metrics = {
                "timestamp": now.isoformat(),
                "transactions_last_hour": total_txs or 0,
                "flagged_last_hour": flagged or 0,
                "blocked_last_hour": blocked or 0,
                "avg_risk_score": round(float(avg_risk), 4) if avg_risk else 0.0,
                "fraud_rate": round((flagged + blocked) / total_txs, 4) if total_txs else 0.0
            }
            
            yield f"data: {json.dumps(metrics)}\n\n"
            
            await asyncio.sleep(5.0)  # Update every 5 seconds
            
    except asyncio.CancelledError:
        pass


@router.get("/transactions")
async def stream_transactions(
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin),
    min_risk_score: float = 0.0
):
    """
    Stream new transactions via Server-Sent Events.
    
    Clients can listen to this endpoint for real-time transaction updates.
    
    Args:
        request: FastAPI request
        db: Database session
        analyst: Authenticated analyst/admin
        min_risk_score: Filter transactions by minimum risk score
        
    Returns:
        StreamingResponse with SSE content
    """
    return StreamingResponse(
        transaction_stream(db, request, min_risk_score),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/alerts")
async def stream_alerts(
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin)
):
    """
    Stream fraud alerts (flagged/blocked transactions) via SSE.
    
    Provides real-time notifications for fraud analysts.
    
    Args:
        request: FastAPI request
        db: Database session
        analyst: Authenticated analyst/admin
        
    Returns:
        StreamingResponse with fraud alert events
    """
    return StreamingResponse(
        alert_stream(db, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/metrics")
async def stream_metrics(
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin)
):
    """
    Stream system metrics via SSE.
    
    Provides real-time dashboard metrics for monitoring.
    
    Args:
        request: FastAPI request
        db: Database session
        analyst: Authenticated analyst/admin
        
    Returns:
        StreamingResponse with metrics updates
    """
    return StreamingResponse(
        metrics_stream(db, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
