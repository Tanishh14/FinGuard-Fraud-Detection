import { useState, useEffect } from 'react'
import { fetchTransactions, appealTransaction } from '../api/transactions.api'

interface Transaction {
    id: number
    merchant: string
    amount: number
    status: string
    final_risk_score: number
    timestamp: string
    is_appealed?: boolean
}

export default function UserTransactionHistory({ userId }: { userId?: number }) {
    const [transactions, setTransactions] = useState<Transaction[]>([])
    const [loading, setLoading] = useState(true)
    const [appealingId, setAppealingId] = useState<number | null>(null)
    const [appealReason, setAppealReason] = useState('')

    const loadTransactions = async () => {
        try {
            const allTx = await fetchTransactions()
            const userTx = userId
                ? allTx.filter((t: any) => t.user_id === userId)
                : allTx

            setTransactions(userTx.sort((a: any, b: any) =>
                new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
            ).slice(0, 8))
        } catch (err) {
            console.error("Failed to fetch history:", err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadTransactions()
    }, [userId])

    const handleAppeal = async (txId: number) => {
        if (!appealReason || appealReason.length < 5) {
            alert("Please provide a reason (at least 5 characters)")
            return
        }
        try {
            await appealTransaction(txId, { reason: appealReason, urgency: 'MEDIUM' })
            setAppealingId(null)
            setAppealReason('')
            loadTransactions()
        } catch (err) {
            console.error("Appeal failed:", err)
            alert("Failed to submit review request.")
        }
    }

    if (loading) {
        return <div className="p-8 text-center animate-pulse text-gray-400 font-bold uppercase text-[10px] tracking-widest">Loading Transaction History...</div>
    }

    return (
        <div className="bg-white rounded-3xl shadow-xl border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
                <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest">Recent Activity</h3>
                <button onClick={loadTransactions} className="text-[10px] font-black text-blue-600 uppercase hover:underline">Refresh</button>
            </div>
            <div className="divide-y divide-gray-50">
                {transactions.length > 0 ? transactions.map((tx) => (
                    <div key={tx.id} className="group transition-all">
                        <div className="p-4 hover:bg-gray-50 transition-colors flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className={`w-10 h-10 rounded-2xl flex items-center justify-center font-bold text-lg ${tx.status === 'APPROVED' ? 'bg-emerald-50 text-emerald-600' :
                                    tx.status === 'BLOCKED' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
                                    }`}>
                                    {tx.merchant[0].toUpperCase()}
                                </div>
                                <div>
                                    <p className="text-sm font-black text-gray-800 tracking-tight">{tx.merchant}</p>
                                    <p className="text-[10px] font-bold text-gray-400 uppercase">{new Date(tx.timestamp).toLocaleDateString()}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <div className="text-right">
                                    <p className="text-sm font-black text-gray-900">₹{tx.amount.toLocaleString()}</p>
                                    <p className={`text-[9px] font-black uppercase tracking-tighter ${tx.status === 'APPROVED' ? 'text-emerald-500' :
                                        tx.status === 'BLOCKED' ? 'text-red-500' : 'text-amber-500'
                                        }`}>
                                        {tx.status}
                                    </p>
                                </div>
                                {tx.status === 'BLOCKED' && !tx.is_appealed && (
                                    <button
                                        onClick={() => setAppealingId(appealingId === tx.id ? null : tx.id)}
                                        className="px-3 py-1 bg-red-50 text-red-600 border border-red-200 rounded-lg text-[10px] font-black uppercase tracking-tighter hover:bg-red-100 transition-colors"
                                    >
                                        Review
                                    </button>
                                )}
                                {tx.status === 'UNDER_REVIEW' && (
                                    <span className="px-2 py-1 bg-orange-50 text-orange-600 rounded-lg text-[9px] font-black uppercase border border-orange-100">Pending Review</span>
                                )}
                            </div>
                        </div>

                        {appealingId === tx.id && (
                            <div className="p-4 bg-red-50/50 border-t border-red-100 animate-in slide-in-from-top duration-300">
                                <p className="text-[10px] font-black uppercase text-red-800 mb-2">Request Manual Review</p>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        placeholder="Reason for review..."
                                        className="flex-1 bg-white border border-red-200 rounded-lg px-3 py-2 text-xs font-bold outline-none focus:ring-1 focus:ring-red-400"
                                        value={appealReason}
                                        onChange={(e) => setAppealReason(e.target.value)}
                                    />
                                    <button
                                        onClick={() => handleAppeal(tx.id)}
                                        className="px-4 py-2 bg-red-600 text-white rounded-lg text-[10px] font-black uppercase tracking-widest hover:bg-red-700 transition-all"
                                    >
                                        Submit
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                )) : (
                    <div className="p-10 text-center text-gray-300 font-bold uppercase text-[10px] tracking-widest">
                        No Recent Transactions found
                    </div>
                )}
            </div>
        </div>
    )
}
