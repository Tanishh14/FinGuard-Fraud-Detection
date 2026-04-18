import { useState, useEffect } from 'react'

interface PushVerifyModalProps {
    txAmount: number
    merchant: string
    riskLabels?: string[]
    onVerify: () => Promise<void>
    onCancel: () => void
}

export default function PushVerifyModal({ txAmount, merchant, riskLabels, onVerify, onCancel }: PushVerifyModalProps) {
    const [loading, setLoading] = useState(false)
    const [success, setSuccess] = useState(false)

    const handleApprove = async () => {
        setLoading(true)
        try {
            await onVerify()
            setSuccess(true)
            setTimeout(onCancel, 2000)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-6 animate-in fade-in duration-300">
            <div className="bg-white rounded-[40px] shadow-2xl w-full max-w-sm overflow-hidden animate-in slide-in-from-bottom-12 duration-500">
                <div className="bg-blue-600 p-8 text-white text-center relative">
                    <div className="w-20 h-20 bg-white/20 rounded-3xl mx-auto mb-4 flex items-center justify-center text-4xl animate-bounce">
                        📱
                    </div>
                    <h2 className="text-xl font-black uppercase tracking-widest">Verify Payment</h2>
                    <p className="text-blue-100 text-xs font-bold mt-2 uppercase tracking-tighter opacity-80">Sent to your trusted device</p>
                </div>

                <div className="p-8">
                    <div className="text-center mb-8">
                        <p className="text-gray-400 text-[10px] font-black uppercase tracking-widest mb-1">Authorizing Amount</p>
                        <h3 className="text-4xl font-black text-gray-900">₹{txAmount.toLocaleString('en-IN')}</h3>
                        <p className="text-gray-500 font-bold text-sm mt-1 mb-4">at {merchant}</p>

                        {riskLabels && riskLabels.length > 0 && (
                            <div className="flex flex-wrap justify-center gap-2 mb-2 p-3 bg-red-50 rounded-2xl border border-red-100">
                                <p className="w-full text-[8px] font-black text-red-400 uppercase tracking-widest mb-1">Risk Factors Detected</p>
                                {riskLabels.map((label, idx) => (
                                    <span key={idx} className="px-2 py-0.5 bg-white border border-red-200 rounded-lg text-[9px] font-black text-red-600 uppercase tracking-tight">
                                        {label}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="space-y-4">
                        {!success ? (
                            <>
                                <button
                                    onClick={handleApprove}
                                    disabled={loading}
                                    className="w-full py-5 bg-blue-600 hover:bg-blue-700 text-white rounded-3xl font-black text-lg transition-all shadow-xl shadow-blue-100 active:scale-95 flex items-center justify-center gap-3"
                                >
                                    {loading ? (
                                        <div className="w-6 h-6 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
                                    ) : (
                                        "Yes, It's Me"
                                    )}
                                </button>
                                <button
                                    onClick={onCancel}
                                    disabled={loading}
                                    className="w-full py-4 text-gray-400 font-bold text-sm hover:text-red-500 transition-colors uppercase tracking-widest"
                                >
                                    No, Decline This
                                </button>
                            </>
                        ) : (
                            <div className="text-center py-4 bg-green-50 rounded-3xl border border-green-100 animate-in zoom-in duration-300">
                                <span className="text-4xl">✅</span>
                                <p className="text-green-700 font-black uppercase tracking-widest text-xs mt-2">Verified Successfully</p>
                            </div>
                        )}
                    </div>

                    <div className="mt-8 pt-6 border-t border-gray-100 flex items-center justify-center gap-2 opacity-30 grayscale">
                        <span className="text-xl">🏦</span>
                        <span className="text-[10px] font-black uppercase tracking-widest text-gray-900">FinGuard Secure Link</span>
                    </div>
                </div>
            </div>
        </div>
    )
}
