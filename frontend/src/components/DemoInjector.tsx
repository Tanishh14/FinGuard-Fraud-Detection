import { useState } from 'react'

interface Scenario {
    id: string
    name: string
    description: string
    icon: string
    payload: any
}

interface DemoInjectorProps {
    onInject: (payload: any) => Promise<void>
}

export default function DemoInjector({ onInject }: DemoInjectorProps) {
    const [isOpen, setIsOpen] = useState(false)
    const [loading, setLoading] = useState<string | null>(null)

    const scenarios: Scenario[] = [
        {
            id: 'phish',
            name: 'The Phish (Large Anomaly)',
            description: 'Mimics a large anomaly after a successful phish.',
            icon: '🎣',
            payload: {
                recipient_name: "Attacker-Safe-Vault",
                merchant: "Global Crypto Exchange",
                merchant_id: "CRYPTO-9921",
                amount: 550000.0 // Very high anomaly
            }
        },
        {
            id: 'ring',
            name: 'The Ring (Network Risk)',
            description: 'Transaction from a known high-risk device cluster.',
            icon: '💍',
            payload: {
                recipient_name: "Money Mule #42",
                merchant: "Local P2P",
                merchant_id: "P2P-RANDOM",
                amount: 2500.0,
                device_id: "DF-RING-NODE-8" // This will trigger GNN logic if configured
            }
        },
        {
            id: 'nocturnal',
            name: 'Nocturnal Bust',
            description: 'High-value transaction at 3:30 AM.',
            icon: '🌙',
            payload: {
                recipient_name: "Urgent Transfer",
                merchant: "Night Vendor",
                merchant_id: "NIGHT-001",
                amount: 8500.0,
                timestamp: new Date(new Date().setHours(3, 30, 0, 0)).toISOString()
            }
        }
    ]

    const handleRun = async (s: Scenario) => {
        setLoading(s.id)
        try {
            await onInject(s.payload)
        } finally {
            setLoading(null)
        }
    }

    return (
        <div className="fixed left-6 bottom-6 z-50">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-14 h-14 bg-indigo-600 text-white rounded-full shadow-2xl flex items-center justify-center text-2xl hover:bg-indigo-700 transition-all hover:rotate-12 transform"
                title="Demo Simulation Mode"
            >
                {isOpen ? '✕' : '🚀'}
            </button>

            {isOpen && (
                <div className="absolute bottom-20 left-0 w-80 bg-white rounded-3xl shadow-2xl border border-gray-100 p-6 animate-in slide-in-from-bottom duration-300">
                    <div className="flex items-center gap-3 mb-4">
                        <span className="text-2xl">⚡</span>
                        <div>
                            <h3 className="text-sm font-black text-gray-900 uppercase tracking-widest leading-none">Simulation Mode</h3>
                            <p className="text-[10px] font-bold text-indigo-500 uppercase mt-1">Hackathon Demo Tools</p>
                        </div>
                    </div>

                    <div className="space-y-3">
                        {scenarios.map(s => (
                            <button
                                key={s.id}
                                onClick={() => handleRun(s)}
                                disabled={!!loading}
                                className="w-full text-left p-4 rounded-2xl border border-gray-100 hover:border-indigo-300 bg-gray-50 hover:bg-indigo-50 transition-all group relative overflow-hidden"
                            >
                                <div className="flex items-center gap-3 relative z-10">
                                    <span className="text-2xl">{s.icon}</span>
                                    <div>
                                        <h4 className="text-xs font-black text-gray-800 uppercase tracking-tight">{s.name}</h4>
                                        <p className="text-[10px] text-gray-500 font-medium leading-tight mt-0.5">{s.description}</p>
                                    </div>
                                </div>
                                {loading === s.id && (
                                    <div className="absolute inset-0 bg-indigo-600/10 flex items-center justify-center">
                                        <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>

                    <div className="mt-4 pt-4 border-t border-gray-100 text-[9px] text-gray-400 font-bold uppercase tracking-widest text-center">
                        FinGuard authoritative demo control
                    </div>
                </div>
            )}
        </div>
    )
}
