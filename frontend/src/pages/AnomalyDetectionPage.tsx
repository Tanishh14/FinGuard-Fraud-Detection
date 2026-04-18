import { useState, useEffect, useTransition, useMemo } from 'react'
import AdminLayout from '../layouts/AdminLayout'
import { getAnomalyPatterns } from '../api/anomaly.api'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAuth } from '../hooks/useAuth'
import ExplainDrawer from '../components/ExplainDrawer'

export default function AnomalyDetectionPage() {
  const [loading, setLoading] = useState(false)
  const [isPending, startTransition] = useTransition()
  const [patterns, setPatterns] = useState([])

  // Filter states
  const [usernameFilter, setUsernameFilter] = useState('')
  const [minAmount, setMinAmount] = useState('')
  const [maxAmount, setMaxAmount] = useState('')
  const [txIdFilter, setTxIdFilter] = useState('')

  // Explainability drawer state
  const [selectedTx, setSelectedTx] = useState<any>(null)
  const [showDrawer, setShowDrawer] = useState(false)
  const { role } = useAuth()

  useEffect(() => {
    const loadPatterns = async () => {
      try {
        setLoading(true)
        const data = await getAnomalyPatterns()
        setPatterns(data)
      } catch (err) {
        console.error("Anomaly service not reachable:", err)
      } finally {
        setLoading(false)
      }
    }

    loadPatterns()
  }, [])

  // Optimize: Move filtering to useMemo so it integrates better with useTransition
  const filteredPatterns = useMemo(() => {
    // ONLY show Blocked, Review, or Flagged anomaly transactions. Hide safe approvals.
    let filtered = patterns.filter((p: any) => 
      ['BLOCKED', 'REVIEW', 'FLAGGED', 'UNDER_REVIEW'].includes(p.decision || p.status)
    );

    // Username filter
    if (usernameFilter.trim()) {
      filtered = filtered.filter((p: any) =>
        p.username?.toLowerCase().includes(usernameFilter.toLowerCase())
      )
    }

    // Amount range filter
    if (minAmount) {
      filtered = filtered.filter((p: any) => p.amount >= parseFloat(minAmount))
    }
    if (maxAmount) {
      filtered = filtered.filter((p: any) => p.amount <= parseFloat(maxAmount))
    }

    // Transaction ID filter
    if (txIdFilter.trim()) {
      filtered = filtered.filter((p: any) =>
        p.transaction_id?.toString() === txIdFilter.trim()
      )
    }

    return filtered
  }, [usernameFilter, minAmount, maxAmount, txIdFilter, patterns])

  // Real-time updates for anomaly decisions
  useWebSocket((event) => {
    if (event.type === 'TRANSACTION_UPDATED') {
      const updatedTx = event.data;
      setPatterns((prev: any) => prev.map((p: any) =>
        (p.transaction_id === updatedTx.id || p.transaction_id === updatedTx.tx_id)
          ? { ...p, decision: updatedTx.decision || updatedTx.status }
          : p
      ));
    } else if (event.type === 'NEW_TRANSACTION') {
      // Refresh patterns if a new transaction comes in that might be an anomaly
      getAnomalyPatterns().then(data => {
        setPatterns(data)
      }).catch(console.error);
    }
  });

  const handleExplain = (pattern: any) => {
    setSelectedTx(pattern)
    setShowDrawer(true)
  }

  const closeDrawer = () => {
    setShowDrawer(false)
    setSelectedTx(null)
  }

  // Format timestamp to IST with full date/time
  const formatTimestamp = (isoString: string) => {
    const date = new Date(isoString)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} IST`
  }

  return (
    <AdminLayout>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">⚡ Anomaly Detection</h1>
        <p className="text-gray-600">Identify unusual patterns and outliers in transaction data</p>
      </div>

      {/* Filters Section */}
      <div className="card p-6 mb-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">🔍 Filters</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Username</label>
            <input
              type="text"
              placeholder="Search by username..."
              value={usernameFilter}
              onChange={(e) => startTransition(() => setUsernameFilter(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Min Amount (₹)</label>
            <input
              type="number"
              placeholder="0"
              value={minAmount}
              onChange={(e) => startTransition(() => setMinAmount(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Max Amount (₹)</label>
            <input
              type="number"
              placeholder="∞"
              value={maxAmount}
              onChange={(e) => startTransition(() => setMaxAmount(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Transaction ID</label>
            <input
              type="text"
              placeholder="Exact match..."
              value={txIdFilter}
              onChange={(e) => startTransition(() => setTxIdFilter(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
        {(usernameFilter || minAmount || maxAmount || txIdFilter) && (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-xs text-gray-600">
              Showing {filteredPatterns.length} of {patterns.length} results
            </span>
            <button
              onClick={() => {
                setUsernameFilter('')
                setMinAmount('')
                setMaxAmount('')
                setTxIdFilter('')
              }}
              className="text-xs text-blue-600 hover:underline"
            >
              Clear Filters
            </button>
          </div>
        )}
      </div>

      {/* Real-time Anomaly Data */}
      <div className="grid grid-cols-1 gap-6">
        <div className="card p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              Recent Anomaly Patterns
              {isPending && <span className="text-[10px] text-blue-500 animate-pulse font-normal tracking-widest uppercase">/ Updating...</span>}
            </h2>
            <div className="flex gap-2">
              <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">
                Live Monitoring Active
              </span>
              <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">
                Autoencoder Connected
              </span>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-12 text-gray-500">
              <div className="animate-spin inline-block w-8 h-8 border-4 border-current border-t-transparent rounded-full mb-2"></div>
              <p>Scanning transaction stream...</p>
            </div>
          ) : filteredPatterns.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-gray-200 text-xs text-gray-500 uppercase">
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Transaction ID</th>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Merchant</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Anomaly Score</th>
                    <th className="px-4 py-3">Decision</th>
                    <th className="px-4 py-3">Explain</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredPatterns.map((p: any) => (
                    <tr key={p.transaction_id || Math.random()} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-600 font-mono">
                        {formatTimestamp(p.timestamp)}
                      </td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-500">
                        TXN-{p.transaction_id}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 font-medium">
                        {p.username || 'Unknown'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {p.merchant}
                      </td>
                      <td className="px-4 py-3 text-sm font-bold text-gray-900">
                        ₹{p.amount?.toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${p.anomaly_score > 0.8 ? 'bg-red-500' : p.anomaly_score > 0.6 ? 'bg-orange-500' : 'bg-yellow-500'}`}
                              style={{ width: `${(p.anomaly_score || 0) * 100}%` }}
                            ></div>
                          </div>
                          <span className={`text-xs font-bold ${p.anomaly_score > 0.8 ? 'text-red-600' : p.anomaly_score > 0.6 ? 'text-orange-600' : 'text-yellow-600'}`}>
                            {((p.anomaly_score || 0) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`badge ${p.decision === 'BLOCKED' ? 'badge-danger' :
                          ['FLAGGED', 'REVIEW', 'UNDER_REVIEW'].includes(p.decision) ? 'badge-warning' : 'badge-success'
                          } text-xs`}>
                          {p.decision}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleExplain(p)}
                          className="text-blue-600 hover:text-blue-800 text-sm font-semibold hover:underline flex items-center gap-1"
                        >
                          Explain →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12 bg-gray-50 rounded-xl border border-dashed border-gray-300">
              <p className="text-gray-500">
                {patterns.length > 0 ? 'No results match your filters.' : 'No anomalies detected in the last observation window.'}
              </p>
              {patterns.length > 0 ? (
                <button
                  onClick={() => {
                    setUsernameFilter('')
                    setMinAmount('')
                    setMaxAmount('')
                    setTxIdFilter('')
                  }}
                  className="mt-4 text-blue-600 text-sm hover:underline"
                >
                  Clear Filters
                </button>
              ) : (
                <button
                  onClick={() => window.location.reload()}
                  className="mt-4 text-blue-600 text-sm hover:underline"
                >
                  Refresh Data
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Explainability Drawer */}
      <ExplainDrawer
        isOpen={showDrawer}
        onClose={closeDrawer}
        transaction={selectedTx}
        userRole={role as string}
      />
    </AdminLayout>
  )
}
