from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import Transaction, User
from app.schemas.api import TransactionIn, TransactionOut, AppealRequest, OTPVerifyRequest
from app.core.dependencies import get_current_user, require_admin
from app.transactions.service import TransactionService

router = APIRouter(tags=["Transactions"])

def get_tx_service(db: Session = Depends(get_db)) -> TransactionService:
    return TransactionService(db)

@router.post("/", response_model=TransactionOut)
async def ingest_transaction(
    payload: TransactionIn,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_tx_service)
):
    return await service.process_transaction(payload.model_dump(), user)

@router.get("/all", response_model=List[TransactionOut])
def get_all_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=10, le=1000),
    filters: dict = Depends(lambda username=None, merchant=None, min_amount=None, max_amount=None, risk_level=None: 
                            {k: v for k, v in locals().items() if v is not None}),
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_tx_service)
):
    return service.get_all_transactions(user, filters, page, page_size)

@router.get("/count")
def get_transaction_count(
    filters: dict = Depends(lambda username=None, merchant=None, min_amount=None, max_amount=None, risk_level=None: 
                            {k: v for k, v in locals().items() if v is not None}),
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_tx_service)
):
    count = service.get_transaction_count(user, filters)
    return {"total": count, "user_role": user.role}

@router.post("/{tx_id}/approve", response_model=TransactionOut)
async def approve_transaction(
    tx_id: int,
    user: User = Depends(require_admin),
    service: TransactionService = Depends(get_tx_service)
):
    return await service.override_transaction(tx_id, "APPROVED", user.id)

@router.post("/{tx_id}/block", response_model=TransactionOut)
async def block_transaction(
    tx_id: int,
    user: User = Depends(require_admin),
    service: TransactionService = Depends(get_tx_service)
):
    return await service.override_transaction(tx_id, "BLOCKED", user.id)

@router.post("/{tx_id}/verify", response_model=TransactionOut)
def verify_transaction(
    tx_id: int,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_tx_service)
):
    return service.verify_transaction_mfa(tx_id, user.id)

@router.post("/{tx_id}/appeal")
def appeal_transaction(
    tx_id: int,
    payload: AppealRequest,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_tx_service)
):
    return service.initiate_otp_flow(tx_id, user, "appeal", payload.reason, payload.urgency)

@router.post("/{tx_id}/report")
def report_transaction(
    tx_id: int,
    payload: AppealRequest,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_tx_service)
):
    return service.initiate_otp_flow(tx_id, user, "report", payload.reason, payload.urgency)

@router.post("/verify-report-appeal-otp", response_model=TransactionOut)
async def verify_report_appeal_otp(
    payload: OTPVerifyRequest,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_tx_service)
):
    return await service.verify_and_finalize_otp(user.email, payload.otp_code, payload.otp_type)
