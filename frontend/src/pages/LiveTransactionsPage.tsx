import { useState, useEffect } from 'react'
import AdminLayout from '../layouts/AdminLayout'
import TransactionsTable from '../components/TransactionsTable'
import InvestigationPanel from '../components/InvestigationPanel'
import { fetchTransactions, getTransactionCount } from '../api/transactions.api'

interface DebugInfo {
  backendStatus: 'connected' | 'disconnected' | 'checking'
  dbStatus: 'connected' | 'disconnected' | 'checking'
  errors: string[]
  timestamp: string
  lastRefresh: string
}

interface Transaction {
  id: number
  user_id: number
  merchant: string
  amount: number
  device_id: string
  ip_address: string
  location: string
  avg_user_spend: number
  risk_score: number
  decision: string
  timestamp: string
}

import { useWebSocket } from '../hooks/useWebSocket'

export default function LiveTransactionsPage() {
  const [transactions, setTransactions] = useState<any[]>([])
  const [selectedTx, setSelectedTx] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [totalCount, setTotalCount] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedRange, setSelectedRange] = useState('1-200')
  const pageSize = 200

  // Filter state
  const [filters, setFilters] = useState({
    username: '',
    merchant: '',
    min_amount: '',
    max_amount: '',
    risk_level: ''
  })

  // Debounced/Buffered filter search (optional, but keep it simple for now)
  const [activeFilters, setActiveFilters] = useState<any>({})

  const [debug, setDebug] = useState<DebugInfo>({
    backendStatus: 'checking',
    dbStatus: 'checking',
    errors: [],
    timestamp: new Date().toISOString(),
    lastRefresh: ''
  })

  // Handle real-time updates
  useWebSocket((event) => {
    if (event.type === 'NEW_TRANSACTION') {
      const tx = event.data
      // Only add live if no search filters are active (to keep search consistent)
      if (Object.keys(activeFilters).length === 0) {
        setTransactions(prev => [tx, ...prev].slice(0, pageSize))
        setTotalCount(prev => prev + 1)
      }
    } else if (event.type === 'TRANSACTION_UPDATED') {
      const updatedTx = event.data
      setTransactions(prev => prev.map(tx =>
        tx.id === updatedTx.id || tx.tx_id === updatedTx.tx_id || tx.id === updatedTx.tx_id
          ? { ...tx, ...updatedTx, status: updatedTx.decision || updatedTx.status }
          : tx
      ))

      if (selectedTx && (selectedTx.id === updatedTx.id || selectedTx.tx_id === updatedTx.tx_id)) {
        setSelectedTx((prev: any) => ({ ...prev, ...updatedTx, status: updatedTx.decision || updatedTx.status }))
      }
    }

    setDebug(prev => ({
      ...prev,
      lastRefresh: new Date().toLocaleTimeString(),
      timestamp: new Date().toISOString()
    }))
  })

  // Fetch total count with filters
  const loadTotalCount = async (currentFilters: any) => {
    try {
      const result = await getTransactionCount(currentFilters)
      setTotalCount(result.total)
    } catch (err) {
      console.error('Failed to load total count:', err)
    }
  }

  // Load transactions for specific page with filters
  const loadTransactionsPage = async (page: number, currentFilters: any) => {
    try {
      setLoading(true)
      const errors: string[] = []

      // Fetch count first to update pagination
      await loadTotalCount(currentFilters)

      // Fetch transactions
      try {
        const data = await fetchTransactions(page, pageSize, currentFilters)
        if (Array.isArray(data)) {
          setTransactions(data)
          setDebug(prev => ({
            ...prev,
            dbStatus: 'connected',
            backendStatus: 'connected',
            lastRefresh: new Date().toLocaleTimeString()
          }))
        }
      } catch (err: any) {
        errors.push('Failed to fetch transactions: ' + err.message)
      }

      setDebug(prev => ({
        ...prev,
        errors,
        timestamp: new Date().toISOString()
      }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTransactionsPage(currentPage, activeFilters)
  }, [currentPage, activeFilters])

  const handleRefresh = async () => {
    await loadTransactionsPage(currentPage, activeFilters)
  }

  const handleSearch = () => {
    const newActiveFilters = {
      username: filters.username || undefined,
      merchant: filters.merchant || undefined,
      min_amount: filters.min_amount ? parseFloat(filters.min_amount) : undefined,
      max_amount: filters.max_amount ? parseFloat(filters.max_amount) : undefined,
      risk_level: filters.risk_level || undefined
    }
    setActiveFilters(newActiveFilters)
    setCurrentPage(1) // Reset to first page of results
    setSelectedRange(`1-${pageSize}`)
  }

  const handleClear = () => {
    setFilters({
      username: '',
      merchant: '',
      min_amount: '',
      max_amount: '',
      risk_level: ''
    })
    setActiveFilters({})
    setCurrentPage(1)
    setSelectedRange(`1-${pageSize}`)
  }

  return (
    <AdminLayout>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Live Transactions</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={handleClear}
            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Reset Filters
          </button>
        </div>
      </div>



      {/* Debug Information */}
      <div className="mb-6 p-4 bg-gray-900 text-gray-100 rounded-lg font-mono text-sm overflow-auto">
        <div className="mb-2 text-blue-400">=== DEBUG INFO ===</div>
        <div>Backend Status: <span className={debug.backendStatus === 'connected' ? 'text-green-400' : 'text-red-400'}>{debug.backendStatus.toUpperCase()}</span></div>
        <div>Database Status: <span className={debug.dbStatus === 'connected' ? 'text-green-400' : 'text-red-400'}>{debug.dbStatus.toUpperCase()}</span></div>
        <div>Transactions Loaded: {transactions.length}</div>
        {debug.lastRefresh && <div>Last Refresh: {debug.lastRefresh}</div>}
        <div>Debug Timestamp: {debug.timestamp}</div>

        {debug.errors.length > 0 && (
          <>
            <div className="mt-2 text-red-400">=== ERRORS ===</div>
            {debug.errors.map((err, idx) => (
              <div key={idx} className="text-red-300">• {err}</div>
            ))}
          </>
        )}

        {Object.keys(activeFilters).length > 0 && (
          <div className="mt-2 text-blue-300 italic">Filter active: {JSON.stringify(activeFilters)}</div>
        )}

        {debug.errors.length === 0 && (
          <div className="mt-2 text-green-400">=== STATUS: OK ===</div>
        )}
      </div>

      {/* Status Indicators */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className={`card p-6 border-l-4 ${debug.backendStatus === 'connected' ? 'border-green-500 bg-green-50' : 'border-red-500 bg-red-50'}`}>
          <div className="text-gray-600 text-sm font-semibold mb-2">Backend Connection</div>
          <div className={`text-3xl font-bold ${debug.backendStatus === 'connected' ? 'text-green-600' : 'text-red-600'}`}>
            {debug.backendStatus === 'connected' ? '✓' : '✗'}
          </div>
          <div className={`text-sm mt-1 ${debug.backendStatus === 'connected' ? 'text-green-700' : 'text-red-700'}`}>
            {debug.backendStatus === 'connected' ? 'Connected' : 'Disconnected'}
          </div>
        </div>

        <div className={`card p-6 border-l-4 ${debug.dbStatus === 'connected' ? 'border-green-500 bg-green-50' : 'border-red-500 bg-red-50'}`}>
          <div className="text-gray-600 text-sm font-semibold mb-2">Database Connection</div>
          <div className={`text-3xl font-bold ${debug.dbStatus === 'connected' ? 'text-green-600' : 'text-red-600'}`}>
            {debug.dbStatus === 'connected' ? '✓' : '✗'}
          </div>
          <div className={`text-sm mt-1 ${debug.dbStatus === 'connected' ? 'text-green-700' : 'text-red-700'}`}>
            {debug.dbStatus === 'connected' ? 'Connected' : 'Disconnected'}
          </div>
        </div>

        {/* LIVE TOTAL COUNTER */}
        <div className="card p-6 border-l-4 border-purple-500 bg-purple-50">
          <div className="text-gray-600 text-sm font-semibold mb-2">Found Transactions</div>
          <div className="text-3xl font-bold text-purple-600">{totalCount.toLocaleString()}</div>
          <div className="text-sm mt-1 text-purple-700">{Object.keys(activeFilters).length > 0 ? 'matching your search' : 'processed till now'}</div>
        </div>

        <div className="card p-6 border-l-4 border-blue-500 bg-blue-50">
          <div className="text-gray-600 text-sm font-semibold mb-2">Current Batch</div>
          <div className="text-3xl font-bold text-blue-600">{transactions.length}</div>
          <div className="text-sm mt-1 text-blue-700">records on this page</div>
        </div>
      </div>

      {/* Additional Stats */}
      {transactions.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="card p-6">
            <div className="text-gray-600 text-sm font-semibold mb-2">Flagged/Blocked</div>
            <div className="text-2xl font-bold text-red-600">
              {transactions.filter(tx => tx.decision === 'BLOCKED' || tx.decision === 'FLAGGED').length}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              ({((transactions.filter(tx => tx.decision === 'BLOCKED' || tx.decision === 'FLAGGED').length / transactions.length) * 100).toFixed(1)}%) in this batch
            </div>
          </div>

          <div className="card p-6">
            <div className="text-gray-600 text-sm font-semibold mb-2">Avg Risk Score</div>
            <div className="text-2xl font-bold text-yellow-600">
              {transactions.length > 0 ? (transactions.reduce((sum, tx) => sum + (tx.risk_score || tx.final_risk_score || 0), 0) / transactions.length).toFixed(1) : 0}%
            </div>
          </div>

          <div className="card p-6">
            <div className="text-gray-600 text-sm font-semibold mb-2">Total Amount</div>
            <div className="text-2xl font-bold text-blue-600">
              ₹{(transactions.reduce((sum, tx) => sum + tx.amount, 0)).toLocaleString('en-IN')}
            </div>
          </div>
        </div>
      )}

      {/* Control Panel: Filters + Pagination */}
      <div className="card p-6 mb-8 bg-white shadow-xl border-t-4 border-blue-600">
        <div className="flex flex-col gap-6">
          {/* Advanced Search Filters Row */}
          <div className="flex flex-wrap items-end gap-4 pb-4 border-b border-gray-100">
            <div className="flex-1 min-w-[150px]">
              <label className="text-[10px] font-black uppercase text-gray-400 mb-1 block">Username</label>
              <input
                type="text"
                placeholder="Search user..."
                value={filters.username}
                onChange={(e) => setFilters(prev => ({ ...prev, username: e.target.value }))}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-sm font-bold"
              />
            </div>
            <div className="flex-1 min-w-[150px]">
              <label className="text-[10px] font-black uppercase text-gray-400 mb-1 block">Merchant</label>
              <input
                type="text"
                placeholder="Search merchant..."
                value={filters.merchant}
                onChange={(e) => setFilters(prev => ({ ...prev, merchant: e.target.value }))}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-sm font-bold"
              />
            </div>
            <div className="flex gap-2 min-w-[200px]">
              <div className="flex-1">
                <label className="text-[10px] font-black uppercase text-gray-400 mb-1 block">Min Amount</label>
                <input
                  type="number"
                  placeholder="₹ 0"
                  value={filters.min_amount}
                  onChange={(e) => setFilters(prev => ({ ...prev, min_amount: e.target.value }))}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-sm font-bold"
                />
              </div>
              <div className="flex-1">
                <label className="text-[10px] font-black uppercase text-gray-400 mb-1 block">Max Amount</label>
                <input
                  type="number"
                  placeholder="₹ max"
                  value={filters.max_amount}
                  onChange={(e) => setFilters(prev => ({ ...prev, max_amount: e.target.value }))}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-sm font-bold"
                />
              </div>
            </div>
            <div className="w-[150px]">
              <label className="text-[10px] font-black uppercase text-gray-400 mb-1 block">Risk Verdict</label>
              <select
                value={filters.risk_level}
                onChange={(e) => setFilters(prev => ({ ...prev, risk_level: e.target.value }))}
                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all text-sm font-bold appearance-none cursor-pointer"
              >
                <option value="">All Levels</option>
                <option value="SAFE">Safe/Approved</option>
                <option value="SUSPICIOUS">Suspicious/Flagged</option>
                <option value="BLOCKED">Blocked</option>
              </select>
            </div>
            <button
              onClick={handleSearch}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-black uppercase tracking-widest text-[10px] rounded-xl shadow-lg shadow-blue-200 transition-all active:scale-95 flex items-center gap-2 h-[38px]"
            >
              Apply Filter
            </button>
          </div>

          {/* Range Selector & Pagination Row */}
          {totalCount > 0 && (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <label className="text-xs font-black uppercase tracking-widest text-gray-400">Transaction Range:</label>
                <div className="relative">
                  <select
                    value={selectedRange}
                    onChange={(e) => {
                      const value = e.target.value
                      setSelectedRange(value)
                      const page = Math.ceil(parseInt(value.split('–')[0].trim()) / pageSize) || 1
                      setCurrentPage(page)
                    }}
                    className="px-6 py-2 border border-blue-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 bg-blue-50/30 text-blue-700 font-bold text-sm appearance-none pr-10 cursor-pointer hover:bg-blue-50 transition-colors"
                  >
                    {Array.from({ length: Math.ceil(totalCount / pageSize) }, (_, i) => {
                      const start = i * pageSize + 1
                      const end = Math.min((i + 1) * pageSize, totalCount)
                      const rangeLabel = `${start} – ${end}`
                      return (
                        <option key={i} value={rangeLabel}>
                          {rangeLabel} ({end - start + 1} transactions)
                        </option>
                      )
                    })}
                  </select>
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-blue-400">▼</div>
                </div>
              </div>

              <div className="flex items-center gap-6">
                <div className="px-4 py-1.5 bg-gray-50 rounded-full border border-gray-100 flex items-center gap-3">
                  <span className="text-[10px] font-black uppercase text-gray-400">Pagination Status:</span>
                  <span className="text-sm font-black text-gray-700 italic">Page {currentPage} of {Math.max(1, Math.ceil(totalCount / pageSize))}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Loading State */}
      {loading && transactions.length === 0 && (
        <div className="card p-8 text-center">
          <div className="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
          <p className="text-gray-600">Loading transactions...</p>
        </div>
      )}

      {/* Transactions Table */}
      {!loading && (
        <TransactionsTable
          transactions={transactions}
          onSelectTransaction={(tx) => setSelectedTx(tx)}
        />
      )}

      {/* Investigation Panel Modal */}
      {selectedTx && (
        <InvestigationPanel
          transaction={selectedTx}
          onClose={() => setSelectedTx(null)}
          onActionSuccess={handleRefresh}
        />
      )}

      {/* No Data State */}
      {!loading && transactions.length === 0 && debug.dbStatus === 'connected' && (
        <div className="card p-8 text-center">
          <div className="text-4xl mb-4">📊</div>
          <p className="text-gray-600">No transactions available. Ensure data is being sent to the backend.</p>
        </div>
      )}
    </AdminLayout>
  )
}
