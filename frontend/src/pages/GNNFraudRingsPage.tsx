import { useState } from 'react'
import AdminLayout from '../layouts/AdminLayout'
import NetworkGraph from '../components/NetworkGraph'
import { searchGraphData, searchClusterAnalysis } from '../api/gnn.api'

export default function GNNFraudRingsPage() {
  const [loading, setLoading] = useState(false)
  const [graphData, setGraphData] = useState<any>(null)
  const [clusters, setClusters] = useState<any[]>([])
  const [selectedCluster, setSelectedCluster] = useState<any>(null)
  const [showExplanation, setShowExplanation] = useState(false)
  const [explanation, setExplanation] = useState('')
  const [loadingExplanation, setLoadingExplanation] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  // Search fields
  const [searchTxId, setSearchTxId] = useState('')
  const [searchMerchant, setSearchMerchant] = useState('')
  const [searchUsername, setSearchUsername] = useState('')

  const hasSearchInput = searchTxId.trim() || searchMerchant.trim() || searchUsername.trim()

  const handleSearch = async () => {
    if (!hasSearchInput) return

    try {
      setLoading(true)
      setHasSearched(true)

      const params: any = {}
      if (searchTxId.trim()) params.transaction_id = parseInt(searchTxId.trim())
      if (searchMerchant.trim()) params.merchant_name = searchMerchant.trim()
      if (searchUsername.trim()) params.username = searchUsername.trim()

      const [graphResponse, clusterResponse] = await Promise.all([
        searchGraphData(params),
        searchClusterAnalysis({ ...params, min_cluster_size: 2, risk_threshold: 0.3 })
      ])
      setGraphData(graphResponse)
      setClusters(clusterResponse.clusters || [])
    } catch (err) {
      console.error("GNN search failed:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setSearchTxId('')
    setSearchMerchant('')
    setSearchUsername('')
    setGraphData(null)
    setClusters([])
    setHasSearched(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && hasSearchInput) {
      handleSearch()
    }
  }

  const handleExplainCluster = async (cluster: any) => {
    setSelectedCluster(cluster)
    setShowExplanation(true)
    setLoadingExplanation(true)
    setExplanation('')

    try {
      const mockExplanation = `**Cluster Risk Assessment:**
This cluster has a risk score of ${cluster.risk_score}/100, classified as ${cluster.risk_score > 80 ? 'HIGH' : cluster.risk_score > 60 ? 'MEDIUM' : 'LOW'} risk. The cluster consists of ${cluster.user_count} users conducting ${cluster.total_tx_count} transactions with an average amount of ₹${cluster.avg_amount.toLocaleString()}.

**Key Evidence:**
${cluster.shared_devices && cluster.shared_devices.length > 0 ? `- Device ${cluster.shared_devices[0].device_id.substring(0, 8)}... is shared by ${cluster.shared_devices[0].user_count} users, indicating potential coordinated activity` : '- No shared devices detected'}
- ${cluster.flagged_tx_count} out of ${cluster.total_tx_count} transactions (${((cluster.flagged_tx_count / cluster.total_tx_count) * 100).toFixed(1)}%) were flagged as suspicious
${cluster.top_users && cluster.top_users.length > 0 ? `- User ${cluster.top_users[0].user_id} contributes ${cluster.top_users[0].contribution}% of the cluster's risk score with individual risk of ${cluster.top_users[0].risk_score}/100` : ''}
- Dominant pattern detected: ${cluster.dominant_pattern}

**Risk Propagation:**
The risk spreads through ${cluster.merchant_count} merchants and ${cluster.device_count} devices. ${cluster.shared_devices && cluster.shared_devices.length > 0 ? `The most concerning propagation vector is the shared device connecting ${cluster.shared_devices[0].user_count} users, amplifying risk by enabling coordinated transactions.` : 'Risk propagation is primarily through merchant relationships.'}

**Recommended Action:**
${cluster.risk_score > 80 ? 'IMMEDIATE INVESTIGATION REQUIRED. This cluster shows strong indicators of coordinated fraud activity. Recommend freezing accounts and escalating to law enforcement.' : cluster.risk_score > 60 ? 'ENHANCED MONITORING. This cluster warrants close observation and additional verification before taking action.' : 'ROUTINE MONITORING. This cluster may represent legitimate shared merchant usage. Continue standard monitoring protocols.'}`

      setExplanation(mockExplanation)
    } catch (err) {
      console.error("Failed to generate explanation:", err)
      setExplanation("⚠️ Explanation temporarily unavailable. Please review cluster details manually.")
    } finally {
      setLoadingExplanation(false)
    }
  }

  return (
    <AdminLayout>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">🔗 GNN Fraud Network Analysis</h1>
        <p className="text-gray-600">Search and visualize fraud networks using Graph Neural Networks</p>
      </div>

      {/* Search Controls */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-lg font-bold text-gray-800">🔍 Search Filters</span>
          <span className="text-xs text-gray-500 ml-2">Enter at least one field to search</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          {/* Transaction ID Search */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
              Transaction ID
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm">
                #
              </span>
              <input
                id="search-tx-id"
                type="number"
                value={searchTxId}
                onChange={(e) => setSearchTxId(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. 1042"
                className="w-full pl-8 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all placeholder-gray-400"
              />
            </div>
          </div>

          {/* Merchant Name Search */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
              Merchant Name
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm">
                🏪
              </span>
              <input
                id="search-merchant"
                type="text"
                value={searchMerchant}
                onChange={(e) => setSearchMerchant(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. Amazon, Flipkart"
                className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all placeholder-gray-400"
              />
            </div>
          </div>

          {/* Username Search */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
              Username
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm">
                👤
              </span>
              <input
                id="search-username"
                type="text"
                value={searchUsername}
                onChange={(e) => setSearchUsername(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. john_doe"
                className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all placeholder-gray-400"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            id="btn-search-gnn"
            onClick={handleSearch}
            disabled={!hasSearchInput || loading}
            className={`px-6 py-2.5 text-sm font-semibold rounded-lg transition-all flex items-center gap-2 ${hasSearchInput && !loading
                ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
          >
            {loading ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                Searching...
              </>
            ) : (
              <>🔍 Search Network</>
            )}
          </button>

          {hasSearched && (
            <button
              id="btn-clear-search"
              onClick={handleClear}
              className="px-4 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50 transition-all"
            >
              ✕ Clear
            </button>
          )}

          {graphData && graphData.stats && (
            <div className="ml-auto flex gap-2">
              <span className="px-3 py-1.5 bg-purple-100 text-purple-700 rounded-full text-xs font-semibold">
                {graphData.stats.total_users || 0} Users
              </span>
              <span className="px-3 py-1.5 bg-emerald-100 text-emerald-700 rounded-full text-xs font-semibold">
                {graphData.stats.total_merchants || 0} Merchants
              </span>
              <span className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">
                {graphData.stats.total_transactions || 0} Transactions
              </span>
              {graphData._performance && (
                <span className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-xs font-semibold">
                  ⚡ {graphData._performance.total_ms}ms
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Graph Visualization */}
      <div className="card p-6 mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Network Visualization</h2>
        {loading ? (
          <div className="text-center py-32 text-gray-500">
            <div className="animate-spin inline-block w-8 h-8 border-4 border-current border-t-transparent rounded-full mb-2"></div>
            <p>Analyzing network connections...</p>
          </div>
        ) : graphData && graphData.nodes && graphData.nodes.length > 0 ? (
          <NetworkGraph data={graphData} />
        ) : (
          <div className="text-center py-32 bg-gray-50 rounded-xl border border-dashed border-gray-300">
            {hasSearched ? (
              <>
                <p className="text-5xl mb-4">📊</p>
                <p className="text-gray-500 font-medium">No network data found for this search</p>
                <p className="text-gray-400 text-sm mt-1">Try a different transaction ID, merchant, or username</p>
              </>
            ) : (
              <>
                <p className="text-5xl mb-4">🔍</p>
                <p className="text-gray-600 font-semibold text-lg">Enter a search query to visualize the fraud network</p>
                <p className="text-gray-400 text-sm mt-2 max-w-md mx-auto">
                  Search by Transaction ID, Merchant Name, or Username to load the network graph for that specific entity — no more waiting for all transactions to load.
                </p>
              </>
            )}
          </div>
        )}
      </div>

      {/* Detected Clusters */}
      {hasSearched && (
        <div className="card p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Detected Fraud Clusters</h2>
          {clusters.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {clusters.map((cluster) => (
                <div
                  key={cluster.cluster_id}
                  className="border border-gray-200 rounded-xl p-4 hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => handleExplainCluster(cluster)}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className={`px-3 py-1 rounded-lg text-xs font-bold ${cluster.risk_score > 80 ? 'bg-red-100 text-red-700' :
                      cluster.risk_score > 60 ? 'bg-orange-100 text-orange-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                      Cluster #{cluster.cluster_id}
                    </div>
                    <span className="text-2xl font-bold text-gray-900">{cluster.risk_score}</span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
                    <div className="text-center p-2 bg-blue-50 rounded">
                      <div className="font-bold text-blue-700">{cluster.user_count}</div>
                      <div className="text-gray-600">Users</div>
                    </div>
                    <div className="text-center p-2 bg-red-50 rounded">
                      <div className="font-bold text-red-700">{cluster.merchant_count}</div>
                      <div className="text-gray-600">Merchants</div>
                    </div>
                    <div className="text-center p-2 bg-green-50 rounded">
                      <div className="font-bold text-green-700">{cluster.device_count}</div>
                      <div className="text-gray-600">Devices</div>
                    </div>
                  </div>

                  <div className="p-2 bg-gray-50 rounded-lg mb-3 text-xs">
                    <div className="text-gray-600">Flagged Transactions</div>
                    <div className="font-bold text-gray-900">
                      {cluster.flagged_tx_count} / {cluster.total_tx_count}
                    </div>
                  </div>

                  <div className="p-2 bg-yellow-50 rounded-lg border border-yellow-200 text-xs">
                    <div className="font-semibold text-yellow-800 mb-1">Pattern</div>
                    <div className="text-yellow-900">{cluster.dominant_pattern}</div>
                  </div>

                  <button className="w-full mt-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors">
                    Explain →
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-gray-50 rounded-xl border border-dashed border-gray-300">
              <p className="text-gray-500">No fraud clusters detected for this search.</p>
            </div>
          )}
        </div>
      )}

      {/* Explanation Modal */}
      {showExplanation && selectedCluster && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
              <h3 className="text-xl font-bold text-gray-900">🔍 Cluster #{selectedCluster.cluster_id} Analysis</h3>
              <button
                onClick={() => setShowExplanation(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
              >
                ×
              </button>
            </div>

            <div className="p-6">
              {/* Cluster Summary */}
              <div className="bg-gray-50 rounded-xl p-4 mb-6">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 font-semibold">Risk Score:</span>
                    <span className="ml-2 font-bold text-red-600">{selectedCluster.risk_score}/100</span>
                  </div>
                  <div>
                    <span className="text-gray-500 font-semibold">Total Transactions:</span>
                    <span className="ml-2 text-gray-900">{selectedCluster.total_tx_count}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 font-semibold">Flagged:</span>
                    <span className="ml-2 font-bold text-gray-900">{selectedCluster.flagged_tx_count}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 font-semibold">Avg Amount:</span>
                    <span className="ml-2 font-bold text-gray-900">₹{selectedCluster.avg_amount.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* AI Explanation */}
              <div className="bg-white border border-gray-200 rounded-xl p-6">
                <h4 className="text-lg font-bold text-gray-900 mb-4">AI-Powered Network Analysis</h4>
                {loadingExplanation ? (
                  <div className="text-center py-8">
                    <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mb-2"></div>
                    <p className="text-gray-600 text-sm">Generating evidence-based explanation...</p>
                  </div>
                ) : (
                  <div className="prose prose-sm max-w-none">
                    <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">
                      {explanation}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4">
              <button
                onClick={() => setShowExplanation(false)}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminLayout>
  )
}
