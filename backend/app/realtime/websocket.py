"""
FinGuard Real-Time WebSocket Module
====================================
Provides real-time transaction streaming with role-based filtering.

Features:
- Role-aware connection management
- Targeted broadcasting (by role, by user)
- Event types: NEW_TRANSACTION, ANALYST_ACTION, SYSTEM_ALERT
- Automatic reconnection handling
"""
from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging

from app.db.models import User, Transaction, AuditLog, UserRole

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: int
    user_email: str
    role: str
    connected_at: datetime = field(default_factory=datetime.utcnow)


class RoleAwareConnectionManager:
    """
    WebSocket connection manager with role-based filtering.
    
    Capabilities:
    - Track connections by user and role
    - Broadcast to all, by role, or by user
    - Support multiple event types
    """
    
    def __init__(self):
        self.active_connections: Dict[int, ConnectionInfo] = {}  # user_id -> ConnectionInfo
        self.connections_by_role: Dict[str, Set[int]] = {  # role -> set of user_ids
            "end_user": set(),
            "fraud_analyst": set(),
            "admin": set(),
            "auditor": set(),
            "user": set()  # Legacy role
        }
    
    async def connect(self, websocket: WebSocket, user: User):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        conn_info = ConnectionInfo(
            websocket=websocket,
            user_id=user.id,
            user_email=user.email,
            role=user.role
        )
        
        self.active_connections[user.id] = conn_info
        
        # Add to role group
        role = user.role if user.role in self.connections_by_role else "end_user"
        self.connections_by_role[role].add(user.id)
        
        logger.info(f"WebSocket connected: user={user.email}, role={user.role}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "data": {
                "user_id": user.id,
                "role": user.role,
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    
    def disconnect(self, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            conn_info = self.active_connections[user_id]
            
            # Remove from role group
            role = conn_info.role if conn_info.role in self.connections_by_role else "end_user"
            self.connections_by_role[role].discard(user_id)
            
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: user_id={user_id}")
    
    async def broadcast_all(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        
        for user_id, conn_info in self.active_connections.items():
            try:
                await conn_info.websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                disconnected.append(user_id)
        
        # Clean up disconnected clients
        for user_id in disconnected:
            self.disconnect(user_id)

    async def broadcast_json(self, message: dict):
        """Generic JSON broadcast to all connected clients."""
        await self.broadcast_all(message)
    
    async def broadcast_to_roles(self, message: dict, roles: List[str]):
        """
        Broadcast message to users with specific roles.
        
        Args:
            message: Message to send
            roles: List of roles to broadcast to
        """
        target_users = set()
        for role in roles:
            if role in self.connections_by_role:
                target_users.update(self.connections_by_role[role])
        
        disconnected = []
        
        for user_id in target_users:
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id}: {e}")
                    disconnected.append(user_id)
        
        for user_id in disconnected:
            self.disconnect(user_id)
    
    async def broadcast_to_user(self, message: dict, user_id: int):
        """Send message to a specific user."""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast_transaction_event(
        self,
        tx: Transaction,
        audit: Optional[AuditLog] = None,
        event_type: str = "NEW_TRANSACTION"
    ):
        """
        Broadcast a transaction event with role-based filtering.
        
        - Analysts and Admins see all transactions
        - End users only see their own transactions
        - Auditors see all transactions (read-only)
        """
        # Full event for analysts/admins/auditors
        full_event = {
            "type": event_type,
            "data": {
                "tx_id": tx.id,
                "user_id": tx.user_id,
                "amount": tx.amount,
                "merchant": tx.merchant,
                "location": tx.location,
                "device_id": tx.device_id,
                "risk_score": tx.final_risk_score,
                "decision": tx.status,
                "risk_flags": tx.risk_flags,
                "similarity_triggered": getattr(tx, "similarity_triggered", False),
                "inherited_from_transaction_id": getattr(tx, "inherited_from_transaction_id", None),
                "explanation": audit.explanation if audit else None,
                "timestamp": tx.timestamp.isoformat() if tx.timestamp else None
            }
        }
        
        # Limited event for end users (only their own, less details)
        user_event = {
            "type": event_type,
            "data": {
                "tx_id": tx.id,
                "amount": tx.amount,
                "merchant": tx.merchant,
                "status": tx.status,
                "similarity_triggered": getattr(tx, "similarity_triggered", False),
                "timestamp": tx.timestamp.isoformat() if tx.timestamp else None
            }
        }
        
        # Send to analysts, admins, auditors
        await self.broadcast_to_roles(full_event, ["fraud_analyst", "admin", "auditor"])
        
        # Send to the specific end user (if connected)
        await self.broadcast_to_user(user_event, tx.user_id)
    
    async def broadcast_analyst_action(
        self,
        audit: AuditLog,
        tx: Transaction
    ):
        """Broadcast when an analyst takes action on a transaction."""
        event = {
            "type": "ANALYST_ACTION",
            "data": {
                "tx_id": audit.tx_id,
                "action": audit.analyst_action,
                "analyst_id": audit.analyst_id,
                "final_decision": audit.final_decision,
                "timestamp": audit.analyst_action_time.isoformat() if audit.analyst_action_time else None
            }
        }
        
        # Broadcast to all analysts, admins, auditors
        await self.broadcast_to_roles(event, ["fraud_analyst", "admin", "auditor"])
        
        # Also notify the transaction owner
        await self.broadcast_to_user(event, tx.user_id)
    
    async def broadcast_system_alert(self, alert_type: str, message: str, severity: str = "info"):
        """Broadcast system alert to admins only."""
        event = {
            "type": "SYSTEM_ALERT",
            "data": {
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await self.broadcast_to_roles(event, ["admin"])
    
    def get_connection_stats(self) -> dict:
        """Get statistics about current connections."""
        return {
            "total_connections": len(self.active_connections),
            "by_role": {
                role: len(users) for role, users in self.connections_by_role.items()
            }
        }


# Global manager instance
manager = RoleAwareConnectionManager()


async def realtime_transactions_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for realtime transaction feed.
    
    Authentication:
    - Pass token as query parameter: ws://host/ws/transactions?token=JWT_TOKEN
    
    Role-based filtering:
    - Admins/Analysts/Auditors: Receive all transaction events
    - End Users: Receive only their own transaction events
    
    Event Types:
    - NEW_TRANSACTION: New transaction processed
    - ANALYST_ACTION: Analyst reviewed a transaction
    - SYSTEM_ALERT: System notifications (admins only)
    """
    # Authenticate user from token
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return
    
    try:
        from app.core.security import decode_token
        from app.db.session import SessionLocal
        from app.db.models import User
        from jose import jwt, JWTError
        from app.core.config import settings
        
        db = SessionLocal()
        try:
            # Handle Dev Bypass Tokens
            if token == "test-token-admin":
                user = db.query(User).filter(User.role == "admin").first()
                if not user:
                    # Fallback to any user if no admin found
                    user = db.query(User).first()
                logger.info(f"Dev Bypass: Authenticated as {user.email} (Admin)")
            elif token == "test-token-user":
                user = db.query(User).filter(User.role == "user").first()
                if not user:
                    user = db.query(User).first()
                logger.info(f"Dev Bypass: Authenticated as {user.email} (User)")
            else:
                # Normal JWT validation - use direct jwt.decode to avoid HTTPException
                try:
                    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
                    email = payload.get("sub")
                    if not email:
                        logger.error("WebSocket auth failed: No 'sub' in token payload")
                        await websocket.close(code=4001, reason="Invalid token format")
                        return
                    
                    user = db.query(User).filter(User.email == email).first()
                    
                    if not user:
                        logger.error(f"WebSocket auth failed: User {email} not found in database")
                        await websocket.close(code=4001, reason="User not found")
                        return
                        
                except JWTError as jwt_err:
                    logger.error(f"WebSocket JWT decode failed: {jwt_err}")
                    await websocket.close(code=4001, reason=f"Invalid token: {str(jwt_err)}")
                    return
            
            if not user:
                logger.error("WebSocket auth failed: No user object created")
                await websocket.close(code=4001, reason="User not found")
                return
            
            if not user.is_active:
                logger.error(f"WebSocket auth failed: User {user.email} is inactive")
                await websocket.close(code=4003, reason="User deactivated")
                return
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"WebSocket auth failed (outer): {e}", exc_info=True)
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Connect
    await manager.connect(websocket, user)
    
    # Heartbeat task
    async def heartbeat():
        """Send periodic heartbeat to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
        except Exception:
            pass
    
    # Start heartbeat task
    heartbeat_task = asyncio.create_task(heartbeat())
    
    try:
        while True:
            # Handle incoming messages (heartbeat, commands)
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_json({"type": "pong"})
            elif data == "stats" and user.role in ["admin", "fraud_analyst"]:
                await websocket.send_json({
                    "type": "CONNECTION_STATS",
                    "data": manager.get_connection_stats()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(user.id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        manager.disconnect(user.id)
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


# Export for use in other modules
def get_websocket_manager() -> RoleAwareConnectionManager:
    """Get the global WebSocket manager instance."""
    return manager
