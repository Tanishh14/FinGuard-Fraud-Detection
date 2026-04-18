import { useState, useEffect } from 'react'
import { useAuthStore } from '../auth/auth.store'

interface Props {
    transaction: any
    onClose: () => void
    onActionSuccess?: () => void
}

export default function InvestigationPanel({ transaction, onClose, onActionSuccess }: Props) {
    const token = useAuthStore(s => s.token)
    const [forensics, setForensics] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [actionLoading, setActionLoading] = useState<string | null>(null)

    const fetchForensics = async () => {
        try {
            const headers: any = { 'Content-Type': 'application/json' }
            if (token) {
                headers['Authorization'] = `Bearer ${token}`
            }
            
            const res = await fetch(`http://localhost:8000/forensics/story/${transaction.id}`, {
                credentials: 'include',
                headers
            })
            
            if (!res.ok) {
                console.error(`Forensics fetch failed: ${res.status}`, await res.json())
                setForensics(null)
                return
            }
            
            const data = await res.json()
            setForensics(data)
        } catch (err) {
            console.error("Failed to fetch forensics:", err)
            setForensics(null)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (transaction?.id) fetchForensics()
    }, [transaction, token])

    const handleAction = async (endpoint: string, actionName: string) => {
        setActionLoading(actionName)
        try {
            const headers: any = { 'Content-Type': 'application/json' }
            if (token) {
                headers['Authorization'] = `Bearer ${token}`
            }
            
            const res = await fetch(`http://localhost:8000/${endpoint}`, {
                method: 'POST',
                credentials: 'include',
                headers
            })
            
            const data = await res.json()
            
            if (res.ok) {
                console.log(`✓ ${actionName} successful:`, data)
                alert(`✓ ${actionName} completed successfully`)
                fetchForensics() // Refresh panel data
                if (onActionSuccess) onActionSuccess() // Refresh dashboard data
            } else {
                const errorMsg = data.detail || data.message || `${actionName} failed`
                console.error(`✗ ${actionName} failed:`, errorMsg)
                alert(`✗ ${actionName} failed: ${errorMsg}`)
            }
        } catch (err: any) {
            const errorMsg = err.message || 'Network error'
            console.error(`✗ ${actionName} failed with error:`, err)
            alert(`✗ ${actionName} failed: ${errorMsg}`)
        } finally {
            setActionLoading(null)
        }
    }

    if (!transaction) return null

    // Render Risk History SVG Line Chart
    const renderRiskChart = () => {
        if (!forensics?.forensics?.risk_history || forensics.forensics.risk_history.length < 2) return null
        const history = forensics.forensics.risk_history
        const width = 400
        const height = 100
        const points = history.map((d: any, i: number) => {
            const x = (i / (history.length - 1)) * width
            const y = height - (d.score * height)
            return `${x},${y}`
        }).join(' ')

        return (
            <div className="mb-8 p-6 bg-gray-800/30 border border-gray-700 rounded-3xl">
                <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 italic">Fraud Score Evolution</h3>
                <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-24 overflow-visible">
                    <defs>
                        <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.5" />
                            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                        </linearGradient>
                    </defs>
                    <path
                        d={`M 0,${height} L ${points} L ${width},${height} Z`}
                        fill="url(#riskGradient)"
                    />
                    <polyline
                        points={points}
                        fill="none"
                        stroke="#3b82f6"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                    />
                    {history.map((d: any, i: number) => (
                        <circle
                            key={i}
                            cx={(i / (history.length - 1)) * width}
                            cy={height - (d.score * height)}
                            r="3"
                            fill={d.score > 0.65 ? "#ef4444" : "#3b82f6"}
                            className="hover:r-5 transition-all cursor-pointer"
                        />
                    ))}
                </svg>
            </div>
        )
    }

    return (
        <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-gray-900 shadow-[-20px_0_50px_rgba(0,0,0,0.5)] z-50 overflow-y-auto animate-in slide-in-from-right duration-500 border-l border-blue-500/30">
            <div className="p-8">
                {/* Header */}
                <div className="flex justify-between items-center mb-10 border-b border-gray-800 pb-6">
                    <div>
                        <h2 className="text-2xl font-black text-white uppercase italic tracking-tighter">Forensic Investigation</h2>
                        <p className="text-[10px] font-black text-blue-400 uppercase tracking-widest mt-1">Direct Neural Access • Case #{transaction.id}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="w-10 h-10 rounded-full bg-gray-800 text-gray-400 hover:text-white flex items-center justify-center transition-colors"
                    >
                        ✕
                    </button>
                </div>

                {/* Intelligence Breakdown */}
                <div className="card bg-gray-800/50 p-6 rounded-3xl mb-8 border border-gray-700">
                    <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 italic">Neural Scoring Decomposition</h3>
                    <div className="space-y-4">
                        {transaction.intelligence?.breakdown && Object.entries(transaction.intelligence.breakdown).map(([name, score]: [string, any]) => (
                            <div key={name}>
                                <div className="flex justify-between text-[10px] font-black uppercase text-gray-300 mb-1.5">
                                    <span>{name}</span>
                                    <span className="text-blue-400">{score}%</span>
                                </div>
                                <div className="w-full h-1.5 bg-gray-900 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 transition-all duration-1000"
                                        style={{ width: `${score}%` }}
                                    ></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* User Appeal Details */}
                {transaction.is_appealed && (
                    <div className="card bg-red-500/10 p-6 rounded-3xl mb-8 border border-red-500/30 animate-pulse-slow">
                        <div className="flex justify-between items-start mb-4">
                            <h3 className="text-xs font-black text-red-400 uppercase tracking-widest italic">Formal User Appeal Received</h3>
                            <span className={`px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-widest ${transaction.appeal_urgency === 'HIGH' ? 'bg-red-500 text-white' : 'bg-gray-700 text-gray-300'
                                }`}>
                                {transaction.appeal_urgency === 'HIGH' ? '⚡ URGENT' : 'NORMAL PRIORITY'}
                            </span>
                        </div>
                        <p className="text-sm font-bold text-white leading-relaxed bg-black/40 p-4 rounded-2xl border border-white/5 italic">
                            "{transaction.appeal_reason}"
                        </p>
                        <p className="text-[9px] font-black text-gray-500 uppercase tracking-widest mt-3 text-right">
                            Submitted: {new Date(transaction.appeal_timestamp).toLocaleString()}
                        </p>
                    </div>
                )}

                {/* Risk History Chart */}
                {renderRiskChart()}

                {/* Peer Comparison */}
                {forensics?.forensics?.peer_comparison && (
                    <div className="mb-8 p-6 bg-gray-800/30 border border-gray-700 rounded-3xl">
                        <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 italic">Peer Cohort Benchmarks</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-3 bg-gray-900/50 rounded-2xl border border-gray-700">
                                <p className="text-[8px] font-black text-gray-500 uppercase mb-1">Avg Transaction</p>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-sm font-black text-white">₹{forensics.forensics.peer_comparison.user_avg_amount}</span>
                                    <span className="text-[7px] font-bold text-blue-400">vs ₹{forensics.forensics.peer_comparison.global_avg_amount} (Global)</span>
                                </div>
                            </div>
                            <div className="p-3 bg-gray-900/50 rounded-2xl border border-gray-700">
                                <p className="text-[8px] font-black text-gray-500 uppercase mb-1">Avg Probabilistic Risk</p>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-sm font-black text-white">{forensics.forensics.peer_comparison.user_avg_risk}</span>
                                    <span className="text-[7px] font-bold text-blue-400">vs {forensics.forensics.peer_comparison.global_avg_risk} (Global)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Patterns Detected */}
                <div className="mb-8">
                    <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 italic">Pattern Recognition Labels</h3>
                    <div className="flex flex-wrap gap-2">
                        {transaction.intelligence?.labels?.map((label: string, i: number) => (
                            <div key={i} className="px-3 py-1.5 bg-red-500/10 border border-red-500/20 text-red-500 rounded-xl text-[10px] font-black uppercase tracking-tighter">
                                🚨 {label}
                            </div>
                        ))}
                        {transaction.intelligence?.boosters?.map((b: any, i: number) => (
                            <div key={i} className="px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-xl text-[10px] font-black uppercase tracking-tighter">
                                ✅ {b.label}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Action Center */}
                <div className="mt-auto pt-10 border-t border-gray-800 grid grid-cols-2 gap-4">
                    <button
                        disabled={!!actionLoading || !forensics?.user_context?.is_active}
                        onClick={() => handleAction(`forensics/accounts/freeze/${transaction.user_id}`, 'Freeze Account')}
                        className={`py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl transition-all hover:-translate-y-1 ${!forensics?.user_context?.is_active ? 'bg-gray-700 text-gray-500' : 'bg-red-600 hover:bg-red-700 text-white shadow-red-900/20'}`}
                    >
                        {actionLoading === 'Freeze Account' ? 'Freezing...' : (forensics?.user_context?.is_active ? 'Freeze Account' : 'Account Frozen')}
                    </button>
                    <button
                        disabled={!!actionLoading || transaction.status === 'APPROVED'}
                        onClick={() => handleAction(`forensics/transactions/override/${transaction.id}`, transaction.status === 'UNDER_REVIEW' ? 'Approve Appeal' : 'Approve Override')}
                        className={`py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl transition-all hover:-translate-y-1 ${transaction.status === 'APPROVED' ? 'bg-gray-700 text-gray-500' : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-900/20'}`}
                    >
                        {actionLoading === (transaction.status === 'UNDER_REVIEW' ? 'Approve Appeal' : 'Approve Override') ? 'Processing...' : (transaction.status === 'UNDER_REVIEW' ? 'Approve Appeal ✓' : 'Approve Override')}
                    </button>
                    <button
                        disabled={!!actionLoading}
                        onClick={() => handleAction(`transactions/${transaction.id}/block`, 'Confirm Block')}
                        className={`py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all ${transaction.status === 'UNDER_REVIEW' ? 'bg-red-600 hover:bg-red-700 text-white' : 'bg-gray-700 hover:bg-gray-600 text-white'}`}
                    >
                        {actionLoading === 'Confirm Block' ? 'Blocking...' : (transaction.status === 'UNDER_REVIEW' ? 'Deny Appeal ×' : 'Force Block Transaction')}
                    </button>
                    <button
                        disabled={!!actionLoading}
                        onClick={() => handleAction(`forensics/actions/escalate-legal/${transaction.id}`, 'Escalate Case')}
                        className="py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl shadow-blue-900/20 transition-all hover:-translate-y-1"
                    >
                        {actionLoading === 'Escalate Case' ? 'Escalating...' : 'Escalate to Legal'}
                    </button>
                    <button
                        disabled={!!actionLoading}
                        onClick={() => handleAction(`forensics/feedback/${transaction.id}/false-positive`, 'Mark False Positive')}
                        className={`py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all ${!!actionLoading ? 'bg-gray-700 text-gray-500' : 'bg-purple-600 hover:bg-purple-700 text-white'}`}
                    >
                        {actionLoading === 'Mark False Positive' ? 'Marking...' : '✓ Mark False Positive'}
                    </button>
                </div>
            </div>
        </div>
    )
}
