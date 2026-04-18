import { useState } from 'react';
import { useAuthStore } from '../auth/auth.store';

export default function DemoSelector() {
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const token = useAuthStore(state => state.token);

    const stories = [
        { id: 'mumbai_ring', name: 'The Mumbai ATM Ring', icon: '🏧', description: 'Multi-account device sharing and geographic jumps.' },
        { id: 'whale_drain', name: 'The Crypto Whale Drain', icon: '🐳', description: 'High-velocity bulk crypto purchases from a new device.' },
        { id: 'merchant_collusion', name: 'Merchant Collusion', icon: '🤝', description: 'Circular payments between a user and a high-risk merchant.' }
    ];

    const triggerStory = async (storyId: string) => {
        setLoading(true);
        setMessage('');
        try {
            const headers: any = { 'Content-Type': 'application/json' }
            if (token) {
                headers['Authorization'] = `Bearer ${token}`
            }
            
            const response = await fetch(`http://localhost:8000/simulation/start-story/${storyId}`, {
                method: 'POST',
                credentials: 'include',
                headers
            });
            const data = await response.json();
            setMessage(data.message || 'Story triggered successfully.');
            // Refresh the page after 2 seconds to show new data
            setTimeout(() => window.location.reload(), 2000);
        } catch (err) {
            setMessage('Failed to trigger demo story.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card p-8 bg-slate-900 text-white border-none overflow-hidden relative">
            <div className="absolute top-0 right-0 p-4 opacity-10">
                <span className="text-8xl font-black italic">DEMO</span>
            </div>

            <div className="relative z-10">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-3">
                    🎭 Fraud Scenario Engine
                </h2>
                <p className="text-slate-400 text-sm mb-8">
                    Inject pre-packaged fraud patterns into the system for real-time demonstration.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {stories.map(story => (
                        <div
                            key={story.id}
                            className={`p-6 rounded-2xl bg-slate-800 border border-slate-700 transition-all hover:border-blue-500 hover:bg-slate-700 cursor-pointer group flex flex-col justify-between ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                            onClick={() => !loading && triggerStory(story.id)}
                        >
                            <div>
                                <div className="text-3xl mb-4 group-hover:scale-110 transition-transform">{story.icon}</div>
                                <h3 className="font-bold text-sm mb-2 text-white">{story.name}</h3>
                                <p className="text-[10px] text-slate-400 leading-relaxed uppercase tracking-wider">{story.description}</p>
                            </div>

                            <div className="mt-6 pt-4 border-t border-slate-700 flex justify-between items-center text-[10px] font-bold text-blue-400">
                                <span>PLAY STORY</span>
                                <span className="opacity-0 group-hover:opacity-100 transition-opacity">▶️</span>
                            </div>
                        </div>
                    ))}
                </div>

                {message && (
                    <div className={`mt-6 p-4 rounded-xl text-sm font-bold text-center ${message.includes('Failed') ? 'bg-red-900/50 text-red-400' : 'bg-green-900/50 text-green-400'}`}>
                        {message}
                    </div>
                )}
            </div>

            {loading && (
                <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm z-30 flex items-center justify-center">
                    <div className="text-center">
                        <div className="inline-block w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4"></div>
                        <p className="font-bold animate-pulse uppercase tracking-widest text-xs">Injecting Scenario Data...</p>
                    </div>
                </div>
            )}
        </div>
    );
}
