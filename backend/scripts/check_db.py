import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.db.session import SessionLocal
from app.db.models import Transaction

def check_txs():
    db = SessionLocal()
    try:
        txs = db.query(Transaction).order_by(Transaction.id.desc()).limit(5).all()
        for tx in txs:
            print(f"ID: {tx.id}, Amt: {tx.amount}, Risk: {tx.final_risk_score}, Anom: {tx.anomaly_score}")
    finally:
        db.close()

if __name__ == "__main__":
    check_txs()
