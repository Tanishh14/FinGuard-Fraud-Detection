import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { reportTransaction, appealTransaction, verifyReportAppealOTP } from '../api/transactions.api'
import OTPVerificationModal from '../components/OTPVerificationModal'
import api from '../api/axios'

export default function ReportAppealPage() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()
    const { email } = useAuth()

    const [transaction, setTransaction] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [reason, setReason] = useState('')
    const [urgency, setUrgency] = useState('MEDIUM')

    const [otpModalOpen, setOtpModalOpen] = useState(false)
    const [otpError, setOtpError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)

    useEffect(() => {
        const fetchTransaction = async () => {
            try {
                // Using the forensics story endpoint as it gives comprehensive info
                const response = await api.get(`/forensics/story/${id}`)
                setTransaction(response.data.transaction)
            } catch (err) {
                console.error("Failed to fetch transaction details:", err)
                setError("Could not load transaction details. It might not exist or you don't have permission.")
            } finally {
                setLoading(false)
            }
        }
        if (id) fetchTransaction()
    }, [id])

    const isBlocked = transaction?.status === 'BLOCKED'
    const isApproved = transaction?.status === 'APPROVED'

    const handleSubmitRequest = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!reason || reason.length < 5) {
            setError("Please provide a more detailed reason (at least 5 characters).")
            return
        }

        setSubmitting(true)
        setError(null)

        try {
            if (isApproved) {
                await reportTransaction(Number(id), { reason, urgency })
            } else if (isBlocked) {
                await appealTransaction(Number(id), { reason, urgency })
            } else {
                setError("This transaction cannot be reported or appealed in its current state.")
                setSubmitting(false)
                return
            }
            setOtpModalOpen(true)
        } catch (err: any) {
            setError(err.response?.data?.detail || "Failed to initiate request. Please try again.")
        } finally {
            setSubmitting(false)
        }
    }

    const handleVerifyOtp = async (otpCode: string) => {
        setSubmitting(true)
        setOtpError(null)
        try {
            await verifyReportAppealOTP({
                email: email || '',
                otp_code: otpCode,
                otp_type: isApproved ? 'report' : 'appeal'
            })
            setOtpModalOpen(false)
            setSuccess(true)
        } catch (err: any) {
            setOtpError(err.response?.data?.detail || "Invalid or expired OTP.")
        } finally {
            setSubmitting(false)
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="animate-pulse flex flex-col items-center">
                    <div className="w-12 h-12 bg-blue-200 rounded-full mb-4"></div>
                    <div className="h-4 w-48 bg-gray-200 rounded"></div>
                </div>
            </div>
        )
    }

    if (success) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
                <div className="max-w-md w-full bg-white rounded-3xl shadow-xl p-8 text-center border border-gray-100">
                    <div className="w-20 h-20 bg-green-50 text-green-500 rounded-full flex items-center justify-center mx-auto mb-6 text-4xl">
                        ✅
                    </div>
                    <h2 className="text-2xl font-black text-gray-900 mb-4 uppercase italic">Request Submitted</h2>
                    <p className="text-gray-500 mb-8 leading-relaxed">
                        Your {isApproved ? 'report' : 'appeal'} for transaction <strong>#{id}</strong> has been successfully submitted.
                        It is now <strong>UNDER REVIEW</strong> by our fraud analysts.
                    </p>
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="btn-primary w-full py-4 text-sm font-black uppercase tracking-widest italic"
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50 p-4 md:p-8">
            <div className="max-w-2xl mx-auto">
                <button
                    onClick={() => navigate(-1)}
                    className="mb-6 flex items-center gap-2 text-gray-400 hover:text-gray-600 font-bold text-sm uppercase tracking-widest transition-colors"
                >
                    ← Back
                </button>

                <div className="bg-white rounded-3xl shadow-xl overflow-hidden border border-gray-100">
                    <div className={`h-2 ${isBlocked ? 'bg-red-500' : 'bg-green-500'}`}></div>

                    <div className="p-8">
                        <header className="mb-8">
                            <h1 className="text-3xl font-black text-gray-900 uppercase italic tracking-tight mb-2">
                                {isApproved ? 'Report Fraudulent Transaction' : 'Appeal Blocked Transaction'}
                            </h1>
                            <p className="text-gray-500 font-medium">
                                Transaction ID: <span className="text-gray-900">#{id}</span>
                            </p>
                        </header>

                        {error && (
                            <div className="mb-8 p-4 bg-red-50 border border-red-100 text-red-600 rounded-2xl text-sm font-bold animate-shake">
                                ⚠️ {error}
                            </div>
                        )}

                        <section className="bg-gray-50 rounded-2xl p-6 mb-8 border border-gray-100">
                            <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4">Transaction Details</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs text-gray-400 font-bold uppercase mb-1">Amount</p>
                                    <p className="text-xl font-black text-gray-900">
                                        {transaction?.currency} {transaction?.amount?.toLocaleString()}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-gray-400 font-bold uppercase mb-1">Merchant</p>
                                    <p className="text-xl font-black text-gray-900">{transaction?.merchant}</p>
                                </div>
                                <div className="col-span-2 pt-2 border-t border-gray-200">
                                    <p className="text-xs text-gray-400 font-bold uppercase mb-1">Status</p>
                                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase ${isBlocked ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'
                                        }`}>
                                        {transaction?.status}
                                    </span>
                                </div>
                            </div>
                        </section>

                        <form onSubmit={handleSubmitRequest} className="space-y-6">
                            <div>
                                <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                                    Why are you {isApproved ? 'reporting' : 'appealing'} this?
                                </label>
                                <textarea
                                    required
                                    rows={4}
                                    value={reason}
                                    onChange={(e) => setReason(e.target.value)}
                                    placeholder={isApproved ? "e.g. I did not make this transaction..." : "e.g. This was an authorized purchase for..."}
                                    className="w-full bg-gray-50 border-2 border-gray-100 rounded-2xl p-4 text-gray-900 font-medium focus:border-blue-600 focus:bg-white focus:outline-none transition-all"
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                                    Urgency Level
                                </label>
                                <div className="grid grid-cols-3 gap-3">
                                    {['LOW', 'MEDIUM', 'HIGH'].map((level) => (
                                        <button
                                            key={level}
                                            type="button"
                                            onClick={() => setUrgency(level)}
                                            className={`py-3 rounded-xl text-xs font-black transition-all ${urgency === level
                                                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-200'
                                                    : 'bg-gray-50 text-gray-400 border border-gray-100 hover:bg-gray-100'
                                                }`}
                                        >
                                            {level}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={submitting}
                                className="btn-primary w-full py-4 text-sm font-black uppercase tracking-widest italic flex items-center justify-center gap-2 group"
                            >
                                {submitting ? 'Processing...' : (
                                    <>
                                        {isApproved ? 'Submit Fraud Report' : 'Submit Appeal'}
                                        <span className="group-hover:translate-x-1 transition-transform">→</span>
                                    </>
                                )}
                            </button>
                        </form>
                    </div>

                    <div className="px-8 py-4 bg-gray-50 border-t border-gray-100 text-[10px] text-gray-400 font-bold uppercase tracking-tighter text-center">
                        🛡️ FinGuard Dispute Resolution Protocol v2.1
                    </div>
                </div>
            </div>

            <OTPVerificationModal
                isOpen={otpModalOpen}
                onClose={() => setOtpModalOpen(false)}
                onVerify={handleVerifyOtp}
                email={email || 'your email'}
                purpose={isApproved ? "Fraud Report" : "Appeal"}
                loading={submitting}
                error={otpError || undefined}
            />
        </div>
    )
}
