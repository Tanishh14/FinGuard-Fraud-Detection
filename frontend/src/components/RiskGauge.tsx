export default function RiskGauge({ title, value, unit, color = 'blue' }: { title: string, value: number, unit: string, color?: string }) {
    const percentage = Math.min(Math.max(value, 0), 100);

    const colors: Record<string, string> = {
        blue: 'from-blue-500 to-blue-600',
        red: 'from-red-500 to-red-600',
        orange: 'from-orange-500 to-orange-600',
        green: 'from-green-500 to-green-600'
    };

    return (
        <div className="card p-6 flex flex-col items-center justify-center text-center">
            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">{title}</h4>

            <div className="relative w-32 h-32">
                {/* Track */}
                <svg className="w-full h-full" viewBox="0 0 100 100">
                    <circle
                        cx="50" cy="50" r="45"
                        fill="none"
                        stroke="#f3f4f6"
                        strokeWidth="8"
                    />
                    {/* Progress */}
                    <circle
                        cx="50" cy="50" r="45"
                        fill="none"
                        className={`stroke-current text-${color}-500`}
                        strokeWidth="8"
                        strokeDasharray={`${percentage * 2.82} 282`}
                        strokeDashoffset="0"
                        strokeLinecap="round"
                        transform="rotate(-90 50 50)"
                        style={{ transition: 'stroke-dasharray 1s ease-out' }}
                    />
                </svg>

                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl font-black text-gray-900">{value}{unit}</span>
                    <span className="text-[10px] text-gray-400 font-bold uppercase">Real-time</span>
                </div>
            </div>
        </div>
    );
}
