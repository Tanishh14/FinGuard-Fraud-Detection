import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  const { logout, role } = useAuth()
  const isAdminOrAnalyst = role === 'admin' || role === 'fraud_analyst'

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const modules = [
    { name: 'Dashboard', icon: '⚡', path: '/dashboard', visible: isAdminOrAnalyst },
    { name: 'Live Transactions', icon: '💰', path: '/live-transactions', visible: true },
    { name: 'GNN Fraud Rings', icon: '🔗', path: '/gnn-fraud-rings', visible: isAdminOrAnalyst },
    { name: 'Anomaly Detection', icon: '⚠️', path: '/anomaly-detection', visible: isAdminOrAnalyst },
    // 'Fraud Trends' removed per request
  ].filter(m => m.visible)

  const isActive = (path: string) => location.pathname === path

  return (
    <aside className="w-72 bg-white border-r border-gray-200 p-6 shadow-sm">
      <div className="mb-8">
        <h2 className="text-xs font-bold text-gray-600 mb-4 uppercase tracking-widest">
          Detection Modules
        </h2>
      </div>

      <ul className="space-y-3">
        {modules.map((module, idx) => (
          <li
            key={idx}
            onClick={() => navigate(module.path)}
            className={`group relative p-3 rounded-lg cursor-pointer transition-all duration-300 hover:translate-x-1 border ${isActive(module.path)
              ? 'bg-blue-50 border-blue-300'
              : 'bg-gray-50 border-gray-200 hover:bg-blue-50 hover:border-blue-300'
              }`}
          >
            <div className="relative flex items-center gap-3">
              <span className="text-lg">{module.icon}</span>
              <span className={`text-sm font-medium transition-colors ${isActive(module.path)
                ? 'text-blue-600'
                : 'text-gray-700 group-hover:text-blue-600'
                }`}>
                {module.name}
              </span>
            </div>
          </li>
        ))}
      </ul>
      <div className="mt-auto pt-6 border-t border-gray-100">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 p-3 rounded-lg text-red-600 hover:bg-red-50 transition-colors group"
        >
          <span className="text-lg">🚪</span>
          <span className="text-sm font-medium group-hover:font-bold">Logout</span>
        </button>
      </div>
    </aside>
  )
}

