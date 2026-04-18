import { useState, useEffect } from 'react'

interface OTPVerificationModalProps {
    isOpen: boolean
    onClose: () => void
    onVerify: (otp: string) => Promise<void>
    email: string
    purpose: string
    loading: boolean
    error?: string
}

export default function OTPVerificationModal({
    isOpen,
    onClose,
    onVerify,
    email,
    purpose,
    loading,
    error
}: OTPVerificationModalProps) {
    const [otp, setOtp] = useState(['', '', '', '', '', ''])

    if (!isOpen) return null

    const handleChange = (index: number, value: string) => {
        if (value.length > 1) value = value.slice(-1)
        if (!/^\d*$/.test(value)) return

        const newOtp = [...otp]
        newOtp[index] = value
        setOtp(newOtp)

        // Auto-focus next input
        if (value && index < 5) {
            const nextInput = document.getElementById(`otp-${index + 1}`)
            nextInput?.focus()
        }
    }

    const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
        if (e.key === 'Backspace' && !otp[index] && index > 0) {
            const prevInput = document.getElementById(`otp-${index - 1}`)
            prevInput?.focus()
        }
        if (e.key === 'Enter' && otp.every(v => v)) {
            onVerify(otp.join(''))
        }
    }

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="w-full max-w-sm bg-white rounded-3xl shadow-2xl overflow-hidden border border-gray-100 animate-in zoom-in-95 duration-300">
                <div className="p-8 text-center">
                    <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6 text-2xl">
                        📧
                    </div>

                    <h2 className="text-2xl font-black text-gray-900 mb-2 uppercase tracking-tight italic">Verify {purpose}</h2>
                    <p className="text-gray-500 text-sm mb-8 leading-relaxed">
                        We've sent a 6-digit verification code to <br />
                        <span className="font-bold text-gray-900">{email}</span>
                    </p>

                    {error && (
                        <div className="mb-6 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl font-bold italic animate-shake">
                            ⚠️ {error}
                        </div>
                    )}

                    <div className="flex justify-center gap-2 mb-8">
                        {otp.map((digit, i) => (
                            <input
                                key={i}
                                id={`otp-${i}`}
                                type="text"
                                maxLength={1}
                                value={digit}
                                onChange={(e) => handleChange(i, e.target.value)}
                                onKeyDown={(e) => handleKeyDown(i, e)}
                                disabled={loading}
                                className="w-12 h-14 text-center text-xl font-black bg-gray-50 border-2 border-gray-100 rounded-xl focus:border-blue-600 focus:bg-white focus:outline-none transition-all duration-200 disabled:opacity-50"
                            />
                        ))}
                    </div>

                    <button
                        onClick={() => onVerify(otp.join(''))}
                        disabled={loading || otp.some(v => !v)}
                        className="btn-primary w-full py-4 text-sm font-black uppercase tracking-widest italic disabled:opacity-50 disabled:cursor-not-allowed group"
                    >
                        {loading ? (
                            <span className="flex items-center justify-center gap-2">
                                <span className="w-4 h-4 border-2 border-transparent border-t-white rounded-full animate-spin"></span>
                                Verifying...
                            </span>
                        ) : (
                            <span className="flex items-center justify-center gap-2">
                                Verify & Continue <span className="group-hover:translate-x-1 transition-transform">→</span>
                            </span>
                        )}
                    </button>

                    <button
                        onClick={onClose}
                        disabled={loading}
                        className="mt-6 text-xs font-black text-gray-400 hover:text-gray-600 uppercase tracking-widest transition-colors disabled:opacity-30"
                    >
                        Cancel Request
                    </button>
                </div>

                <div className="px-8 py-4 bg-gray-50 border-t border-gray-100 text-[10px] text-gray-400 font-bold uppercase tracking-tighter text-center">
                    🛡️ FinGuard Bank-Grade Security Protocol
                </div>
            </div>
        </div>
    )
}
