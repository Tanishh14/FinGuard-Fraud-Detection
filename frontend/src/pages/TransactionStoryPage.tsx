import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AdminLayout from '../layouts/AdminLayout';
import { useAuthStore } from '../auth/auth.store';

export default function TransactionStoryPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const token = useAuthStore(state => state.token);

    useEffect(() => {
        const fetchStory = async () => {
            try {
                const headers: any = { 'Content-Type': 'application/json' }
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`
                }
                
                const response = await fetch(`http://localhost:8000/forensics/story/${id}`, {
                    credentials: 'include',
                    headers
                });

                if (!response.ok) {
                    const errorJson = await response.json();
                    console.error("Forensics API error:", errorJson);
                    setData(null);
                    return;
                }

                const json = await response.json();
                setData(json);
            } catch (err) {
                console.error("Failed to fetch story:", err);
                setData(null);
            } finally {
                setLoading(false);
            }
        };
        fetchStory();
    }, [id, token]);

    if (loading) return <AdminLayout><div className="p-20 text-center animate-pulse">Reconstructing timeline...</div></AdminLayout>;
    if (!data || !data.transaction) return <AdminLayout><div className="p-20 text-center text-red-500">Transaction Story Not Available</div></AdminLayout>;

    return (
        <AdminLayout>
            <div className="flex items-center gap-4 mb-8">
                <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-full">⬅️</button>
                <h1 className="text-3xl font-bold text-gray-900">🔍 Transaction Story: #{id}</h1>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Left column: Summary & User Context */}
                <div className="space-y-6">
                    <div className="card p-6">
                        <h3 className="font-bold text-gray-900 mb-4">Target Transaction</h3>
                        <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500">Amount</span>
                                <span className="font-mono font-bold">₹{(data.transaction?.amount || 0).toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500">Merchant</span>
                                <span className="font-semibold text-blue-600">{data.transaction?.merchant}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-500">Location</span>
                                <span>{data.transaction?.location}</span>
                            </div>
                            <div className="flex justify-between text-sm pt-2 border-t border-gray-50">
                                <span className="text-gray-500">Risk Score</span>
                                <span className={`font-bold ${(data.transaction?.risk_score || 0) > 0.7 ? 'text-red-500' : 'text-orange-500'}`}>
                                    {Math.round((data.transaction?.risk_score || 0) * 100)}%
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="card p-6 border-l-4 border-blue-500">
                        <h3 className="font-bold text-gray-900 mb-4">User Behavioral Profile</h3>
                        <div className="space-y-3 text-sm">
                            <p className="font-bold text-gray-700">{data.user_context?.username || 'Unknown User'}</p>
                            <p className="text-xs text-gray-400">{data.user_context?.email || ''}</p>
                            <div className="pt-2">
                                <p className="text-xs text-gray-500 mb-1">Average Spend</p>
                                <p className="text-lg font-bold">₹{(data.user_context?.avg_spend || 0).toFixed(2)}</p>
                            </div>
                            <div>
                                <p className="text-xs text-gray-500 mb-1">Total Transactions</p>
                                <p className="text-lg font-bold">{data.user_context?.total_tx || 0}</p>
                            </div>
                        </div>
                    </div>

                    <div className={`card p-6 border-l-4 ${data.forensics?.network_risk?.risk_level === 'HIGH' ? 'border-red-500 bg-red-50' : 'border-green-500'}`}>
                        <h3 className="font-bold text-gray-900 mb-4">Infrastructure Linking</h3>
                        <div className="space-y-2">
                            <p className="text-xs leading-relaxed">
                                Found <strong>{data.forensics?.network_risk?.shared_infrastructure_users || 0}</strong> other users sharing this Device/IP combination.
                            </p>
                            <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase ${data.forensics?.network_risk?.risk_level === 'HIGH' ? 'bg-red-200 text-red-800' : 'bg-green-200 text-green-800'}`}>
                                {data.forensics?.network_risk?.risk_level || 'UNKNOWN'} NETWORK RISK
                            </span>
                        </div>
                    </div>
                </div>

                {/* Right column: Timeline & Explanations */}
                <div className="lg:col-span-3 space-y-8">
                    <div className="card p-8 bg-slate-900 text-white border-none">
                        <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                            📜 Transaction Life-cycle
                        </h3>
                        <div className="relative border-l-2 border-slate-700 ml-4 py-4 space-y-12">
                            {/* Past Events */}
                            {data.forensics?.historical_timeline?.map((h: any, idx: number) => (
                                <div key={h.id || idx} className="relative pl-10">
                                    <div className="absolute left-[-9px] top-1 w-4 h-4 rounded-full bg-slate-700 border-2 border-slate-900"></div>
                                    <div className="text-xs text-slate-500 mb-1">{h.timestamp ? new Date(h.timestamp).toLocaleString() : 'N/A'}</div>
                                    <div className="flex items-center gap-4">
                                        <span className="font-bold">Prior TXN-{h.id || 'Unknown'}</span>
                                        <span className="text-slate-400">₹{(h.amount || 0).toLocaleString()}</span>
                                        <span className={`px-2 py-0.5 rounded text-[10px] ${h.status === 'APPROVED' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                                            {h.status || 'UNKNOWN'}
                                        </span>
                                    </div>
                                </div>
                            ))}

                            {/* Current Event */}
                            <div className="relative pl-10">
                                <div className="absolute left-[-11px] top-0 w-5 h-5 rounded-full bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)]"></div>
                                <div className="text-xs text-blue-400 font-bold mb-1">CURRENT INVESTIGATION • {data.transaction?.timestamp ? new Date(data.transaction.timestamp).toLocaleString() : 'N/A'}</div>
                                <div className="p-4 bg-slate-800 rounded-xl border border-slate-700">
                                    <p className="text-lg font-bold mb-2">Automated {data.forensics?.audit_trail?.auto_decision || 'UNKNOWN'}</p>
                                    <p className="text-slate-400 italic text-sm leading-relaxed mb-4">
                                        "{data.forensics?.audit_trail?.explanation || 'No data'}"
                                    </p>
                                    <div className="flex flex-wrap gap-2">
                                        {data.forensics?.audit_trail?.flags?.map((f: string, idx: number) => (
                                            <span key={idx} className="bg-red-900/40 text-red-400 border border-red-800 px-2 py-1 rounded text-[10px] items-center gap-1 flex">
                                                🚨 {f}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-end gap-4">
                        <button className="btn-secondary px-8">Dismiss Case</button>
                        <button className="btn-primary px-8 bg-red-600 hover:bg-red-700 border-red-600">Block User Permanently</button>
                    </div>
                </div>
            </div>
        </AdminLayout>
    );
}
