
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';

export default function LandingPage() {
    const navigate = useNavigate();
    const { user_id, role, is_loading } = useAuth();

    useEffect(() => {
        // If user is already logged in, redirect to their dashboard
        if (!is_loading && user_id && role) {
            if (role === 'admin' || role === 'fraud_analyst') {
                navigate('/dashboard', { replace: true });
            } else if (role === 'auditor') {
                navigate('/dashboard', { replace: true });
            } else if (role === 'user' || role === 'end_user') {
                navigate('/profile', { replace: true });
            }
        }
    }, [user_id, role, is_loading, navigate]);

    // Show loading spinner while checking auth status
    if (is_loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-slate-900">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-white">
            {/* Navigation */}
            <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-800 rounded-xl flex items-center justify-center font-bold text-white text-xl shadow-lg shadow-blue-200">
                        F
                    </div>
                    <span className="text-xl font-bold text-gray-900 tracking-tight">FinGuard AI</span>
                </div>
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate('/login')}
                        className="px-6 py-2.5 text-sm font-bold text-gray-700 hover:text-blue-600 transition-colors"
                    >
                        Log In
                    </button>
                    <button
                        onClick={() => navigate('/register')}
                        className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-bold hover:bg-blue-700 transition-all shadow-lg shadow-blue-200 hover:shadow-blue-300 transform hover:-translate-y-0.5"
                    >
                        Get Started
                    </button>
                </div>
            </nav>

            {/* Hero Section */}
            <main className="max-w-7xl mx-auto px-8 py-20 lg:py-32">
                <div className="grid lg:grid-cols-2 gap-16 items-center">
                    <div className="space-y-8">
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-full text-xs font-bold uppercase tracking-widest border border-blue-100">
                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                            Live Fraud Prevention
                        </div>

                        <h1 className="text-5xl lg:text-7xl font-black text-gray-900 leading-[1.1] tracking-tight">
                            Secure Every <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600">Transaction.</span>
                        </h1>

                        <p className="text-xl text-gray-500 leading-relaxed max-w-lg">
                            Enterprise-grade fraud detection powered by Graph Neural Networks and Real-time Anomaly Detection. Stop threats before they happen.
                        </p>

                        <div className="flex flex-col sm:flex-row gap-4 pt-4">
                            <button
                                onClick={() => navigate('/register')}
                                className="px-8 py-4 bg-gray-900 text-white rounded-2xl font-bold text-lg hover:bg-black transition-all shadow-xl hover:shadow-2xl hover:-translate-y-1 flex items-center justify-center gap-3"
                            >
                                Start Free Trial
                                <span className="text-gray-400">→</span>
                            </button>
                            <button
                                onClick={() => navigate('/login')}
                                className="px-8 py-4 bg-white text-gray-900 border-2 border-gray-100 rounded-2xl font-bold text-lg hover:border-gray-200 hover:bg-gray-50 transition-all flex items-center justify-center"
                            >
                                View Live Demo
                            </button>
                        </div>

                        <div className="pt-8 flex items-center gap-8 text-sm font-bold text-gray-400 uppercase tracking-widest">
                            <span>Trusted by Industry Leaders</span>
                        </div>
                    </div>

                    <div className="relative">
                        {/* Abstract UI Mockup */}
                        <div className="relative z-10 bg-white rounded-3xl shadow-2xl border border-gray-100 p-6 transform rotate-3 hover:rotate-0 transition-transform duration-700">
                            <div className="absolute -inset-4 bg-gradient-to-br from-blue-500 to-purple-500 rounded-[2rem] opacity-20 blur-2xl -z-10"></div>

                            <div className="flex justify-between items-center mb-8 border-b border-gray-100 pb-4">
                                <div className="flex gap-2">
                                    <div className="w-3 h-3 rounded-full bg-red-400"></div>
                                    <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                                    <div className="w-3 h-3 rounded-full bg-green-400"></div>
                                </div>
                                <div className="text-xs font-bold text-gray-400 uppercase">Live Intelligence</div>
                            </div>

                            <div className="space-y-4">
                                {[1, 2, 3].map((_, i) => (
                                    <div key={i} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-100">
                                        <div className="flex items-center gap-4">
                                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg ${i === 0 ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}`}>
                                                {i === 0 ? '⚠️' : '✅'}
                                            </div>
                                            <div>
                                                <div className="h-2 w-24 bg-gray-200 rounded mb-2"></div>
                                                <div className="h-2 w-16 bg-gray-100 rounded"></div>
                                            </div>
                                        </div>
                                        <div className={`px-3 py-1 rounded-lg text-xs font-bold ${i === 0 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                                            {i === 0 ? 'BLOCKED' : 'APPROVED'}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
