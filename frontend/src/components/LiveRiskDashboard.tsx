import { useEffect, useState } from 'react'
import { fetchRiskGauges } from '../api/analytics.api'

interface RiskMetrics {
    avg_risk: number
    block_rate: number
    total_critical: number
    total_saved: number
    top_risk_merchant: string
}

export default function LiveRiskDashboard() {
    const [metrics, setMetrics] = useState<RiskMetrics | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const loadMetrics = async () => {
            try {
                const data = await fetchRiskGauges()
                setMetrics(data)
            } catch (err) {
                console.error("Failed to fetch risk gauges:", err)
            } finally {
                setLoading(false)
            }
        }
        loadMetrics()
        const interval = setInterval(loadMetrics, 5000) // Poll every 5s for "live" feel
        return () => clearInterval(interval)
    }, [])

    if (loading && !metrics) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8 animate-pulse text-transparent">
                {[1, 2, 3, 4].map(i => (
                    <div key={i} className="h-32 bg-gray-200 rounded-2xl"></div>
                ))}
            </div>
        )
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* ROI Metric */}
            <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-3xl p-6 shadow-xl text-white transform transition-all hover:scale-[1.02] relative overflow-hidden">
                <div className="relative z-10">
                    <p className="text-xs font-black uppercase tracking-widest opacity-80 mb-2">Total Value Protected</p>
                    <h2 className="text-4xl font-black mb-1">₹{(metrics?.total_saved || 0).toLocaleString('en-IN')}</h2>
                    <p className="text-[10px] font-bold text-blue-200 uppercase tracking-tighter">Business ROI Impact: HIGH</p>
                </div>
                <div className="absolute -right-4 -bottom-4 text-8xl opacity-10 font-black">💰</div>
            </div>

            {/* False Positive Impact */}
            <div className="bg-white rounded-3xl p-6 shadow-lg border border-gray-100 flex flex-col justify-between">
                <div>
                    <p className="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">False Positive Impact</p>
                    <div className="flex items-end gap-2">
                        <h2 className="text-3xl font-black text-orange-600">₹{((metrics?.total_saved || 0) * 0.05).toLocaleString('en-IN')}</h2>
                        <span className="text-[10px] font-bold text-gray-400 mb-1 uppercase tracking-tighter">(Estimated)</span>
                    </div>
                </div>
                <div className="mt-4">
                    <p className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Revenue at risk from false flags</p>
                </div>
            </div>

            {/* Risk Rate */}
            <div className="bg-white rounded-3xl p-6 shadow-lg border border-gray-100 flex flex-col justify-between">
                <div>
                    <p className="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Neural Block Rate</p>
                    <div className="flex items-end gap-2">
                        <h2 className="text-3xl font-black text-gray-900">{metrics?.block_rate}%</h2>
                        <span className="text-xs font-bold text-green-500 mb-1">↑ 2.4%</span>
                    </div>
                </div>
                <div className="mt-4 w-full bg-gray-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-blue-600 h-full transition-all duration-1000" style={{ width: `${metrics?.block_rate}%` }}></div>
                </div>
            </div>

            {/* Critical Alerts */}
            <div className="bg-white rounded-3xl p-6 shadow-lg border border-gray-100">
                <p className="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Critical Anomalies</p>
                <h2 className="text-3xl font-black text-red-600">{metrics?.total_critical}</h2>
                <p className="text-[10px] font-bold text-gray-400 mt-2 uppercase">Score {'>'} 0.9 (Immediate Action)</p>
            </div>

            {/* Top Merchant */}
            <div className="bg-white rounded-3xl p-6 shadow-lg border border-gray-100">
                <p className="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Hotspot Merchant</p>
                <h2 className="text-2xl font-black text-indigo-900 truncate">{metrics?.top_risk_merchant}</h2>
                <div className="mt-2 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
                    <p className="text-[10px] font-bold text-indigo-500 uppercase">Monitoring Live Traffic</p>
                </div>
            </div>
        </div>
    )
}
