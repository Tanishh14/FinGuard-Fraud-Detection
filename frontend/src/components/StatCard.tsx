interface Props {
  title: string
  value: string
  icon?: string
  trend?: string
  color?: 'red' | 'orange' | 'green' | 'blue'
}

const colorMap = {
  red: { border: 'border-l-red-500', icon: 'bg-red-100' },
  orange: { border: 'border-l-orange-500', icon: 'bg-orange-100' },
  green: { border: 'border-l-green-500', icon: 'bg-green-100' },
  blue: { border: 'border-l-blue-500', icon: 'bg-blue-100' },
};

export default function StatCard({ title, value, icon = '📊', trend, color = 'blue' }: Props) {
  const colors = colorMap[color];
  
  return (
    <div className={`card-bordered ${colors.border} group`}>
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">
              {title}
            </div>
            <div className="flex items-baseline gap-2">
              <div className="text-3xl font-bold text-gray-900">
                {value}
              </div>
              {trend && (
                <span className={`text-xs font-semibold ${
                  trend.startsWith('+') ? 'text-green-600' : 'text-red-600'
                }`}>
                  {trend}
                </span>
              )}
            </div>
          </div>
          <div className={`w-12 h-12 rounded-lg ${colors.icon} flex items-center justify-center text-xl opacity-75`}>
            {icon}
          </div>
        </div>
      </div>
    </div>
  )
}
