import { useEffect } from 'react';
import { useAuthStore } from '../auth/auth.store';

export const useAlerts = () => {
    const token = useAuthStore(state => state.token);
    const role = useAuthStore(state => state.role);

    useEffect(() => {
        if (!token) return;

        // Alerts are for admin and fraud_analyst roles
        const isAdminOrAnalyst = role === 'admin' || role === 'fraud_analyst';
        if (!isAdminOrAnalyst) return;

        // Request Browser Notification Permission
        if ("Notification" in window) {
            if (Notification.permission !== "granted" && Notification.permission !== "denied") {
                Notification.requestPermission();
            }
        }

        const ws = new WebSocket(`ws://localhost:8000/ws/transactions?token=${token}`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'FRAUD_ALERT') {
                console.log("🚨 SYSTEM ALERT RECV:", data);

                // 1. Browser Notification
                if (Notification.permission === "granted") {
                    new Notification("🚨 FinGuard Fraud Alert!", {
                        body: data.message,
                        icon: "/favicon.ico" // Assuming favicon exists
                    });
                }

                // 2. Play subtle alert sound (optional)
                // const audio = new Audio('/alert.mp3');
                // audio.play();
            }
        };

        ws.onclose = () => {
            console.log("WebSocket for Alerts closed. Retrying in 10s...");
            // Reconnection logic could go here
        };

        return () => {
            ws.close();
        };
    }, [token, role]);
};
