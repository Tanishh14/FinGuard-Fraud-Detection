import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface ProtectedRouteProps {
  children: JSX.Element
  requiredRoles?: string[]
}

export default function ProtectedRoute({ children, requiredRoles }: ProtectedRouteProps) {
  const { user_id, role, is_loading } = useAuth()

  if (is_loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!user_id) {
    return <Navigate to="/login" />
  }

  if (requiredRoles && role && !requiredRoles.includes(role)) {
    // If user is restricted from this page, send them to their allowed home
    return <Navigate to={role === 'user' ? '/profile' : '/dashboard'} />
  }

  return children
}
