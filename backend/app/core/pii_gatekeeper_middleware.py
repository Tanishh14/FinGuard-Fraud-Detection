import re
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

logger = logging.getLogger(__name__)

# PII Patterns for Leak Scan (FCA PS21/4, RBI Compliance)
PII_PATTERNS = {
    "account_number": re.compile(r"\b\d{9,18}\b"),
    "phone_number": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
}

class PiiGatekeeperMiddleware(BaseHTTPMiddleware):
    """
    Sovereign PII Isolation Boundary Gatekeeper.
    Enforces a hard architectural boundary between the Sealed Zone (PII) 
    and the Narrative Zone (LLM).
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Inspect Outbound toward Narrative Layer (Simulated by tags or paths)
        # In a real microservice setup, this would be a proxy filter.
        # Here we intercept responses from endpoints that generate narratives.
        
        response = await call_next(request)
        
        # Only scan JSON responses from explainability/narrative routes
        if "/explain" in request.url.path or "/narrative" in request.url.path:
            return await self._secure_response(response)
            
        return response

    async def _secure_response(self, response: Response) -> Response:
        """
        Regex-based scan on LLM outputs for account/phone patterns.
        Rejects or redacts if PII is detected.
        """
        # Consume response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
            
        try:
            body_str = response_body.decode()
            leaks_found = []
            
            for label, pattern in PII_PATTERNS.items():
                if pattern.search(body_str):
                    leaks_found.append(label)
                    
            if leaks_found:
                logger.critical(f"PII LEAK DETECTED in Narrative Output: {leaks_found}")
                # Block the response to satisfy compliance
                error_msg = json.dumps({
                    "error": "PII Leak Blocked",
                    "detail": "Architectural boundary violation: PII detected in narrative zone.",
                    "code": "SOVEREIGN_VIOLATION"
                })
                return Response(
                    content=error_msg,
                    status_code=403,
                    media_type="application/json"
                )
                
        except Exception as e:
            logger.error(f"Error in PII Gatekeeper scan: {e}")
            
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

def strip_pii_for_narrative(raw_data: dict) -> dict:
    """
    Lossy transformation utility to generate an Anonymized Evidence Pack.
    Used before passing data to the Narrative Layer.
    """
    # Extract only verifiable facts without identity
    return {
        "rule_triggers": raw_data.get("risk_flags", []),
        "behavioral_metrics": {
            "velocity": raw_data.get("tx_count_last_hour", 0),
            "amount_z_score": raw_data.get("amount_z_score", 0.0),
            "is_night_tx": raw_data.get("is_night_tx", False)
        },
        "gnn_motifs": raw_data.get("motifs", []),
        "confidence": raw_data.get("final_risk_score", 0.0)
    }
