import { useState, useEffect } from 'react';

interface Hotspot {
    location: string;
    lat: number;
    lng: number;
    count: number;
    risk: number;
}

export default function GeoMap({ hotspots }: { hotspots: Hotspot[] }) {
    return (
        <div className="card p-0 overflow-hidden relative group">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white/80 backdrop-blur-md sticky top-0 z-10">
                <div>
                    <h3 className="font-bold text-gray-900">Global Fraud Hotspots</h3>
                    <p className="text-xs text-gray-500">Live geographic distribution of suspicious activity</p>
                </div>
                <div className="flex gap-2">
                    <span className="flex items-center gap-1 text-[10px] font-bold text-gray-400 uppercase">
                        <span className="w-2 h-2 rounded-full bg-red-500"></span> High Risk
                    </span>
                    <span className="flex items-center gap-1 text-[10px] font-bold text-gray-400 uppercase">
                        <span className="w-2 h-2 rounded-full bg-blue-500"></span> Volume
                    </span>
                </div>
            </div>

            <div className="h-[400px] bg-slate-50 relative overflow-hidden bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]">
                {/* Simple Grid Overlay for aesthetic */}
                <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>

                {/* Legend Overlay */}
                <div className="absolute bottom-4 left-4 bg-white/90 p-3 rounded-xl shadow-xl border border-gray-100 z-10 text-[10px]">
                    <div className="space-y-2">
                        {hotspots.slice(0, 3).map((h, i) => (
                            <div key={i} className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                                <span className="font-bold text-gray-700">{h.location}</span>
                                <span className="text-gray-400">({h.count} tx)</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Hotspot Markers (Simplified Projection) */}
                <div className="absolute inset-0">
                    {hotspots.map((h, idx) => {
                        // VERY crude projection for demo purposes
                        const x = ((h.lng + 180) / 360) * 100;
                        const y = ((90 - h.lat) / 180) * 100;

                        return (
                            <div
                                key={idx}
                                className="absolute group/marker transform -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all hover:scale-150"
                                style={{ left: `${x}%`, top: `${y}%` }}
                            >
                                {/* Pulse effect for high risk */}
                                {h.risk > 0.7 && (
                                    <div className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-75"></div>
                                )}
                                <div className={`w-3 h-3 rounded-full border-2 border-white shadow-lg ${h.risk > 0.7 ? 'bg-red-500' : 'bg-blue-500'}`}></div>

                                {/* Tooltip */}
                                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-[10px] font-bold rounded opacity-0 group-hover/marker:opacity-100 transition-opacity whitespace-nowrap z-20">
                                    {h.location}: {Math.round(h.risk * 100)}% Risk
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="absolute inset-0 flex items-center justify-center opacity-5 pointer-events-none select-none">
                    <span className="text-9xl font-black italic">FINGUARD MAP</span>
                </div>
            </div>
        </div>
    );
}
