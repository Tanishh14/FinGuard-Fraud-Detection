from app.db.session import SessionLocal
from app.db.models import Transaction

db = SessionLocal()
txs = db.query(Transaction).filter(Transaction.status == 'REVIEW').limit(10).all()
for tx in txs:
    gate_status = None
    for label in tx.intelligence.get("labels", []):
        if "GATE" in label:
            gate_status = label
            break
    exp = tx.explanation.encode('ascii', 'ignore').decode('ascii') if tx.explanation else ''
    print(f"Amt: {tx.amount}, FRS: {tx.final_risk_score}, Gate: {gate_status}, Explanation: {exp}")
