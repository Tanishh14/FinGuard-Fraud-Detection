"""GNN (Graph Neural Network) router for fraud ring detection and network analysis."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, select, or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from functools import lru_cache
import time
import hashlib
import json

from app.db.session import get_db
from app.db.models import Transaction, User, MerchantProfile, UserDevice
from app.core.dependencies import require_analyst_or_admin

router = APIRouter(tags=["GNN"])

# PERFORMANCE: Simple in-memory cache
_graph_cache: Dict[str, tuple] = {}  # {cache_key: (data, timestamp)}


@router.get("/fraud-rings")
async def get_fraud_rings(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    min_ring_size: int = Query(3, ge=2, le=50, description="Minimum ring size to detect"),
    risk_threshold: float = Query(0.6, ge=0.0, le=1.0, description="Minimum risk score"),
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin)
):
    """
    Detect fraud rings using graph analysis of user-merchant-device relationships.
    
    A fraud ring is a group of users who:
    - Share merchants or devices
    - Have high average risk scores
    - Transact within a time period
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get high-risk transactions in the time period
    high_risk_txs = db.query(Transaction).filter(
        and_(
            Transaction.timestamp >= cutoff_date,
            Transaction.final_risk_score >= risk_threshold
        )
    ).all()
    
    # Build graph: find users who share merchants or devices
    user_connections: Dict[int, set] = {}
    
    for tx in high_risk_txs:
        if tx.user_id not in user_connections:
            user_connections[tx.user_id] = set()
        
        # Find other users who used same merchant or device
        related_txs = db.query(Transaction).filter(
            and_(
                Transaction.timestamp >= cutoff_date,
                Transaction.user_id != tx.user_id,
                ((Transaction.merchant == tx.merchant) | 
                 (Transaction.device_id == tx.device_id))
            )
        ).all()
        
        for related_tx in related_txs:
            if related_tx.final_risk_score >= risk_threshold:
                user_connections[tx.user_id].add(related_tx.user_id)
    
    # Detect connected components (fraud rings) using DFS
    visited = set()
    fraud_rings = []
    ring_id = 1
    
    def dfs(user_id: int, component: set):
        """Depth-first search to find connected components."""
        visited.add(user_id)
        component.add(user_id)
        
        if user_id in user_connections:
            for neighbor in user_connections[user_id]:
                if neighbor not in visited:
                    dfs(neighbor, component)
    
    # Find all connected components
    for user_id in user_connections.keys():
        if user_id not in visited:
            component = set()
            dfs(user_id, component)
            
            if len(component) >= min_ring_size:
                # Calculate ring statistics
                ring_users = list(component)
                ring_txs = db.query(Transaction).filter(
                    and_(
                        Transaction.user_id.in_(ring_users),
                        Transaction.timestamp >= cutoff_date
                    )
                ).all()
                
                avg_risk = sum(tx.final_risk_score for tx in ring_txs) / len(ring_txs)
                
                # Get member emails
                members = db.query(User).filter(User.id.in_(ring_users)).all()
                member_emails = [u.email for u in members]
                
                fraud_rings.append({
                    "ring_id": ring_id,
                    "size": len(component),
                    "members": member_emails,
                    "member_count": len(member_emails),
                    "avg_risk_score": round(avg_risk, 3),
                    "transaction_count": len(ring_txs)
                })
                ring_id += 1
    
    # Sort by avg_risk_score descending
    fraud_rings.sort(key=lambda x: x["avg_risk_score"], reverse=True)
    
    return fraud_rings


@router.get("/user-connections/{user_id}")
async def get_user_connections(
    user_id: int,
    days: int = Query(90, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin)
):
    """
    Get a specific user's network connections: merchants, devices, and linked users.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get user info
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}
    
    # Get user's transactions
    user_txs = db.query(Transaction).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.timestamp >= cutoff_date
        )
    ).all()
    
    # Analyze merchants
    merchant_stats = {}
    for tx in user_txs:
        if tx.merchant not in merchant_stats:
            merchant_stats[tx.merchant] = {
                "merchant_name": tx.merchant,
                "transaction_count": 0,
                "total_amount": 0.0,
                "risk_scores": []
            }
        merchant_stats[tx.merchant]["transaction_count"] += 1
        merchant_stats[tx.merchant]["total_amount"] += tx.amount
        merchant_stats[tx.merchant]["risk_scores"].append(tx.final_risk_score)
    
    merchants = [
        {
            "merchant_name": m["merchant_name"],
            "transaction_count": m["transaction_count"],
            "total_amount": round(m["total_amount"], 2),
            "avg_risk_score": round(sum(m["risk_scores"]) / len(m["risk_scores"]), 3)
        }
        for m in merchant_stats.values()
    ]
    
    # Analyze devices
    device_stats = {}
    for tx in user_txs:
        if tx.device_id and tx.device_id not in device_stats:
            device_stats[tx.device_id] = {
                "device_id": tx.device_id,
                "transaction_count": 0,
                "risk_scores": []
            }
        if tx.device_id:
            device_stats[tx.device_id]["transaction_count"] += 1
            device_stats[tx.device_id]["risk_scores"].append(tx.final_risk_score)
    
    devices = [
        {
            "device_id": d["device_id"],
            "transaction_count": d["transaction_count"],
            "avg_risk_score": round(sum(d["risk_scores"]) / len(d["risk_scores"]), 3)
        }
        for d in device_stats.values()
    ]
    
    # Find linked users (who share merchants or devices)
    linked_user_ids = set()
    for tx in user_txs:
        related_txs = db.query(Transaction).filter(
            and_(
                Transaction.timestamp >= cutoff_date,
                Transaction.user_id != user_id,
                ((Transaction.merchant == tx.merchant) | 
                 (Transaction.device_id == tx.device_id))
            )
        ).distinct(Transaction.user_id).all()
        
        for related_tx in related_txs:
            linked_user_ids.add(related_tx.user_id)
    
    linked_users = []
    if linked_user_ids:
        linked_user_objs = db.query(User).filter(User.id.in_(linked_user_ids)).all()
        linked_users = [
            {"user_id": u.id, "email": u.email}
            for u in linked_user_objs
        ]
    
    # Calculate statistics
    flagged_count = sum(1 for tx in user_txs if tx.status == "FLAGGED")
    avg_risk = sum(tx.final_risk_score for tx in user_txs) / len(user_txs) if user_txs else 0.0
    
    return {
        "user_id": user_id,
        "email": user.email,
        "merchants": merchants,
        "devices": devices,
        "linked_users": linked_users,
        "stats": {
            "total_transactions": len(user_txs),
            "avg_risk_score": round(avg_risk, 3),
            "flagged_count": flagged_count,
            "period_days": days
        }
    }


@router.get("/risk-propagation")
async def get_risk_propagation(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin)
):
    """
    Analyze how risk propagates through the network via merchants and devices.
    Identifies high-risk hotspots (merchants/devices with many high-risk transactions).
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all transactions in period
    txs = db.query(Transaction).filter(
        Transaction.timestamp >= cutoff_date
    ).all()
    
    # Analyze merchant risk hotspots
    merchant_stats = {}
    for tx in txs:
        if tx.merchant not in merchant_stats:
            merchant_stats[tx.merchant] = {
                "name": tx.merchant,
                "transaction_count": 0,
                "risk_scores": [],
                "flagged_count": 0
            }
        merchant_stats[tx.merchant]["transaction_count"] += 1
        merchant_stats[tx.merchant]["risk_scores"].append(tx.final_risk_score)
        if tx.status in ["FLAGGED", "BLOCKED"]:
            merchant_stats[tx.merchant]["flagged_count"] += 1
    
    merchant_hotspots = [
        {
            "type": "merchant",
            "name": m["name"],
            "transaction_count": m["transaction_count"],
            "avg_risk_score": round(sum(m["risk_scores"]) / len(m["risk_scores"]), 3),
            "flagged_count": m["flagged_count"],
            "fraud_rate": round(m["flagged_count"] / m["transaction_count"], 3)
        }
        for m in merchant_stats.values()
        if m["transaction_count"] >= 5  # Only include merchants with >= 5 transactions
    ]
    
    # Analyze device risk hotspots
    device_stats = {}
    for tx in txs:
        if tx.device_id:
            if tx.device_id not in device_stats:
                device_stats[tx.device_id] = {
                    "name": tx.device_id,
                    "transaction_count": 0,
                    "risk_scores": [],
                    "flagged_count": 0
                }
            device_stats[tx.device_id]["transaction_count"] += 1
            device_stats[tx.device_id]["risk_scores"].append(tx.final_risk_score)
            if tx.status in ["FLAGGED", "BLOCKED"]:
                device_stats[tx.device_id]["flagged_count"] += 1
    
    device_hotspots = [
        {
            "type": "device",
            "name": d["name"],
            "transaction_count": d["transaction_count"],
            "avg_risk_score": round(sum(d["risk_scores"]) / len(d["risk_scores"]), 3),
            "flagged_count": d["flagged_count"],
            "fraud_rate": round(d["flagged_count"] / d["transaction_count"], 3)
        }
        for d in device_stats.values()
        if d["transaction_count"] >= 3  # Only include devices with >= 3 transactions
    ]
    
    # Sort by fraud_rate descending
    merchant_hotspots.sort(key=lambda x: x["fraud_rate"], reverse=True)
    device_hotspots.sort(key=lambda x: x["fraud_rate"], reverse=True)
    
    return {
        "merchant_hotspots": merchant_hotspots[:20],  # Top 20
        "device_hotspots": device_hotspots[:20],  # Top 20
        "analysis_period_days": days
    }
@router.get("/graph-data")
async def get_graph_data(
    days: int = Query(30, ge=1, le=365),
    max_nodes: int = Query(500, ge=50, le=2000, description="Maximum nodes to return"),
    risk_threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum risk to include"),
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin)
):
    """
    OPTIMIZED graph data endpoint with sub-500ms target.
    
    Performance features:
    - Column-only queries (no ORM overhead)
    - In-memory caching (60s TTL) 
    - Minimal payload (only essential fields)
    - Instrumented timing
    """
    start_time = time.time()
    
    # OPTIMIZATION 1: Check cache first
    cache_key = hashlib.md5(f"graph_{days}_{max_nodes}_{risk_threshold}".encode()).hexdigest()
    if cache_key in _graph_cache:
        cached_data, cached_time = _graph_cache[cache_key]
        if time.time() - cached_time < 60:  # 60s TTL
            cached_data["_cache_hit"] = True
            cached_data["_response_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return cached_data
    
    # OPTIMIZATION 2: Column-only query (avoid ORM object creation)
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    recent_cutoff = datetime.utcnow() - timedelta(days=min(7, days))
    
    query_start = time.time()
    
    # Use tuple query instead of ORM objects
    txs = db.query(
        Transaction.id,
        Transaction.user_id,
        Transaction.merchant,
        Transaction.merchant_id,
        Transaction.device_id,
        Transaction.amount,
        Transaction.final_risk_score,
        Transaction.status,
        Transaction.timestamp
    ).filter(
        and_(
            Transaction.timestamp >= cutoff_date,
            ((Transaction.final_risk_score >= risk_threshold) | 
             (Transaction.timestamp >= recent_cutoff))
        )
    ).limit(5000).all()
    
    query_time_ms = round((time.time() - query_start) * 1000, 2)
    
    # OPTIMIZATION 3: Fast aggregation with dict lookups (not ORM)
    process_start = time.time()
    
    user_stats = {}
    merchant_stats = {}
    device_stats = {}
    edge_agg = {}
    
    for tx_tuple in txs:
        tx_id, user_id, merchant, merchant_id, device_id, amount, risk, status, timestamp = tx_tuple
        
        # User stats
        if user_id not in user_stats:
            user_stats[user_id] = {
                "risk_sum": 0.0, "risk_count": 0,
                "merchants": set(), "devices": set(),
                "tx_count": 0, "total_amount": 0.0, "flagged": 0
            }
        s = user_stats[user_id]
        s["risk_sum"] += risk
        s["risk_count"] += 1
        s["merchants"].add(merchant)
        if device_id:
            s["devices"].add(device_id)
        s["tx_count"] += 1
        s["total_amount"] += amount
        if status in ["FLAGGED", "BLOCKED"]:
            s["flagged"] += 1
        
        # Merchant stats
        if merchant not in merchant_stats:
            merchant_stats[merchant] = {
                "amount_sum": 0.0, "amount_count": 0,
                "risk_sum": 0.0, "risk_count": 0,
                "users": set(), "tx_count": 0, "flagged": 0
            }
        m = merchant_stats[merchant]
        m["amount_sum"] += amount
        m["amount_count"] += 1
        m["risk_sum"] += risk
        m["risk_count"] += 1
        m["users"].add(user_id)
        m["tx_count"] += 1
        if status in ["FLAGGED", "BLOCKED"]:
            m["flagged"] += 1
        
        # Device stats
        if device_id:
            if device_id not in device_stats:
                device_stats[device_id] = {
                    "users": set(), "risk_sum": 0.0, "risk_count": 0,
                    "tx_count": 0, "flagged": 0
                }
            d = device_stats[device_id]
            d["users"].add(user_id)
            d["risk_sum"] += risk
            d["risk_count"] += 1
            d["tx_count"] += 1
            if status in ["FLAGGED", "BLOCKED"]:
                d["flagged"] += 1
        
        # Edge aggregation
        edge_key_m = (f"user_{user_id}", f"merchant_{merchant}")
        if edge_key_m not in edge_agg:
            edge_agg[edge_key_m] = {"count": 0, "amount_sum": 0.0, "risk_sum": 0.0}
        edge_agg[edge_key_m]["count"] += 1
        edge_agg[edge_key_m]["amount_sum"] += amount
        edge_agg[edge_key_m]["risk_sum"] += risk
        
        if device_id:
            edge_key_d = (f"user_{user_id}", f"device_{device_id}")
            if edge_key_d not in edge_agg:
                edge_agg[edge_key_d] = {"count": 0, "amount_sum": 0.0, "risk_sum": 0.0}
            edge_agg[edge_key_d]["count"] += 1
            edge_agg[edge_key_d]["amount_sum"] += amount
            edge_agg[edge_key_d]["risk_sum"] += risk
    
    # OPTIMIZATION 4: Build minimal nodes (only essential fields)
    total_risk = sum(s["risk_sum"] for s in user_stats.values())
    nodes = []
    
    # User nodes
    for user_id, s in user_stats.items():
        avg_risk = s["risk_sum"] / s["risk_count"] if s["risk_count"] > 0 else 0
        nodes.append({
            "id": f"user_{user_id}",
            "label": f"User_{user_id}",
            "type": "user",
            "val": avg_risk * 10 + 2,
            "risk_score": round(avg_risk * 100, 1),
            "merchant_count": len(s["merchants"]),
            "device_count": len(s["devices"]),
            "tx_count": s["tx_count"],
            "avg_amount": round(s["total_amount"] / s["tx_count"], 2) if s["tx_count"] > 0 else 0,
            "anomaly_rate": round((s["flagged"] / s["tx_count"] * 100), 1) if s["tx_count"] > 0 else 0
        })
    
    # Merchant nodes
    for merchant, m in merchant_stats.items():
        avg_risk = m["risk_sum"] / m["risk_count"] if m["risk_count"] > 0 else 0
        nodes.append({
            "id": f"merchant_{merchant}",
            "label": merchant,
            "type": "merchant",
            "val": 3,
            "avg_amount": round(m["amount_sum"] / m["amount_count"], 2) if m["amount_count"] > 0 else 0,
            "anomaly_rate": round((m["flagged"] / m["tx_count"] * 100), 1) if m["tx_count"] > 0 else 0,
            "user_count": len(m["users"]),
            "tx_count": m["tx_count"],
            "risk_score": round(avg_risk * 100, 1)
        })
    
    # Device nodes
    for device_id, d in device_stats.items():
        avg_risk = d["risk_sum"] / d["risk_count"] if d["risk_count"] > 0 else 0
        nodes.append({
            "id": f"device_{device_id}",
            "label": f"Device_{device_id[:8]}",
            "type": "device",
            "val": len(d["users"]) + 1,
            "user_count": len(d["users"]),
            "tx_count": d["tx_count"],
            "risk_score": round(avg_risk * 100, 1)
        })
    
    # OPTIMIZATION 5: Sort and limit
    nodes.sort(key=lambda x: x["risk_score"], reverse=True)
    if len(nodes) > max_nodes:
        nodes = nodes[:max_nodes]
        retained = {n["id"] for n in nodes}
    else:
        retained = None
    
    # OPTIMIZATION 6: Build minimal links
    links = []
    for (source, target), e in edge_agg.items():
        if retained and (source not in retained or target not in retained):
            continue
        links.append({
            "source": source,
            "target": target,
            "tx_count": e["count"],
            "avg_amount": round(e["amount_sum"] / e["count"], 2) if e["count"] > 0 else 0,
            "risk": round(e["risk_sum"] / e["count"], 4) if e["count"] > 0 else 0
        })
    
    process_time_ms = round((time.time() - process_start) * 1000, 2)
    total_time_ms = round((time.time() - start_time) * 1000, 2)
    
    result = {
        "nodes": nodes,
        "links": links,
        "stats": {
            "total_users": len(user_stats),
            "total_merchants": len(merchant_stats),
            "total_devices": len(device_stats),
            "total_transactions": len(txs),
            "nodes_rendered": len(nodes),
            "links_rendered": len(links),
            "period_days": days,
            "filtered": len(nodes) >= max_nodes
        },
        "_performance": {
            "query_ms": query_time_ms,
            "processing_ms": process_time_ms,
            "total_ms": total_time_ms,
            "cache_hit": False
        }
    }
    
    # OPTIMIZATION 7: Cache result
    _graph_cache[cache_key] = (result, time.time())
    
    # Cleanup old cache entries (keep last 10)
    if len(_graph_cache) > 10:
        oldest_key = min(_graph_cache.keys(), key=lambda k: _graph_cache[k][1])
        del _graph_cache[oldest_key]
    
    return result


@router.get("/graph-data/search")
async def search_graph_data(
    transaction_id: Optional[int] = Query(None, description="Search by transaction ID"),
    merchant_name: Optional[str] = Query(None, description="Search by merchant name (partial match)"),
    username: Optional[str] = Query(None, description="Search by username (partial match)"),
    max_nodes: int = Query(500, ge=50, le=2000, description="Maximum nodes to return"),
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin)
):
    """
    Search-based graph data endpoint. Only loads transactions matching the search criteria.
    At least one search parameter must be provided.
    
    Performance: Instead of loading ALL transactions, this only queries matching ones,
    making it dramatically faster for large datasets (10k+ transactions).
    """
    start_time = time.time()
    
    if not transaction_id and not merchant_name and not username:
        return {
            "nodes": [],
            "links": [],
            "stats": {
                "total_users": 0, "total_merchants": 0, "total_devices": 0,
                "total_transactions": 0, "nodes_rendered": 0, "links_rendered": 0,
                "search_mode": True
            },
            "message": "Please provide at least one search parameter (transaction_id, merchant_name, or username)"
        }
    
    query_start = time.time()
    
    # Build the base query - only select needed columns
    base_query = db.query(
        Transaction.id,
        Transaction.user_id,
        Transaction.merchant,
        Transaction.merchant_id,
        Transaction.device_id,
        Transaction.amount,
        Transaction.final_risk_score,
        Transaction.status,
        Transaction.timestamp
    )
    
    # Collect target user IDs and transaction IDs for filtering
    target_user_ids = set()
    target_tx_ids = set()
    target_merchants = set()
    
    # FAST PATH: If ONLY transaction_id is provided, return just that transaction's graph
    only_tx_id = transaction_id and not merchant_name and not username
    
    # Step 1: Identify matching transactions/users based on search criteria
    if transaction_id:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if tx:
            target_tx_ids.add(tx.id)
            if only_tx_id:
                # Strict mode: only this single transaction
                pass
            else:
                target_user_ids.add(tx.user_id)
                if tx.merchant:
                    target_merchants.add(tx.merchant)
    
    if username:
        matching_users = db.query(User).filter(
            User.username.ilike(f"%{username}%")
        ).limit(50).all()
        for u in matching_users:
            target_user_ids.add(u.id)
    
    if merchant_name:
        # Find transactions with matching merchant name
        matching_txs = db.query(Transaction.merchant).filter(
            Transaction.merchant.ilike(f"%{merchant_name}%")
        ).distinct().limit(50).all()
        for (m,) in matching_txs:
            target_merchants.add(m)
    
    # Step 2: Query transactions for the matched users and merchants
    if only_tx_id:
        # Strict: only the single transaction
        filters = [Transaction.id.in_(list(target_tx_ids))]
    elif username and not merchant_name and not transaction_id:
        # Focused Username Search: Get top 200 most recent/high-risk TXs for these users
        focused_tx_ids = db.query(Transaction.id).filter(
            Transaction.user_id.in_(list(target_user_ids))
        ).order_by(
            desc(Transaction.timestamp), 
            desc(Transaction.final_risk_score)
        ).limit(200).all()
        
        target_tx_ids = {tid for (tid,) in focused_tx_ids}
        filters = [Transaction.id.in_(list(target_tx_ids))]
    else:
        filters = []
        if target_user_ids:
            filters.append(Transaction.user_id.in_(list(target_user_ids)))
        if target_merchants:
            filters.append(Transaction.merchant.in_(list(target_merchants)))
        if target_tx_ids and not target_user_ids and not target_merchants:
            filters.append(Transaction.id.in_(list(target_tx_ids)))
    
    if not filters:
        return {
            "nodes": [], "links": [],
            "stats": {
                "total_users": 0, "total_merchants": 0, "total_devices": 0,
                "total_transactions": 0, "nodes_rendered": 0, "links_rendered": 0,
                "search_mode": True
            },
            "message": "No matching transactions found for the search criteria"
        }
    
    txs = base_query.filter(or_(*filters)).limit(5000).all()
    
    query_time_ms = round((time.time() - query_start) * 1000, 2)
    
    # Process data (same logic as /graph-data but with search context)
    process_start = time.time()
    
    user_stats = {}
    merchant_stats = {}
    device_stats = {}
    edge_agg = {}
    
    for tx_tuple in txs:
        tx_id, user_id, merchant, merchant_id, device_id, amount, risk, status, timestamp = tx_tuple
        
        # User stats
        if user_id not in user_stats:
            user_stats[user_id] = {
                "risk_sum": 0.0, "risk_count": 0,
                "merchants": set(), "devices": set(),
                "tx_count": 0, "total_amount": 0.0, "flagged": 0
            }
        s = user_stats[user_id]
        s["risk_sum"] += risk
        s["risk_count"] += 1
        s["merchants"].add(merchant)
        if device_id:
            s["devices"].add(device_id)
        s["tx_count"] += 1
        s["total_amount"] += amount
        if status in ["FLAGGED", "BLOCKED"]:
            s["flagged"] += 1
        
        # Merchant stats
        if merchant not in merchant_stats:
            merchant_stats[merchant] = {
                "amount_sum": 0.0, "amount_count": 0,
                "risk_sum": 0.0, "risk_count": 0,
                "users": set(), "tx_count": 0, "flagged": 0
            }
        m = merchant_stats[merchant]
        m["amount_sum"] += amount
        m["amount_count"] += 1
        m["risk_sum"] += risk
        m["risk_count"] += 1
        m["users"].add(user_id)
        m["tx_count"] += 1
        if status in ["FLAGGED", "BLOCKED"]:
            m["flagged"] += 1
        
        # Device stats
        if device_id:
            if device_id not in device_stats:
                device_stats[device_id] = {
                    "users": set(), "risk_sum": 0.0, "risk_count": 0,
                    "tx_count": 0, "flagged": 0
                }
            d = device_stats[device_id]
            d["users"].add(user_id)
            d["risk_sum"] += risk
            d["risk_count"] += 1
            d["tx_count"] += 1
            if status in ["FLAGGED", "BLOCKED"]:
                d["flagged"] += 1
        
        # Edge aggregation
        edge_key_m = (f"user_{user_id}", f"merchant_{merchant}")
        if edge_key_m not in edge_agg:
            edge_agg[edge_key_m] = {"count": 0, "amount_sum": 0.0, "risk_sum": 0.0}
        edge_agg[edge_key_m]["count"] += 1
        edge_agg[edge_key_m]["amount_sum"] += amount
        edge_agg[edge_key_m]["risk_sum"] += risk
        
        if device_id:
            edge_key_d = (f"user_{user_id}", f"device_{device_id}")
            if edge_key_d not in edge_agg:
                edge_agg[edge_key_d] = {"count": 0, "amount_sum": 0.0, "risk_sum": 0.0}
            edge_agg[edge_key_d]["count"] += 1
            edge_agg[edge_key_d]["amount_sum"] += amount
            edge_agg[edge_key_d]["risk_sum"] += risk
    
    # Build nodes
    nodes = []
    
    # User nodes
    for user_id, s in user_stats.items():
        avg_risk = s["risk_sum"] / s["risk_count"] if s["risk_count"] > 0 else 0
        # Get username for display
        user_obj = db.query(User.username, User.email).filter(User.id == user_id).first()
        label = user_obj.username if user_obj and user_obj.username else (user_obj.email if user_obj else f"User_{user_id}")
        nodes.append({
            "id": f"user_{user_id}",
            "label": label,
            "type": "user",
            "val": avg_risk * 10 + 2,
            "risk_score": round(avg_risk * 100, 1),
            "merchant_count": len(s["merchants"]),
            "device_count": len(s["devices"]),
            "tx_count": s["tx_count"],
            "avg_amount": round(s["total_amount"] / s["tx_count"], 2) if s["tx_count"] > 0 else 0,
            "anomaly_rate": round((s["flagged"] / s["tx_count"] * 100), 1) if s["tx_count"] > 0 else 0
        })
    
    # Merchant nodes
    for merchant, m in merchant_stats.items():
        avg_risk = m["risk_sum"] / m["risk_count"] if m["risk_count"] > 0 else 0
        nodes.append({
            "id": f"merchant_{merchant}",
            "label": merchant,
            "type": "merchant",
            "val": 3,
            "avg_amount": round(m["amount_sum"] / m["amount_count"], 2) if m["amount_count"] > 0 else 0,
            "anomaly_rate": round((m["flagged"] / m["tx_count"] * 100), 1) if m["tx_count"] > 0 else 0,
            "user_count": len(m["users"]),
            "tx_count": m["tx_count"],
            "risk_score": round(avg_risk * 100, 1)
        })
    
    # Device nodes
    for device_id, d in device_stats.items():
        avg_risk = d["risk_sum"] / d["risk_count"] if d["risk_count"] > 0 else 0
        nodes.append({
            "id": f"device_{device_id}",
            "label": f"Device_{device_id[:8]}",
            "type": "device",
            "val": len(d["users"]) + 1,
            "user_count": len(d["users"]),
            "tx_count": d["tx_count"],
            "risk_score": round(avg_risk * 100, 1)
        })
    
    # Sort and limit
    nodes.sort(key=lambda x: x["risk_score"], reverse=True)
    if len(nodes) > max_nodes:
        nodes = nodes[:max_nodes]
        retained = {n["id"] for n in nodes}
    else:
        retained = None
    
    # Build links
    links = []
    for (source, target), e in edge_agg.items():
        if retained and (source not in retained or target not in retained):
            continue
        links.append({
            "source": source,
            "target": target,
            "tx_count": e["count"],
            "avg_amount": round(e["amount_sum"] / e["count"], 2) if e["count"] > 0 else 0,
            "risk": round(e["risk_sum"] / e["count"], 4) if e["count"] > 0 else 0
        })
    
    process_time_ms = round((time.time() - process_start) * 1000, 2)
    total_time_ms = round((time.time() - start_time) * 1000, 2)
    
    # Build search context for UI
    search_context = {}
    if transaction_id:
        search_context["transaction_id"] = transaction_id
    if merchant_name:
        search_context["merchant_name"] = merchant_name
    if username:
        search_context["username"] = username
    
    return {
        "nodes": nodes,
        "links": links,
        "stats": {
            "total_users": len(user_stats),
            "total_merchants": len(merchant_stats),
            "total_devices": len(device_stats),
            "total_transactions": len(txs),
            "nodes_rendered": len(nodes),
            "links_rendered": len(links),
            "search_mode": True
        },
        "search_context": search_context,
        "_performance": {
            "query_ms": query_time_ms,
            "processing_ms": process_time_ms,
            "total_ms": total_time_ms
        }
    }


@router.get("/cluster-analysis/search")
async def search_cluster_analysis(
    transaction_id: Optional[int] = Query(None, description="Search by transaction ID"),
    merchant_name: Optional[str] = Query(None, description="Search by merchant name (partial match)"),
    username: Optional[str] = Query(None, description="Search by username (partial match)"),
    min_cluster_size: int = Query(2, ge=2, le=50),
    risk_threshold: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin)
):
    """
    Search-based cluster analysis. Only analyzes clusters containing the searched entities.
    At least one search parameter must be provided.
    """
    if not transaction_id and not merchant_name and not username:
        return {
            "clusters": [],
            "total_clusters": 0,
            "message": "Please provide at least one search parameter"
        }
    
    # Identify target user IDs and merchants
    target_user_ids = set()
    target_merchants = set()
    target_tx_ids = set()
    
    # FAST PATH: If ONLY transaction_id is provided, return just that transaction's context
    only_tx_id = transaction_id and not merchant_name and not username
    
    if transaction_id:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if tx:
            target_tx_ids.add(tx.id)
            if only_tx_id:
                # Strict mode: only this user/merchant for this specific TX
                target_user_ids.add(tx.user_id)
                if tx.merchant:
                    target_merchants.add(tx.merchant)
            else:
                target_user_ids.add(tx.user_id)
                if tx.merchant:
                    target_merchants.add(tx.merchant)
    
    if username:
        matching_users = db.query(User).filter(
            User.username.ilike(f"%{username}%")
        ).limit(50).all()
        for u in matching_users:
            target_user_ids.add(u.id)
    
    if merchant_name:
        matching_txs = db.query(Transaction.merchant).filter(
            Transaction.merchant.ilike(f"%{merchant_name}%")
        ).distinct().limit(50).all()
        for (m,) in matching_txs:
            target_merchants.add(m)
        # Also find users who transacted with these merchants
        if target_merchants:
            user_txs = db.query(Transaction.user_id).filter(
                Transaction.merchant.in_(list(target_merchants))
            ).distinct().limit(200).all()
            for (uid,) in user_txs:
                target_user_ids.add(uid)
    
    if not target_user_ids and not target_merchants and not target_tx_ids:
        return {
            "clusters": [],
            "total_clusters": 0,
            "message": "No matching entities found"
        }
    
    # Get transactions for the target entities
    if only_tx_id:
        # Strict: only the single transaction (though clustering needs more)
        filters = [Transaction.id.in_(list(target_tx_ids))]
    elif username and not merchant_name and not transaction_id:
        # Focused Username Search: Get top 500 transactions for these users
        focused_tx_ids = db.query(Transaction.id).filter(
            Transaction.user_id.in_(list(target_user_ids))
        ).order_by(
            desc(Transaction.timestamp)
        ).limit(500).all()
        
        target_tx_ids = {tid for (tid,) in focused_tx_ids}
        filters = [Transaction.id.in_(list(target_tx_ids))]
    else:
        filters = []
        if target_user_ids:
            filters.append(Transaction.user_id.in_(list(target_user_ids)))
        if target_merchants:
            filters.append(Transaction.merchant.in_(list(target_merchants)))
    
    all_txs = db.query(Transaction).filter(
        or_(*filters)
    ).limit(5000).all()
    
    # Filter high-risk for clustering
    high_risk_txs = [tx for tx in all_txs if tx.final_risk_score >= risk_threshold]
    
    # Build connection graph
    user_connections: Dict[int, set] = {}
    user_tx_map: Dict[int, list] = {}
    
    # Pre-index transactions by merchant and device for fast lookups
    merchant_users: Dict[str, set] = {}
    device_users: Dict[str, set] = {}
    
    for tx in high_risk_txs:
        if tx.user_id not in user_tx_map:
            user_tx_map[tx.user_id] = []
        user_tx_map[tx.user_id].append(tx)
        
        if tx.user_id not in user_connections:
            user_connections[tx.user_id] = set()
        
        if tx.merchant:
            if tx.merchant not in merchant_users:
                merchant_users[tx.merchant] = set()
            merchant_users[tx.merchant].add(tx.user_id)
        
        if tx.device_id:
            if tx.device_id not in device_users:
                device_users[tx.device_id] = set()
            device_users[tx.device_id].add(tx.user_id)
    
    # Build connections from shared merchants/devices (in-memory, no extra DB queries)
    for merchant, users in merchant_users.items():
        user_list = list(users)
        for i in range(len(user_list)):
            for j in range(i + 1, len(user_list)):
                user_connections.setdefault(user_list[i], set()).add(user_list[j])
                user_connections.setdefault(user_list[j], set()).add(user_list[i])
    
    for device, users in device_users.items():
        user_list = list(users)
        for i in range(len(user_list)):
            for j in range(i + 1, len(user_list)):
                user_connections.setdefault(user_list[i], set()).add(user_list[j])
                user_connections.setdefault(user_list[j], set()).add(user_list[i])
    
    # Detect clusters using DFS
    visited = set()
    clusters = []
    cluster_id = 1
    
    def dfs(user_id: int, component: set):
        visited.add(user_id)
        component.add(user_id)
        if user_id in user_connections:
            for neighbor in user_connections[user_id]:
                if neighbor not in visited:
                    dfs(neighbor, component)
    
    for user_id in user_connections.keys():
        if user_id not in visited:
            component = set()
            dfs(user_id, component)
            
            if len(component) >= min_cluster_size:
                cluster_users = list(component)
                cluster_txs = [tx for tx in all_txs if tx.user_id in component]
                
                if not cluster_txs:
                    continue
                
                total_amount = sum(tx.amount for tx in cluster_txs)
                avg_amount = total_amount / len(cluster_txs)
                avg_risk = sum(tx.final_risk_score for tx in cluster_txs) / len(cluster_txs)
                flagged_count = sum(1 for tx in cluster_txs if tx.status in ["FLAGGED", "BLOCKED"])
                
                devices = {}
                merchants = {}
                for tx in cluster_txs:
                    if tx.device_id:
                        if tx.device_id not in devices:
                            devices[tx.device_id] = set()
                        devices[tx.device_id].add(tx.user_id)
                    if tx.merchant:
                        if tx.merchant not in merchants:
                            merchants[tx.merchant] = set()
                        merchants[tx.merchant].add(tx.user_id)
                
                shared_devices = [
                    {"device_id": dev_id, "user_count": len(users)}
                    for dev_id, users in devices.items() if len(users) > 1
                ]
                shared_devices.sort(key=lambda x: x["user_count"], reverse=True)
                
                shared_merchants = [
                    {"merchant": merch, "user_count": len(users)}
                    for merch, users in merchants.items() if len(users) > 1
                ]
                shared_merchants.sort(key=lambda x: x["user_count"], reverse=True)
                
                pattern = "Unknown pattern"
                if shared_devices:
                    top_device_users = shared_devices[0]["user_count"]
                    if top_device_users >= len(component) * 0.5:
                        pattern = f"Shared device ({shared_devices[0]['device_id'][:8]}...)"
                elif len(set(tx.merchant for tx in cluster_txs)) == 1:
                    pattern = f"Single merchant ({cluster_txs[0].merchant})"
                else:
                    amounts = [tx.amount for tx in cluster_txs]
                    if max(amounts) > sum(amounts) / len(amounts) * 3:
                        pattern = "Amount spikes detected"
                
                user_risks = {}
                for uid in cluster_users:
                    u_txs = [tx for tx in cluster_txs if tx.user_id == uid]
                    user_risks[uid] = sum(tx.final_risk_score for tx in u_txs) / len(u_txs) if u_txs else 0
                
                top_users = sorted(user_risks.items(), key=lambda x: x[1], reverse=True)[:3]
                top_user_details = [
                    {
                        "user_id": uid,
                        "risk_score": round(risk * 100, 1),
                        "contribution": round(risk / avg_risk * 100, 1) if avg_risk > 0 else 0
                    }
                    for uid, risk in top_users
                ]
                
                clusters.append({
                    "cluster_id": cluster_id,
                    "risk_score": round(avg_risk * 100, 1),
                    "user_count": len(component),
                    "merchant_count": len(merchants),
                    "device_count": len(devices),
                    "total_tx_count": len(cluster_txs),
                    "flagged_tx_count": flagged_count,
                    "avg_amount": round(avg_amount, 2),
                    "total_amount": round(total_amount, 2),
                    "dominant_pattern": pattern,
                    "top_users": top_user_details,
                    "shared_devices": shared_devices[:3],
                    "shared_merchants": shared_merchants[:3]
                })
                cluster_id += 1
    
    clusters.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "clusters": clusters,
        "total_clusters": len(clusters),
        "search_mode": True
    }


@router.get("/cluster-analysis")
async def get_cluster_analysis(
    days: int = Query(30, ge=1, le=365),
    min_cluster_size: int = Query(3, ge=2, le=50),
    risk_threshold: float = Query(0.6, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst_or_admin)
):
    """
    Detect and analyze fraud clusters with comprehensive metrics.
    Returns cluster statistics, risk scores, and dominant fraud patterns.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get high-risk transactions
    high_risk_txs = db.query(Transaction).filter(
        and_(
            Transaction.timestamp >= cutoff_date,
            Transaction.final_risk_score >= risk_threshold
        )
    ).all()
    
    # Build connection graph
    user_connections: Dict[int, set] = {}
    user_tx_map: Dict[int, list] = {}
    
    for tx in high_risk_txs:
        if tx.user_id not in user_tx_map:
            user_tx_map[tx.user_id] = []
        user_tx_map[tx.user_id].append(tx)
        
        if tx.user_id not in user_connections:
            user_connections[tx.user_id] = set()
        
        # Find connected users (shared merchant or device)
        related_txs = db.query(Transaction).filter(
            and_(
                Transaction.timestamp >= cutoff_date,
                Transaction.user_id != tx.user_id,
                ((Transaction.merchant == tx.merchant) | 
                 (Transaction.device_id == tx.device_id))
            )
        ).all()
        
        for related_tx in related_txs:
            if related_tx.final_risk_score >= risk_threshold:
                user_connections[tx.user_id].add(related_tx.user_id)
    
    # Detect clusters using DFS
    visited = set()
    clusters = []
    cluster_id = 1
    
    def dfs(user_id: int, component: set):
        visited.add(user_id)
        component.add(user_id)
        if user_id in user_connections:
            for neighbor in user_connections[user_id]:
                if neighbor not in visited:
                    dfs(neighbor, component)
    
    # Find all connected components
    for user_id in user_connections.keys():
        if user_id not in visited:
            component = set()
            dfs(user_id, component)
            
            if len(component) >= min_cluster_size:
                # Gather cluster transactions
                cluster_users = list(component)
                cluster_txs = db.query(Transaction).filter(
                    and_(
                        Transaction.user_id.in_(cluster_users),
                        Transaction.timestamp >= cutoff_date
                    )
                ).all()
                
                # Calculate statistics
                total_amount = sum(tx.amount for tx in cluster_txs)
                avg_amount = total_amount / len(cluster_txs) if cluster_txs else 0
                avg_risk = sum(tx.final_risk_score for tx in cluster_txs) / len(cluster_txs) if cluster_txs else 0
                flagged_count = sum(1 for tx in cluster_txs if tx.status in ["FLAGGED", "BLOCKED"])
                
                # Identify shared devices and merchants
                devices = {}
                merchants = {}
                for tx in cluster_txs:
                    if tx.device_id:
                        if tx.device_id not in devices:
                            devices[tx.device_id] = set()
                        devices[tx.device_id].add(tx.user_id)
                    
                    if tx.merchant not in merchants:
                        merchants[tx.merchant] = set()
                    merchants[tx.merchant].add(tx.user_id)
                
                # Find most shared device (risk amplifier)
                shared_devices = [
                    {"device_id": dev_id, "user_count": len(users)}
                    for dev_id, users in devices.items() if len(users) > 1
                ]
                shared_devices.sort(key=lambda x: x["user_count"], reverse=True)
                
                # Find most shared merchant
                shared_merchants = [
                    {"merchant": merch, "user_count": len(users)}
                    for merch, users in merchants.items() if len(users) > 1
                ]
                shared_merchants.sort(key=lambda x: x["user_count"], reverse=True)
                
                # Determine dominant pattern
                pattern = "Unknown pattern"
                if shared_devices:
                    top_device_users = shared_devices[0]["user_count"]
                    if top_device_users >= len(component) * 0.5:
                        pattern = f"Shared device ({shared_devices[0]['device_id'][:8]}...)"
                elif len(set(tx.merchant for tx in cluster_txs)) == 1:
                    pattern = f"Single merchant ({cluster_txs[0].merchant})"
                else:
                    # Check for amount spikes
                    amounts = [tx.amount for tx in cluster_txs]
                    if max(amounts) > sum(amounts) / len(amounts) * 3:
                        pattern = "Amount spikes detected"
                
                # Get top risk contributors
                user_risks = {}
                for user_id in cluster_users:
                    user_txs = [tx for tx in cluster_txs if tx.user_id == user_id]
                    user_risks[user_id] = sum(tx.final_risk_score for tx in user_txs) / len(user_txs) if user_txs else 0
                
                top_users = sorted(user_risks.items(), key=lambda x: x[1], reverse=True)[:3]
                top_user_details = [
                    {
                        "user_id": user_id,
                        "risk_score": round(risk * 100, 1),
                        "contribution": round(risk / avg_risk * 100, 1) if avg_risk > 0 else 0
                    }
                    for user_id, risk in top_users
                ]
                
                clusters.append({
                    "cluster_id": cluster_id,
                    "risk_score": round(avg_risk * 100, 1),
                    "user_count": len(component),
                    "merchant_count": len(merchants),
                    "device_count": len(devices),
                    "total_tx_count": len(cluster_txs),
                    "flagged_tx_count": flagged_count,
                    "avg_amount": round(avg_amount, 2),
                    "total_amount": round(total_amount, 2),
                    "dominant_pattern": pattern,
                    "top_users": top_user_details,
                    "shared_devices": shared_devices[:3],
                    "shared_merchants": shared_merchants[:3]
                })
                cluster_id += 1
    
    # Sort by risk score descending
    clusters.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "clusters": clusters,
        "total_clusters": len(clusters),
        "analysis_period_days": days
    }
