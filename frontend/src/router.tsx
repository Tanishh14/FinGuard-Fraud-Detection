import { createBrowserRouter, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import NotFound from './pages/NotFound'
import ProtectedRoute from './components/ProtectedRoute'
import GNNFraudRingsPage from './pages/GNNFraudRingsPage'
import AnomalyDetectionPage from './pages/AnomalyDetectionPage'
import LiveTransactionsPage from './pages/LiveTransactionsPage'
import FraudAnalystDashboard from './pages/FraudAnalystDashboard'
import TransactionStoryPage from './pages/TransactionStoryPage'
import ProfilePage from './pages/ProfilePage'
import ReportAppealPage from './pages/ReportAppealPage'

import LandingPage from './pages/LandingPage'

const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute requiredRoles={['admin', 'fraud_analyst']}>
        <DashboardPage />
      </ProtectedRoute>
    )
  },
  {
    path: '/analyst',
    element: (
      <ProtectedRoute requiredRoles={['fraud_analyst', 'admin']}>
        <FraudAnalystDashboard />
      </ProtectedRoute>
    )
  },
  {
    path: '/gnn-fraud-rings',
    element: (
      <ProtectedRoute requiredRoles={['admin', 'fraud_analyst']}>
        <GNNFraudRingsPage />
      </ProtectedRoute>
    )
  },
  {
    path: '/anomaly-detection',
    element: (
      <ProtectedRoute requiredRoles={['admin', 'fraud_analyst']}>
        <AnomalyDetectionPage />
      </ProtectedRoute>
    )
  },
  // '/trends' route removed per request
  {
    path: '/live-transactions',
    element: (
      <ProtectedRoute requiredRoles={['admin', 'fraud_analyst']}>
        <LiveTransactionsPage />
      </ProtectedRoute>
    )
  },
  {
    path: '/forensics/story/:id',
    element: (
      <ProtectedRoute requiredRoles={['admin', 'fraud_analyst']}>
        <TransactionStoryPage />
      </ProtectedRoute>
    )
  },
  {
    path: '/profile',
    element: (
      <ProtectedRoute>
        <ProfilePage />
      </ProtectedRoute>
    )
  },
  {
    path: '/transactions/:id/report-appeal',
    element: (
      <ProtectedRoute>
        <ReportAppealPage />
      </ProtectedRoute>
    )
  },
  { path: '*', element: <NotFound /> }
])

export default router
