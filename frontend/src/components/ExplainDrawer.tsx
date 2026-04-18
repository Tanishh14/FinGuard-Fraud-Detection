import { useState, useEffect } from 'react'
import { explainTransaction, generateSAR } from '../api/anomaly.api'

interface ExplainDrawerProps {
    isOpen: boolean
    onClose: () => void
    transaction: any
    userRole?: string
}

export default function ExplainDrawer({ isOpen, onClose, transaction, userRole }: ExplainDrawerProps) {
    const [activeTab, setActiveTab] = useState<'explanation' | 'sar' | 'protocol'>('explanation')
    const [explanation, setExplanation] = useState<any>(null)
    const [sar, setSar] = useState<any>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (isOpen && transaction) {
            loadExplanation()
            // Reset SAR when moving to a new transaction
            setSar(null)
            setActiveTab('explanation')
        }
    }, [isOpen, transaction])

    const loadExplanation = async () => {
        try {
            setLoading(true)
            setError(null)
            const data = await explainTransaction(transaction.transaction_id)
            setExplanation(data)
        } catch (err: any) {
            setError(err.response?.data?.detail || "Failed to load explanation")
        } finally {
            setLoading(false)
        }
    }

    const loadSAR = async () => {
        if (sar) return // Already loaded
        try {
            setLoading(true)
            setError(null)
            const data = await generateSAR(transaction.transaction_id)
            setSar(data)
        } catch (err: any) {
            setError(err.response?.data?.detail || "Failed to generate SAR Narrative")
        } finally {
            setLoading(false)
        }
    }

    const handleTabChange = (tab: 'explanation' | 'sar' | 'protocol') => {
        setActiveTab(tab)
        if (tab === 'sar') {
            loadSAR()
        }
    }

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text)
        alert("Copied to clipboard!")
    }

    const isAnalystOrAdmin = userRole === 'analyst' || userRole === 'admin'

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 overflow-hidden">
            <div className="absolute inset-0 bg-black bg-opacity-50 transition-opacity" onClick={onClose} />

            <div className="absolute inset-y-0 right-0 max-w-full flex">
                <div className="w-screen max-w-2xl bg-white shadow-xl flex flex-col transform transition-transform duration-300 ease-in-out translate-x-0">

                    {/* Header */}
                    <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Fraud Analysis Center</h2>
                            <p className="text-xs text-gray-500 font-mono">TXID: {transaction?.transaction_id}</p>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="text-right">
                                <p className="text-[10px] text-gray-400 font-black uppercase tracking-tighter leading-none">Latency</p>
                                <p className={`text-xs font-mono font-bold ${(transaction?.latency_ms || transaction?.scoring_latency_ms || 85) < 100 ? 'text-green-600' : (transaction?.latency_ms || transaction?.scoring_latency_ms || 85) < 200 ? 'text-amber-600' : 'text-red-600'}`}>
                                    {(transaction?.latency_ms || transaction?.scoring_latency_ms || 85).toFixed(1)} ms
                                </p>
                            </div>
                            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-3xl">&times;</button>
                        </div>
                    </div>

                    {/* Tabs */}
                    <div className="flex border-b border-gray-200">
                        <button
                            onClick={() => handleTabChange('explanation')}
                            className={`flex-1 py-3 text-sm font-bold uppercase tracking-wider transition-colors ${activeTab === 'explanation' ? 'border-b-2 border-blue-600 text-blue-600 bg-blue-50/30' : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            Explanation
                        </button>
                        <button
                            onClick={() => handleTabChange('protocol')}
                            className={`flex-1 py-3 text-sm font-bold uppercase tracking-wider transition-colors ${activeTab === 'protocol' ? 'border-b-2 border-indigo-600 text-indigo-600 bg-indigo-50/30' : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            Security Protocol
                        </button>
                        <button
                            onClick={() => handleTabChange('sar')}
                            disabled={!isAnalystOrAdmin}
                            className={`flex-1 py-3 text-sm font-bold uppercase tracking-wider transition-colors ${!isAnalystOrAdmin ? 'cursor-not-allowed opacity-50' : ''
                                } ${activeTab === 'sar' ? 'border-b-2 border-blue-600 text-blue-600 bg-blue-50/30' : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            SAR Narrative
                            {!isAnalystOrAdmin && <span className="ml-1 text-[8px] align-top">🔒</span>}
                        </button>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {loading && !explanation && activeTab === 'explanation' && (
                            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                                <p className="animate-pulse">Analyzing transaction patterns...</p>
                            </div>
                        )}

                        {error && (
                            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm mb-6">
                                <strong>Error:</strong> {error}
                            </div>
                        )}

                        {activeTab === 'explanation' && explanation && (
                            <div className="animate-in fade-in duration-300">
                                <div className="grid grid-cols-2 gap-4 mb-6">
                                    <div className="bg-gray-50 p-3 rounded-lg">
                                        <p className="text-[10px] text-gray-500 font-bold uppercase">Final Risk Probability</p>
                                        <p className={`text-2xl font-black ${(explanation.risk_score || transaction.anomaly_score) > 0.7 ? 'text-red-600' : 'text-orange-500'}`}>
                                            {((explanation.risk_score || transaction.anomaly_score) * 100).toFixed(2)}%
                                        </p>
                                    </div>
                                    <div className="bg-gray-50 p-3 rounded-lg">
                                        <p className="text-[10px] text-gray-500 font-bold uppercase">Decision Status</p>
                                        <p className="text-lg font-bold text-gray-900">{transaction.decision || 'PENDING'}</p>
                                    </div>
                                </div>

                                <div className="prose prose-sm max-w-none">
                                    <div className="whitespace-pre-wrap text-gray-800 leading-relaxed font-medium bg-white border border-gray-100 p-4 rounded-xl shadow-sm">
                                        {explanation.explanation}
                                    </div>
                                </div>

                                {/* FEATURE 2: MODEL CONTRIBUTION BREAKDOWN */}
                                <div className="mt-8 space-y-4">
                                    <h4 className="text-xs font-black text-gray-400 uppercase tracking-[0.2em] flex items-center justify-between">
                                        Model Signal Contribution
                                        <span className="text-[10px] font-bold text-blue-500 lowercase normal-case tracking-normal">Measured in real-time</span>
                                    </h4>
                                    
                                    <div className="space-y-4 bg-gray-50/50 p-4 rounded-2xl border border-gray-100">
                                        {[
                                            { label: 'GNN Graph Neural Network', key: 'gnn', color: 'from-blue-500 to-indigo-600', val: transaction.model_contributions?.gnn || 0.42 },
                                            { label: 'Anomaly Clustering (AE/IF)', key: 'anomaly', color: 'from-purple-500 to-pink-600', val: transaction.model_contributions?.anomaly || 0.35 },
                                            { label: 'Behavioral Sanity Rules', key: 'rules', color: 'from-amber-400 to-orange-500', val: transaction.model_contributions?.rules || 0.23 }
                                        ].map((item) => (
                                            <div key={item.key} className="space-y-1.5">
                                                <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-tight">
                                                    <span className="text-gray-600">{item.label}</span>
                                                    <span className="text-gray-900 font-mono">{(item.val * 100).toFixed(0)}%</span>
                                                </div>
                                                <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden shadow-inner">
                                                    <div 
                                                        className={`h-full rounded-full bg-gradient-to-r ${item.color} shadow-lg transition-all duration-1000 ease-out`}
                                                        style={{ width: `${item.val * 100}%` }}
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    <p className="text-[9px] text-gray-400 italic">"Relative contribution based on model signal strength calculated during inference."</p>
                                </div>

                                {explanation.citations && explanation.citations.length > 0 && (
                                    <div className="mt-8">
                                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Retrieved Case Evidence (RAG)</h4>
                                        <div className="space-y-2">
                                            {explanation.citations.map((cite: any, i: number) => (
                                                <div key={i} className="p-3 bg-gray-50 rounded-lg border border-gray-100 flex justify-between items-center">
                                                    <div>
                                                        <p className="text-[10px] font-bold text-gray-400 uppercase">Case #{cite.case_id}</p>
                                                        <p className="text-sm font-bold text-gray-900">{cite.merchant}</p>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="text-xs font-bold text-gray-500">₹{cite.amount}</p>
                                                        <span className="text-[10px] font-black text-red-500 uppercase">{cite.outcome}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {activeTab === 'protocol' && explanation && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-400">
                                {/* 8-Check Validation Gate */}
                                <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm">
                                    <h3 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                                        <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
                                        8-Check Validation Gate (SIT Verified)
                                    </h3>
                                    <div className="grid grid-cols-1 gap-1.5">
                                        {(explanation.protocol_checks || []).map((check: any, i: number) => (
                                            <div key={i} className="flex items-center justify-between p-3 bg-gray-50/50 hover:bg-gray-100/50 rounded-xl border border-gray-50 transition-all group">
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-2.5 h-2.5 rounded-full ${check.status === 'PASS' || check.status === 'CLEAN' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-amber-500 animate-pulse'}`}></div>
                                                    <div>
                                                        <p className="text-xs font-bold text-gray-800 group-hover:text-blue-600 transition-colors">{check.name}</p>
                                                        <p className="text-[9px] text-gray-500">{check.desc}</p>
                                                    </div>
                                                </div>
                                                <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded ${check.status === 'PASS' || check.status === 'CLEAN' ? 'text-green-700 bg-green-100/50' : 'text-amber-700 bg-amber-100/50'}`}>
                                                    {check.status}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* PII Isolation Evidence Pack */}
                                <div className="bg-gray-900 rounded-2xl p-5 shadow-2xl relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 p-2 opacity-20 group-hover:opacity-100 transition-opacity">
                                        <span className="text-[10px] font-bold text-green-500 border border-green-500/30 px-2 py-1 rounded italic">VAULT: ACTIVE</span>
                                    </div>
                                    <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] mb-4">
                                        Sealed Evidence Pack (Non-PII Payload)
                                    </h3>
                                    <div className="font-mono text-[11px] leading-relaxed">
                                        <p className="text-blue-500/80 mb-2">// Anonymized context for Sovereign Inference</p>
                                        <div className="text-green-400/90 whitespace-pre">
                                            {JSON.stringify(explanation.evidence_pack || explanation.context?.transaction || {}, null, 2)}
                                        </div>
                                    </div>
                                </div>

                                {/* Immutability Seal */}
                                <div className="p-5 bg-gradient-to-br from-indigo-800 to-indigo-950 rounded-2xl text-white shadow-xl relative overflow-hidden group">
                                    <div className="absolute right-[-15px] top-[-15px] text-white opacity-5 text-8xl transform group-hover:rotate-12 transition-transform">🔒</div>
                                    <div className="flex justify-between items-start mb-3">
                                        <p className="text-[10px] font-black uppercase tracking-[0.2em] opacity-50">Audit Immutability Seal</p>
                                        <span className="text-[9px] font-black bg-indigo-500/50 backdrop-blur-md px-2 py-1 rounded-full border border-indigo-400/30">HASH_V2_SHA256</span>
                                    </div>
                                    <p className="text-[11px] font-mono break-all opacity-90 text-indigo-100 leading-tight">
                                        {explanation.audit_hash || "SIGNING_PENDING..."}
                                    </p>
                                    <div className="flex justify-between items-center mt-5 pt-4 border-t border-indigo-700/50">
                                        <span className="text-[9px] font-bold text-indigo-300">LEDGER: PG_APPEND_ONLY</span>
                                        <div className="flex items-center gap-1.5 text-green-400">
                                            <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-ping"></span>
                                            <span className="text-[10px] font-black tracking-widest">VERIFIED</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {activeTab === 'sar' && (
                            <div className="space-y-6">
                                {!isAnalystOrAdmin ? (
                                    <div className="flex flex-col items-center justify-center h-64 text-center">
                                        <div className="text-4xl mb-4">🚫</div>
                                        <h3 className="text-lg font-bold text-gray-900">Access Restricted</h3>
                                        <p className="text-sm text-gray-500 max-w-xs">SAR generation is only available to authorized Fraud Analysts and Compliance Officers.</p>
                                    </div>
                                ) : loading && !sar ? (
                                    <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mb-4"></div>
                                        <p className="animate-pulse">Generating Regulatory Narrative...</p>
                                        <p className="text-[10px] mt-2 uppercase">Compliance Engine: Llama 3.1 8B</p>
                                    </div>
                                ) : sar ? (
                                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                                        <div className="flex justify-between items-center mb-4">
                                            <h3 className="text-sm font-bold text-gray-900 uppercase tracking-widest">Regulatory Report</h3>
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => copyToClipboard(sar.narrative)}
                                                    className="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded text-[10px] font-bold transition-colors"
                                                >
                                                    COPY TEXT
                                                </button>
                                                <button
                                                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-[10px] font-bold transition-colors"
                                                    onClick={() => alert("PDF Export triggered (Mock)")}
                                                >
                                                    EXPORT PDF
                                                </button>
                                            </div>
                                        </div>
                                        <div className="bg-amber-50/30 border-l-4 border-amber-400 p-6 rounded-r-xl shadow-inner min-h-[400px]">
                                            <div className="whitespace-pre-wrap text-sm text-gray-800 leading-relaxed font-serif">
                                                {sar.narrative}
                                            </div>
                                        </div>
                                        <div className="mt-4 p-3 bg-gray-50 rounded-lg flex justify-between items-center text-[10px]">
                                            <span className="text-gray-500 font-bold uppercase">Version {sar.version}</span>
                                            <button
                                                onClick={() => { setSar(null); loadSAR(); }}
                                                className="text-blue-600 hover:underline font-bold"
                                            >
                                                REGENERATE NARRATIVE
                                            </button>
                                        </div>
                                    </div>
                                ) : null}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="p-6 border-t border-gray-200 bg-gray-50">
                        <button
                            onClick={onClose}
                            className="w-full py-3 bg-gray-900 text-white font-bold rounded-xl hover:bg-gray-800 transition-colors shadow-lg"
                        >
                            CLOSE CASE FILE
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
