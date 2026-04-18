# FinGuard AI - Bank-Grade Startup Guide

## 🏦 System Overview

FinGuard AI is now a **bank-grade fraud detection system** with:
- ✅ Multi-user RBAC (Customer, Analyst, Admin, Auditor)
- ✅ Persistent user behavioral profiles with online learning
- ✅ Real-time ML scoring (Autoencoder + Isolation Forest + GNN)
- ✅ Complete audit trail for regulatory compliance
- ✅ Real-time WebSocket broadcasting
- ✅ Merchant and device tracking

## 🚀 Quick Start

### Prerequisites

1. **Python 3.9+** installed
2. **PostgreSQL** installed and running
3. **Node.js** (for frontend)

### Step 1: Setup Database

```powershell
# Create PostgreSQL database
createdb finguard

# Or using psql
psql -U postgres -c "CREATE DATABASE finguard;"
```

### Step 2: Start Backend

```powershell
# Navigate to backend directory
cd FinGuard-Financial-Fraud-Detection-main\backend

# Run startup script (automated)
.\start_backend.ps1

# OR manually:
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Run from the 'backend' directory so it can find the 'app' module
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (Swagger UI)
- **WebSocket**: ws://localhost:8000/ws/transactions

### Step 3: Start Frontend

```powershell
# Navigate to frontend directory
cd FinGuard-Financial-Fraud-Detection-main\frontend

# Install dependencies
npm install

# Start development server
npm start
```

Frontend will be available at: http://localhost:3000

## 👥 User Roles & Access

### 1. Customer
- Submit transactions
- View own transaction history
- **Default role for new users**

### 2. Analyst (Fraud Analyst)
- View all flagged/blocked transactions
- Review and override decisions
- Access to transaction explanations
- Cannot modify system configuration

### 3. Admin
- Full access to all transactions
- System configuration (thresholds, models)
- User management
- Dashboard and metrics
- Read-only audit trail access

### 4. Auditor
- Read-only access to all transactions
- Full audit trail access
- Compliance reporting
- Cannot modify any data

## 📊 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token

### Transactions
- `POST /transactions/` - Submit transaction (scores automatically)
- `GET /transactions/all` - Get all transactions (analyst/admin)
- `GET /transactions/flagged` - Get flagged transactions (analyst/admin)
- `GET /transactions/{id}` - Get specific transaction

### Explainability
- `GET /explainability/transaction/{id}` - Get explanation (admin only)

## 🧪 Testing the System

### 1. Register Users

```bash
# Register a customer
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@test.com",
    "password": "password123",
    "role": "customer"
  }'

# Register an analyst
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "analyst@test.com",
    "password": "password123",
    "role": "analyst"
  }'

# Register an admin
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "password123",
    "role": "admin"
  }'
```

### 2. Login and Get Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@test.com",
    "password": "password123"
  }'

# Save the access_token from response
```

### 3. Submit Test Transaction

```bash
# Normal transaction (should be APPROVED)
curl -X POST http://localhost:8000/transactions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "user_id": 1,
    "merchant": "Amazon",
    "amount": 49.99,
    "device_id": "device_123",
    "ip_address": "192.168.1.1",
    "location": "New York, NY"
  }'

# Suspicious transaction (should be FLAGGED or BLOCKED)
curl -X POST http://localhost:8000/transactions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "user_id": 1,
    "merchant": "Unknown Merchant",
    "amount": 5000.00,
    "device_id": "new_device_999",
    "ip_address": "1.2.3.4",
    "location": "Unknown Location"
  }'
```

## 🔍 What Happens When a Transaction is Submitted?

1. **Merchant/Device Tracking**: System creates or updates merchant and device records
2. **User Profile Retrieval**: Gets user's behavioral baseline (avg spending, patterns)
3. **ML Scoring**:
   - Autoencoder calculates reconstruction error
   - Isolation Forest detects anomalies
   - GNN analyzes graph relationships
   - Weighted fusion: `0.3*AE + 0.3*IF + 0.4*GNN`
4. **Rule-Based Checks**:
   - Amount Z-score > 5
   - Amount > 10x average
   - Night transaction (unusual for user)
   - Location mismatch
   - High velocity (>5 tx/hour)
5. **Decision Logic**:
   - `risk_score < 0.3` → **APPROVED**
   - `0.3 ≤ risk_score < 0.7` OR warning flags → **FLAGGED**
   - `risk_score ≥ 0.7` OR critical flags → **BLOCKED**
6. **Audit Logging**: Every decision is logged with full traceability
7. **Profile Update**: User's baseline is updated incrementally (Welford's algorithm)
8. **WebSocket Broadcast**: Flagged/blocked transactions are pushed to analysts in real-time

## 📈 Database Schema

### Core Tables
- **users**: User accounts with RBAC
- **user_behavior_profiles**: Persistent behavioral baselines
- **merchants**: Merchant reputation tracking
- **devices**: User device tracking
- **accounts**: User account linking
- **transactions**: Enhanced with ML scores and decisions
- **audit_logs**: Full compliance trail

## 🔧 Configuration

Edit `backend/app/ml/model_registry.py`:

```python
# Risk thresholds
RISK_THRESHOLDS = {
    "approved_max": 0.3,    # Lower = stricter
    "flagged_max": 0.7,
}

# Fusion weights
FUSION_WEIGHTS = {
    "autoencoder": 0.3,
    "isolation_forest": 0.3,
    "gnn": 0.4
}

# Rule thresholds
RULE_THRESHOLDS = {
    "amount_z_score_max": 5.0,
    "amount_ratio_max": 10.0,
}
```

## 🐛 Troubleshooting

### Database Connection Error
```
Error: Could not connect to database
```
**Solution**: Make sure PostgreSQL is running and database exists:
```powershell
# Check if PostgreSQL is running
Get-Service postgresql*

# Create database
createdb finguard
```

### Import Errors
```
ModuleNotFoundError: No module named 'torch'
```
**Solution**: Install dependencies:
```powershell
pip install -r requirements.txt
```

### Port Already in Use
```
Error: [Errno 48] Address already in use
```
**Solution**: Kill process on port 8000:
```powershell
# Find process
netstat -ano | findstr :8000

# Kill it
taskkill /PID <PID> /F
```

## 📞 Support

For issues or questions about the bank-grade implementation, check:
1. Backend logs for ML scoring errors
2. Database connection status
3. Swagger docs at http://localhost:8000/docs

## 🎯 Next Steps

1. **Load Pre-trained Models**: Place trained models in `backend/models/`
2. **Configure Thresholds**: Adjust risk thresholds based on your use case
3. **Add Celery Workers**: For production-grade async processing
4. **Setup Redis**: For caching and real-time features
5. **Deploy**: Use Docker for containerized deployment

---

**Built with bank-grade requirements:**
- Multi-user concurrent access ✓
- Persistent behavioral profiles ✓
- Real-time scoring and streaming ✓
- Complete audit trail ✓
- Regulatory compliance ready ✓
