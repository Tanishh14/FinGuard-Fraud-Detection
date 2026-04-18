import logging
import io
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fpdf import FPDF

from app.analytics.repository import AnalyticsRepository

logger = logging.getLogger(__name__)

class AnalyticsService:
    """
    Service for providing high-level business intelligence and dashboard metrics.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository(db)

    def get_kpi_dashboard(self) -> Dict[str, Any]:
        """Collects all core KPIs for the main dashboard banner."""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        status_counts = self.repo.get_status_counts(last_24h)
        status_map = {s: c for s, c in status_counts}
        total_24h = sum(status_map.values())
        
        return {
            "kpi": {
                "total_24h": total_24h,
                "approved_rate": round(status_map.get("APPROVED", 0) / (total_24h or 1) * 100, 1),
                "blocked_rate": round(status_map.get("BLOCKED", 0) / (total_24h or 1) * 100, 1),
                "review_rate": round(status_map.get("FLAGGED", 0) / (total_24h or 1) * 100, 1),
                "avg_anomaly_score": round(self.repo.get_avg_risk_score(last_24h), 3),
                "active_high_risk_users": self.repo.get_high_risk_user_count(last_24h, 0.8),
                "active_fraud_rings": self.repo.get_low_trust_device_count(0.3)
            },
            "live_graph": self._get_live_graph_data(now)
        }

    def get_risk_entities(self, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Ranks users, merchants, and devices by risk level."""
        last_7d = datetime.utcnow() - timedelta(days=7)
        users = self.repo.get_top_users_by_risk(last_7d, 0.5, limit)
        merchants = self.repo.get_top_merchants(limit)
        
        return {
            "users": [{"id": u.user_id, "risk": round(u.max_risk, 3), "count": u.tx_count, "last_active": u.last_active} for u in users],
            "merchants": merchants,
            "devices": [] # Placeholder for now to avoid frontend crash
        }

    def get_geo_metrics(self, days: int = 30) -> List[Dict[str, Any]]:
        """Aggregated spatial distribution of transactions."""
        start = datetime.utcnow() - timedelta(days=days)
        data = self.repo.get_geo_data(start)
        return [{
            "location": r.location, "lat": r.latitude, "lng": r.longitude,
            "count": r.count, "risk": round(float(r.avg_risk), 2)
        } for r in data]

    def get_model_performance(self, days: int = 30) -> Dict[str, Any]:
        """Calculates ML model precision, recall, and accuracy."""
        # Frontend ModelPerf interface expects deviations and intensities
        # Let's provide both the telemetry the UI wants and the stats I added
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        return {
            "autoencoder_deviation": round(self.repo.get_avg_anomaly_score(last_24h), 3),
            "gnn_risk_intensity": round(self.repo.get_avg_gnn_score(last_24h), 3),
            "isolation_forest_anomaly": round(self.repo.get_avg_if_score(last_24h), 3),
            "avg_final_risk": round(self.repo.get_avg_risk_score(last_24h), 3),
            "stats": self.repo.get_model_performance(now - timedelta(days=days), now)
        }

    def get_case_dashboard(self) -> Dict[str, Any]:
        """High-level summary of investigation cases."""
        stats = self.repo.get_case_stats()
        return {
            "open_cases": stats.get("open", 0),
            "pending_reviews": stats.get("pending", 0),
            "resolved_today": stats.get("resolved_today", 0)
        }

    def get_risk_trends(self, days: int = 7, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Time-series data for risk levels."""
        return self.repo.get_risk_trends(days, threshold)

    def get_risk_gauges(self, threshold: float = 0.9) -> Dict[str, Any]:
        """Specific distribution for radial gauge charts."""
        return self.repo.get_risk_gauges(threshold)

    def get_top_merchants(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Ranked list of merchants by transaction count/risk."""
        return self.repo.get_top_merchants(limit)

    def get_forensic_summary(self) -> Dict[str, Any]:
        """Aggregate forensic investigation metrics."""
        return self.repo.get_forensic_summary()

    def _get_live_graph_data(self, now: datetime) -> List[Dict[str, Any]]:
        """Helper to format time-bucketed graph metrics."""
        start = now - timedelta(minutes=60)
        raw_data = self.repo.get_time_bucketed_stats(start)
        
        graph_map = {}
        for minute, status, count in raw_data:
            if minute not in graph_map:
                graph_map[minute] = {"time": minute, "APPROVED": 0, "BLOCKED": 0, "FLAGGED": 0}
            if status in ["APPROVED", "BLOCKED"]:
                graph_map[minute][status] = count
            else:
                graph_map[minute]["FLAGGED"] += count
                
        return sorted(graph_map.values(), key=lambda x: x['time'])

    def generate_transaction_report(self, time_range: str, username: Optional[str] = None) -> bytes:
        """Generates a professional PDF report of transactions."""
        # Calculate start time based on range
        now = datetime.utcnow()
        start_time = None
        if time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "monthly":
            start_time = now - timedelta(days=30)
        elif time_range == "yearly":
            start_time = now - timedelta(days=365)

        # Fetch data
        transactions = self.repo.get_filtered_transactions(start_time=start_time, username=username)
        total_amount = sum(tx.amount for tx in transactions)
        
        # Initialize PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", "B", 20)
        pdf.set_text_color(33, 37, 41)
        pdf.cell(0, 15, "FinGuard AI - Transaction Report", ln=True, align="C")
        
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(108, 117, 125)
        pdf.cell(0, 10, f"Generated On: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}", ln=True, align="C")
        pdf.ln(10)
        
        # Filter Summary
        pdf.set_fill_color(248, 249, 250)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "Report Parameters", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 8, f"Time Range: {time_range.capitalize()}", ln=True)
        if username:
            pdf.cell(0, 8, f"User Filter: {username}", ln=True)
        pdf.ln(5)
        
        # Table Header
        pdf.set_fill_color(52, 58, 64)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 10)
        
        col_widths = [30, 60, 40, 60]
        headers = ["TX ID", "User Name", "Amount (INR)", "Timestamp"]
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, border=1, align="C", fill=True)
        pdf.ln()
        
        # Table Content
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 9)
        fill = False
        
        for tx in transactions:
            # Alternating row colors
            if fill:
                pdf.set_fill_color(242, 242, 242)
            else:
                pdf.set_fill_color(255, 255, 255)
                
            pdf.cell(col_widths[0], 8, str(tx.id), border=1, fill=True)
            pdf.cell(col_widths[1], 8, tx.username, border=1, fill=True)
            pdf.cell(col_widths[2], 8, f"{tx.amount:,.2f}", border=1, align="R", fill=True)
            pdf.cell(col_widths[3], 8, tx.timestamp.strftime("%Y-%m-%d %H:%M"), border=1, fill=True)
            pdf.ln()
            fill = not fill
            
        # Summary Section at Bottom
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(233, 236, 239)
        pdf.cell(130, 12, "TOTAL TRANSACTIONS", border=1, fill=True)
        pdf.cell(60, 12, str(len(transactions)), border=1, align="R", fill=True, ln=True)
        
        pdf.cell(130, 12, "TOTAL DISBURSED AMOUNT", border=1, fill=True)
        pdf.cell(60, 12, f"INR {total_amount:,.2f}", border=1, align="R", fill=True, ln=True)
        
        # Footer
        pdf.set_y(-20)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(173, 181, 189)
        pdf.cell(0, 10, "CONFIDENTIAL - PROPERTY OF FINGUARD AI FINANCIAL INTELLIGENCE UNIT", align="C")
        
        return bytes(pdf.output())
