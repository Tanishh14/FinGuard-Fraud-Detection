import { useState, useEffect } from 'react'
import AdminLayout from '../layouts/AdminLayout'
import { useAuth } from '../hooks/useAuth'
import LiveRiskDashboard from '../components/LiveRiskDashboard'

interface ReviewQueueItem {
  tx_id: number
  user_id: number
  amount: number
  merchant: string
  location: string
  timestamp: string
  risk_score: number
  status: string
  risk_flags: string[]
  explanation: string | null
  audit_id: number | null
}

interface TransactionDetail {
  id: number
  user_id: number
  merchant: string
  amount: number
  location: string
  device_id: string
  ip_address: string
  timestamp: string
  ae_score: number
  if_score: number
  gnn_score: number
  rule_score: number
  final_risk_score: number
  risk_flags: string[]
  status: string
  explanation: string
  avg_user_spend: number
}

export default function FraudAnalystDashboard() {
  const { token } = useAuth()
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([])
  const [selectedTx, setSelectedTx] = useState<ReviewQueueItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [reviewNotes, setReviewNotes] = useState('')
  const [stats, setStats] = useState({
    total: 0,
    flagged: 0,
    reviewed_today: 0,
    false_positive_rate: 0
  })

  useEffect(() => {
    loadReviewQueue()
    loadStats()
  }, [])

  const loadReviewQueue = async () => {
    try {
      setLoading(true)
      const headers: any = { 'Content-Type': 'application/json' }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      
      const response = await fetch('http://localhost:8000/audit/review-queue?limit=50', {
        credentials: 'include',
        headers
      })
      if (response.ok) {
        const data = await response.json()
        setReviewQueue(data)
      }
    } catch (error) {
      console.error('Failed to load review queue:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const headers: any = { 'Content-Type': 'application/json' }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      
      const response = await fetch('http://localhost:8000/audit/stats', {
        credentials: 'include',
        headers
      })
      if (response.ok) {
        const data = await response.json()
        setStats({
          total: data.total_transactions,
          flagged: data.auto_flagged + data.auto_blocked,
          reviewed_today: data.analyst_reviewed,
          false_positive_rate: data.false_positive_rate
        })
      }
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  const handleReview = async (action: 'APPROVED' | 'REJECTED' | 'ESCALATED') => {
    if (!selectedTx) return

    try {
      setActionLoading(true)
      const headers: any = { 'Content-Type': 'application/json' }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      
      const response = await fetch(`http://localhost:8000/audit/transactions/${selectedTx.tx_id}/review`, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: JSON.stringify({
          action: action,
          notes: reviewNotes || null
        })
      })

      if (response.ok) {
        // Remove from queue and reset selection
        setReviewQueue(prev => prev.filter(item => item.tx_id !== selectedTx.tx_id))
        setSelectedTx(null)
        setReviewNotes('')
        loadStats()
      } else {
        const error = await response.json()
        alert(`Review failed: ${error.detail}`)
      }
    } catch (error) {
      console.error('Review failed:', error)
      alert('Failed to submit review')
    } finally {
      setActionLoading(false)
    }
  }

  const getRiskColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600 bg-red-100'
    if (score >= 0.5) return 'text-orange-600 bg-orange-100'
    return 'text-yellow-600 bg-yellow-100'
  }

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount || 0)
  }

  return (
    <AdminLayout>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">🔍 Fraud Analyst Dashboard</h1>
        <p className="text-gray-600 mt-1">Review flagged transactions and make decisions</p>
      </div>

      <LiveRiskDashboard />

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="card p-4 bg-gradient-to-br from-blue-50 to-blue-100 border-l-4 border-blue-500">
          <div className="text-sm text-blue-600 font-medium">Total Transactions</div>
          <div className="text-2xl font-bold text-blue-800">{stats.total.toLocaleString()}</div>
        </div>
        <div className="card p-4 bg-gradient-to-br from-orange-50 to-orange-100 border-l-4 border-orange-500">
          <div className="text-sm text-orange-600 font-medium">Flagged for Review</div>
          <div className="text-2xl font-bold text-orange-800">{reviewQueue.length}</div>
        </div>
        <div className="card p-4 bg-gradient-to-br from-green-50 to-green-100 border-l-4 border-green-500">
          <div className="text-sm text-green-600 font-medium">Reviewed (30 days)</div>
          <div className="text-2xl font-bold text-green-800">{stats.reviewed_today}</div>
        </div>
        <div className="card p-4 bg-gradient-to-br from-purple-50 to-purple-100 border-l-4 border-purple-500">
          <div className="text-sm text-purple-600 font-medium">False Positive Rate</div>
          <div className="text-2xl font-bold text-purple-800">{stats.false_positive_rate}%</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Review Queue */}
        <div className="card">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <span className="text-orange-500">⚠️</span>
              Review Queue
              <span className="ml-auto text-sm font-normal text-gray-500">
                {reviewQueue.length} pending
              </span>
            </h2>
          </div>

          <div className="max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center">
                <div className="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
              </div>
            ) : reviewQueue.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <div className="text-4xl mb-2">✅</div>
                <p>No transactions pending review</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {reviewQueue.map((item) => (
                  <div
                    key={item.tx_id}
                    onClick={() => setSelectedTx(item)}
                    className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${selectedTx?.tx_id === item.tx_id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                      }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <span className="font-medium">#{item.tx_id}</span>
                        <span className="text-gray-500 text-sm ml-2">{item.merchant}</span>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(item.risk_score)}`}>
                        {(item.risk_score * 100).toFixed(0)}% Risk
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">{formatAmount(item.amount)}</span>
                      <span className="text-gray-400">{new Date(item.timestamp).toLocaleDateString()}</span>
                    </div>
                    {item.risk_flags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {item.risk_flags.slice(0, 3).map((flag, idx) => (
                          <span key={idx} className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded">
                            {flag}
                          </span>
                        ))}
                        {item.risk_flags.length > 3 && (
                          <span className="text-xs text-gray-400">+{item.risk_flags.length - 3} more</span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Transaction Detail & Review Panel */}
        <div className="card">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold">📋 Transaction Details</h2>
          </div>

          {selectedTx ? (
            <div className="p-4">
              {/* Transaction Info */}
              <div className="space-y-4 mb-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-gray-500 uppercase">Transaction ID</label>
                    <p className="font-medium">#{selectedTx.tx_id}</p>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 uppercase">User ID</label>
                    <p className="font-medium">#{selectedTx.user_id}</p>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 uppercase">Amount</label>
                    <p className="font-medium text-lg">{formatAmount(selectedTx.amount)}</p>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 uppercase">Merchant</label>
                    <p className="font-medium">{selectedTx.merchant}</p>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 uppercase">Location</label>
                    <p className="font-medium">{selectedTx.location}</p>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 uppercase">Timestamp</label>
                    <p className="font-medium">{new Date(selectedTx.timestamp).toLocaleString()}</p>
                  </div>
                </div>

                {/* Risk Score Breakdown */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-semibold mb-3 text-gray-700">Risk Score: {(selectedTx.risk_score * 100).toFixed(1)}%</h3>
                  <div className="w-full bg-gray-200 rounded-full h-3 mb-3">
                    <div
                      className={`h-3 rounded-full ${selectedTx.risk_score >= 0.8 ? 'bg-red-500' :
                        selectedTx.risk_score >= 0.5 ? 'bg-orange-500' : 'bg-yellow-500'
                        }`}
                      style={{ width: `${selectedTx.risk_score * 100}%` }}
                    ></div>
                  </div>
                </div>

                {/* Risk Flags */}
                {selectedTx.risk_flags.length > 0 && (
                  <div>
                    <label className="text-xs text-gray-500 uppercase">Risk Flags</label>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {selectedTx.risk_flags.map((flag, idx) => (
                        <span key={idx} className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm">
                          {flag.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* AI Explanation */}
                {selectedTx.explanation && (
                  <div className="bg-blue-50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold mb-2 text-blue-800 flex items-center gap-2">
                      🧠 AI Explanation
                    </h3>
                    <p className="text-sm text-blue-900">{selectedTx.explanation}</p>
                  </div>
                )}
              </div>

              {/* Review Actions */}
              <div className="border-t pt-4">
                <label className="text-xs text-gray-500 uppercase mb-2 block">Review Notes (Optional)</label>
                <textarea
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Add notes about your decision..."
                  className="w-full p-3 border border-gray-300 rounded-lg mb-4 text-sm"
                  rows={3}
                />

                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() => handleReview('APPROVED')}
                    disabled={actionLoading}
                    className="py-3 px-4 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50"
                  >
                    ✓ Approve
                  </button>
                  <button
                    onClick={() => handleReview('REJECTED')}
                    disabled={actionLoading}
                    className="py-3 px-4 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
                  >
                    ✗ Reject
                  </button>
                  <button
                    onClick={() => handleReview('ESCALATED')}
                    disabled={actionLoading}
                    className="py-3 px-4 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700 transition-colors disabled:opacity-50"
                  >
                    ↑ Escalate
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              <div className="text-4xl mb-2">👆</div>
              <p>Select a transaction from the queue to review</p>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  )
}
