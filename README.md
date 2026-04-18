# FinGuard AI - Bank-Grade Fraud Detection System

FinGuard AI is a state-of-the-art financial fraud detection platform designed to meet production bank-grade standards. It utilizes a multi-model ML architecture, real-time behavioral profiling, and a robust rule engine to detect anomalies and fraudulent patterns with high precision.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python**: 3.10+
- **Node.js**: 18+
- **Database**: SQLite (default for development) or PostgreSQL

### 2. Backend Setup (ML & API)
```bash
# Navigate to backend directory (CRITICAL: Do not go into backend/app)
cd backend

# Install dependencies
pip install -r requirements.txt

# Start the server (Must be run from the 'backend' directory)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 3. Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start Dev Server (Port 5173/5174)
npm run dev
```

---

## 🧠 Machine Learning Architecture

FinGuard uses a **Weighted Fusion Engine** (0.3 AE + 0.3 IF + 0.4 GNN) combined with a **Heuristic Override Layer**.

### 1. Model Breakdown
- **Autoencoder (AE)**: Neural-based reconstruction error detection for behavioral anomalies.
- **Isolation Forest (IF)**: Tree-based anomaly detection for outlier isolation.
- **Graph Neural Network (GNN)**: Analyzes user-merchant-device relationships to identify fraud rings.

### 2. Heuristic Override (Bank-Grade Safety)
Critical rules override ML scores to ensure 100% protection against extreme anomalies:
- **₹1 Crore+ Rule**: Any transaction > ₹10,000,000 is blocked immediately.
- **Extreme Jump Rule**: Transactions > 10x user's average are blocked.
- **Velocity Rule**: High frequency (>10 tx/hr) triggers a security flag.

---

## 💬 Explainability Engine

FinGuard doesn't just block; it explains. The engine analyzes the delta between the transaction and the user's **Behavioral Profile**:
- **Baseline Comparison**: Matches amount against user average (e.g., "Transaction is 500x higher than typical").
- **Flag Descriptions**: Provides clear reasons like "Unusual Night Transaction" or "New Device Anomaly".
- **Risk Confidence**: Displays a weighted percentage of how certain the system is about the risk.

---

## 🧪 Testing Fraud Scenarios

| Scenario | Input | Expected Result |
| :--- | :--- | :--- |
| **Normal** | ₹500 to Local Shop | **APPROVED** (Low Score) |
| **Suspicious** | ₹20,000 at 2 AM | **FLAGGED** (Review Required) |
| **Extreme** | ₹6,000,000,000 | **BLOCKED** (100% Risk) |

---

## 👥 User Roles
- **Customer**: Initiate secure payments.
- **Fraud Analyst**: Review flagged items and investigate explanations.
- **Admin**: Configure ML thresholds and manage system health.