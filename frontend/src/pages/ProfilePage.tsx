import { useState, useEffect } from 'react'
import { useAuthStore } from '../auth/auth.store'
import { toggle2faApi, verifyAppealOtpApi } from '../api/auth.api'
import { sendTransaction, fetchTransactions, appealTransaction } from '../api/transactions.api'
import UserLayout from '../layouts/UserLayout'
import OTPVerificationModal from '../components/OTPVerificationModal'

export default function ProfilePage() {
    const { role, username, email, user_id, is_2fa_enabled, set2faEnabled } = useAuthStore()
    const [loading, setLoading] = useState(false)

    // Transaction State
    const [amount, setAmount] = useState('')
    const [recipient, setRecipient] = useState('')
    const [txLoading, setTxLoading] = useState(false)
    const [txResult, setTxResult] = useState<any>(null)
    const [history, setHistory] = useState<any[]>([])

    // Appeal State
    const [showAppealForm, setShowAppealForm] = useState(false)
    const [appealReason, setAppealReason] = useState('')
    const [appealing, setAppealing] = useState(false)
    const [showAppealOtp, setShowAppealOtp] = useState(false)
    const [appealOtpError, setAppealOtpError] = useState('')
    const [appealOtpLoading, setAppealOtpLoading] = useState(false)

    useEffect(() => {
        loadHistory()
        // Extract email from profile if possible, or just use auth store
    }, [])

    const userEmail = email || "" // Use email from store


    const loadHistory = async () => {
        try {
            const data = await fetchTransactions()
            setHistory(data)
        } catch (e) {
            console.error(e)
        }
    }

    const handleToggle2fa = async () => {
        setLoading(true)
        try {
            const res = await toggle2faApi()
            set2faEnabled(res.is_2fa_enabled)
        } catch (err: any) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const handleSimulate = async (e: React.FormEvent) => {
        e.preventDefault()
        setTxLoading(true)
        setTxResult(null)
        setShowAppealForm(false)
        try {
            const payload = {
                user_id,
                recipient_name: recipient || 'Unknown Recipient',
                merchant: recipient || 'Test Merchant',
                amount: parseFloat(amount),
                device_id: 'browser-simulated',
                ip_address: '127.0.0.1',
                location: 'Mumbai, India',
                currency: 'INR'
            }
            const res = await sendTransaction(payload)
            setTxResult(res)
            loadHistory()
        } catch (err: any) {
            setTxResult({ error: err.response?.data?.detail || 'Transaction Failed' })
        } finally {
            setTxLoading(false)
        }
    }

    const handleAppeal = async () => {
        if (!txResult?.id) return
        setAppealing(true)
        try {
            await appealTransaction(txResult.id, { reason: appealReason, urgency: 'HIGH' })
            setShowAppealOtp(true)
        } catch (err: any) {
            alert(`❌ Failed to request appeal: ${err.response?.data?.detail}`)
        } finally {
            setAppealing(false)
        }
    }

    const handleVerifyAppealOtp = async (otpCode: string) => {
        setAppealOtpError('')
        setAppealOtpLoading(true)
        try {
            await verifyAppealOtpApi(userEmail, otpCode)
            setTxResult({ ...txResult, status: 'UNDER_REVIEW', is_appealed: true })
            setShowAppealForm(false)
            setShowAppealOtp(false)
            alert("✅ Review Request Submitted: An admin will review your transaction shortly.")
            loadHistory()
        } catch (err: any) {
            setAppealOtpError(err.response?.data?.detail || 'Verification failed. Please try again.')
        } finally {
            setAppealOtpLoading(false)
        }
    }

    return (
        <UserLayout>
            <div className="max-w-7xl mx-auto py-8 px-4 bg-gray-50 min-h-screen">

                {/* STATUS CARD - Shows after transaction */}
                {txResult && (
                    <div className="mb-8">
                        {/* Security Alert Banner if Blocked or Flagged */}
                        {(txResult.decision === 'BLOCKED' || txResult.decision === 'FLAGGED' || txResult.decision === 'REVIEW_NEEDED' || txResult.decision === 'REVIEW') && (
                            <div className={`border-l-4 p-4 mb-6 rounded-r shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                                txResult.decision === 'BLOCKED' ? 'bg-red-50 border-red-400' : 'bg-orange-50 border-orange-400'
                            }`}>
                                <div className="flex items-start gap-4">
                                    <div className="text-2xl">{txResult.decision === 'BLOCKED' ? '🚫' : '⚠️'}</div>
                                    <div>
                                        <h3 className={`font-bold uppercase text-sm tracking-wider ${
                                            txResult.decision === 'BLOCKED' ? 'text-red-800' : 'text-orange-800'
                                        }`}>
                                            {txResult.decision === 'BLOCKED' ? 'Security Protocol: Transaction Declined' : 'Security Check: Review Required'}
                                        </h3>
                                        <p className={`text-xs mt-1 ${
                                            txResult.decision === 'BLOCKED' ? 'text-red-700' : 'text-orange-700'
                                        }`}>
                                            {txResult.decision === 'BLOCKED' 
                                                ? 'This transaction was automatically blocked for your protection.' 
                                                : 'Unusual patterns detected. This transaction is being held temporarily for verification.'
                                            }
                                            {!is_2fa_enabled && <button onClick={handleToggle2fa} className="underline ml-1 font-bold">Enable 2FA Now →</button>}
                                        </p>
                                    </div>
                                </div>
                                {!txResult.is_appealed && txResult.status !== 'UNDER_REVIEW' && (
                                    <button
                                        onClick={() => setShowAppealForm(true)}
                                        className="px-4 py-2 bg-white border border-orange-300 text-orange-700 text-xs font-bold uppercase rounded-lg hover:bg-orange-100 transition-colors shadow-sm whitespace-nowrap"
                                    >
                                        📝 Request Review
                                    </button>
                                )}
                                {(txResult.is_appealed || txResult.status === 'UNDER_REVIEW') && (
                                    <span className="px-4 py-2 bg-orange-200 text-orange-800 text-xs font-bold uppercase rounded-lg">
                                        ⏳ Under Review
                                    </span>
                                )}
                            </div>
                        )}

                        {/* Appeal Form */}
                        {showAppealForm && (
                            <div className="mb-6 p-6 bg-white rounded-xl shadow-lg border border-orange-200">
                                <h4 className="font-bold text-gray-900 mb-2">Request Transaction Review</h4>
                                <p className="text-sm text-gray-500 mb-4">Please explain why this transaction should be approved (e.g., emergency medical payment).</p>
                                <textarea
                                    className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none mb-4"
                                    rows={3}
                                    placeholder="e.g. This was an emergency medical payment to a hospital..."
                                    value={appealReason}
                                    onChange={e => setAppealReason(e.target.value)}
                                ></textarea>
                                <div className="flex justify-end gap-3">
                                    <button
                                        onClick={() => setShowAppealForm(false)}
                                        className="px-4 py-2 text-gray-500 text-sm font-bold hover:text-gray-700"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleAppeal}
                                        disabled={appealing || !appealReason}
                                        className="px-6 py-2 bg-blue-600 text-white text-sm font-bold rounded-lg hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        {appealing ? 'Submitting...' : 'Submit Appeal'}
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Detailed Diagnostic Card */}
                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
                            <div className="flex justify-between items-start mb-8">
                                <div className="flex items-center gap-4">
                                    <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl ${
                                        txResult.decision === 'APPROVED' ? 'bg-green-100 text-green-600' : 
                                        (txResult.decision === 'FLAGGED' || txResult.decision === 'REVIEW_NEEDED') ? 'bg-orange-100 text-orange-600' : 
                                        'bg-red-100 text-red-600'
                                    }`}>
                                        {txResult.decision === 'APPROVED' ? '✓' : (txResult.decision === 'FLAGGED' || txResult.decision === 'REVIEW_NEEDED') ? '⚠️' : '✕'}
                                    </div>
                                    <div>
                                        <h2 className={`text-xl font-bold ${
                                            txResult.decision === 'APPROVED' ? 'text-green-700' : 
                                            (txResult.decision === 'FLAGGED' || txResult.decision === 'REVIEW_NEEDED') ? 'text-orange-700' : 
                                            'text-red-700'
                                        }`}>
                                            Transaction {
                                                txResult.decision === 'APPROVED' ? 'Authorized' : 
                                                (txResult.decision === 'FLAGGED' || txResult.decision === 'REVIEW_NEEDED') ? 'Held for Review' : 
                                                'Declined'
                                            }
                                        </h2>
                                        <p className="text-xs text-gray-400 uppercase tracking-widest mt-1">
                                            ID: #{txResult.id} • {new Date().toLocaleString()}
                                        </p>
                                    </div>
                                </div>
                                <span className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest border ${
                                    txResult.decision === 'APPROVED' ? 'bg-green-50 text-green-700 border-green-200' : 
                                    (txResult.decision === 'FLAGGED' || txResult.decision === 'REVIEW_NEEDED') ? 'bg-orange-50 text-orange-700 border-orange-200' : 
                                    'bg-red-50 text-red-700 border-red-200'
                                }`}>
                                    {txResult.decision}
                                </span>
                            </div>

                            {role === 'admin' && (
                                <>
                                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4">Admin/Analyst Diagnostic Report</h4>
                                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                                        {[
                                            { label: 'Anomaly Engine', score: txResult.ae_score || 0 },
                                            { label: 'Graph Neural Net', score: txResult.gnn_score || 0 },
                                            { label: 'Merchant Risk', score: txResult.rule_score || 0 },
                                            { label: 'User Behavior', score: txResult.if_score || 0 }
                                        ].map((item, idx) => (
                                            <div key={idx}>
                                                <div className="flex justify-between text-[10px] font-bold text-gray-400 uppercase mb-2">
                                                    {item.label}
                                                    <span className={item.score > 0.5 ? 'text-red-500' : 'text-green-500'}>{(item.score * 100).toFixed(0)}%</span>
                                                </div>
                                                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                                    <div className="h-full rounded-full" style={{ width: `${Math.max(5, item.score * 100)}%`, backgroundColor: item.score > 0.5 ? '#ef4444' : '#10b981' }}></div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="mt-6 flex items-center gap-2">
                                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Calculated Risk:</span>
                                        <span className="px-2 py-1 bg-gray-100 rounded text-xs font-mono font-bold">{((txResult.risk_score || 0) * 100).toFixed(1)}%</span>
                                    </div>
                                </>
                            )}
                            {role !== 'admin' && (
                                <div className="bg-blue-50 p-4 rounded-xl border border-blue-100 italic text-blue-700 text-xs text-center font-medium">
                                    🛡️ Your transaction was analyzed by our real-time AI safety engine.
                                </div>
                            )}
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
                    {/* TRANSFER FORM */}
                    <div className="lg:col-span-1">
                        <div className="bg-white rounded-3xl shadow-xl shadow-blue-900/5 p-8 relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-blue-600 to-indigo-600"></div>

                            <h3 className="text-xl font-black italic text-gray-900 mb-8 uppercase tracking-tighter">Initiate Transfer</h3>

                            <form onSubmit={handleSimulate} className="space-y-6">
                                <div>
                                    <label className="text-[10px] font-black uppercase text-gray-400 tracking-widest mb-1.5 block">Recipient Account / Name</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. Sarah Jenkins (SA-10293)"
                                        value={recipient}
                                        onChange={e => setRecipient(e.target.value)}
                                        className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all placeholder:font-normal placeholder:text-gray-400"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="text-[10px] font-black uppercase text-gray-400 tracking-widest mb-1.5 block">Amount (INR)</label>
                                    <div className="relative">
                                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold">₹</span>
                                        <input
                                            type="number"
                                            placeholder="0.00"
                                            value={amount}
                                            onChange={e => setAmount(e.target.value)}
                                            className="w-full bg-gray-50 border border-gray-200 rounded-xl pl-8 pr-4 py-3 text-lg font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all placeholder:font-normal placeholder:text-gray-400"
                                            required
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="text-[10px] font-black uppercase text-gray-400 tracking-widest mb-1.5 block">Merchant ID</label>
                                    <input
                                        type="text"
                                        placeholder="MERCH-8821"
                                        className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all placeholder:font-normal placeholder:text-gray-400 uppercase"
                                    />
                                </div>

                                <button
                                    type="submit"
                                    disabled={txLoading}
                                    className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-black uppercase text-xs tracking-widest transition-all shadow-lg shadow-blue-200 transform hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center gap-2"
                                >
                                    {txLoading ? 'Processing...' : 'Send Authorized Payment →'}
                                </button>
                            </form>
                        </div>
                    </div>

                    {/* RECENT ACTIVITY */}
                    <div className="lg:col-span-2">
                        <div className="bg-white rounded-3xl shadow-sm border border-gray-200 p-8 min-h-[500px]">
                            <div className="flex items-center justify-between mb-8">
                                <h3 className="text-sm font-black text-gray-400 uppercase tracking-widest">Recent Activity</h3>
                                <button onClick={loadHistory} className="text-xs font-bold text-blue-600 hover:text-blue-700">Refresh</button>
                            </div>

                            <div className="space-y-4">
                                {history.length === 0 ? (
                                    <div className="text-center py-20">
                                        <p className="text-sm font-bold text-gray-300 uppercase tracking-widest">No Recent Transactions</p>
                                    </div>
                                ) : (
                                    history.map((tx) => (
                                        <div key={tx.id} className="group border border-transparent hover:border-gray-100 rounded-xl transition-all">
                                            <div className="flex items-center justify-between p-4 hover:bg-gray-50 rounded-xl transition-colors">
                                                <div className="flex items-center gap-4">
                                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold ${
                                                        tx.decision === 'APPROVED' ? 'bg-green-100 text-green-600' : 
                                                        (tx.decision === 'FLAGGED' || tx.decision === 'REVIEW_NEEDED') ? 'bg-orange-100 text-orange-600' :
                                                        'bg-red-100 text-red-600'
                                                    }`}>
                                                        {tx.decision === 'APPROVED' ? '✓' : (tx.decision === 'FLAGGED' || tx.decision === 'REVIEW_NEEDED') ? '⚠️' : '✕'}
                                                    </div>
                                                    <div>
                                                        <h4 className="font-bold text-gray-900 text-sm">{tx.merchant}</h4>
                                                        <p className="text-[10px] text-gray-400 uppercase tracking-wide">{new Date(tx.timestamp).toLocaleDateString()}</p>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-4">
                                                    <div className="text-right">
                                                        <p className="font-mono font-bold text-gray-900">₹{tx.amount.toLocaleString()}</p>
                                                        <div className="flex items-center justify-end gap-1 mt-1">
                                                            <span className={`text-[10px] font-bold uppercase ${
                                                                tx.status === 'UNDER_REVIEW' ? 'text-orange-500' : 
                                                                tx.decision === 'APPROVED' ? 'text-green-500' : 
                                                                (tx.decision === 'FLAGGED' || tx.decision === 'REVIEW_NEEDED') ? 'text-orange-500' :
                                                                'text-red-500'
                                                            }`}>
                                                                {tx.status === 'UNDER_REVIEW' ? 'UNDER REVIEW' : tx.decision || 'PROCESSING'}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    {(tx.decision === 'BLOCKED' || tx.decision === 'REVIEW' || tx.decision === 'FLAGGED' || tx.decision === 'REVIEW_NEEDED') && tx.status !== 'UNDER_REVIEW' && !tx.is_appealed && (
                                                        <button
                                                            onClick={() => {
                                                                setTxResult({ id: tx.id, decision: tx.decision, explanation: 'Historical Transaction', merchant: tx.merchant, amount: tx.amount });
                                                                setShowAppealForm(true);
                                                                window.scrollTo({ top: 0, behavior: 'smooth' });
                                                            }}
                                                            className="px-3 py-1 bg-red-50 text-red-600 border border-red-100 rounded-lg text-[10px] font-black uppercase tracking-tighter hover:bg-red-100"
                                                        >
                                                            Review
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <OTPVerificationModal
                isOpen={showAppealOtp}
                onClose={() => setShowAppealOtp(false)}
                onVerify={handleVerifyAppealOtp}
                email={userEmail}
                purpose=" "
                loading={appealOtpLoading}
                error={appealOtpError}
            />
        </UserLayout>
    )
}
