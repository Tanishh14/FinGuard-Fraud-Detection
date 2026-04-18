import { useNavigate } from 'react-router-dom'
import { FixedSizeList, ListChildComponentProps } from 'react-window'
import { memo } from 'react'

interface Intelligence {
  labels: string[]
  boosters: { type: 'SUCCESS' | 'WARNING' | 'INFO'; label: string }[]
  breakdown: Record<string, number>
}

interface Transaction {
  id: number
  txId?: string
  user_id: number
  user?: string
  merchant: string
  amount: number
  risk?: number
  risk_score?: number
  final_risk_score?: number
  status: 'APPROVED' | 'BLOCKED' | 'FLAGGED' | 'REVIEW' | 'UNDER REVIEW' | 'PENDING'
  decision?: string
  device_id?: string
  ip_address?: string
  location?: string
  timestamp?: string
  username?: string
  intelligence?: Intelligence
  sparkline?: number[]
}

interface Props {
  transactions?: Transaction[]
  onSelectTransaction?: (tx: Transaction) => void
  height?: number
}

const Sparkline = ({ data }: { data: number[] }) => {
  if (!data || data.length === 0) return <div className="text-[10px] text-gray-300">N/A</div>
  const max = Math.max(...data, 1)
  return (
    <div className="flex items-end gap-0.5 h-6 w-16 px-1">
      {data.map((val, i) => (
        <div
          key={i}
          className="bg-blue-400/50 w-full rounded-t-sm"
          style={{ height: `${(val / max) * 100}%` }}
        ></div>
      ))}
    </div>
  )
}

const getRiskBand = (risk: number) => {
  if (risk >= 85) return {
    bg: 'bg-red-500/10',
    border: 'border-red-500/20',
    text: 'text-red-600',
    bar: 'bg-red-500',
    icon: '🚨',
    animate: 'animate-pulse'
  }
  if (risk >= 60) return {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    text: 'text-orange-600',
    bar: 'bg-orange-500',
    icon: '⚠️'
  }
  if (risk >= 30) return {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    text: 'text-yellow-600',
    bar: 'bg-yellow-500',
    icon: '🔔'
  }
  return {
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    text: 'text-emerald-600',
    bar: 'bg-emerald-500',
    icon: '✅'
  }
}

const getDisplayRisk = (tx: Transaction) => {
  const risk = tx.final_risk_score ?? tx.risk_score ?? tx.risk ?? 0
  return risk > 1 ? risk : risk * 100
}

const getDisplayAmount = (tx: Transaction) => {
  return `₹${(tx.amount || 0).toLocaleString('en-IN')}`
}

// Separate Row component for performance (memoized)
const Row = memo(({ index, style, data }: ListChildComponentProps) => {
  const { transactions, onSelectTransaction } = data
  const tx = transactions?.[index]

  if (!tx) return null

  const risk = getDisplayRisk(tx)
  const band = getRiskBand(risk)
  const user = tx.username || tx.user || `User #${tx.user_id}`

  return (
    <div
      style={style}
      onClick={() => onSelectTransaction?.(tx)}
      className={`flex items-center group cursor-pointer border-b border-gray-100 hover:bg-gray-50 transition-all duration-300 ${risk >= 85 ? 'bg-red-50/30' : ''}`}
    >
      {/* User & Metrics */}
      <div className="w-[20%] px-6 py-4 flex items-center gap-4">
        <div className={`w-8 h-8 rounded-xl flex-shrink-0 flex items-center justify-center font-black text-xs text-white shadow-lg rotate-3 group-hover:rotate-0 transition-transform duration-500 bg-gradient-to-br ${risk >= 70 ? 'from-red-600 to-pink-700' : 'from-blue-600 to-indigo-700'}`}>
          {user.substring(0, 1).toUpperCase()}
        </div>
        <div className="min-w-0">
          <div className="text-[11px] font-black text-gray-900 group-hover:text-blue-600 transition-colors uppercase tracking-tight truncate">{user}</div>
          <div className="flex items-center gap-2 mt-1">
            <Sparkline data={tx.sparkline || []} />
          </div>
        </div>
      </div>

      {/* Merchant Info */}
      <div className="w-[14%] px-6 py-4">
        <div className="text-[11px] font-black text-gray-800 uppercase tracking-tight truncate">{tx.merchant}</div>
        <div className="text-[8px] font-black text-gray-400 uppercase tracking-widest mt-0.5 truncate">{tx.location || "Remote"}</div>
      </div>

      {/* Payment */}
      <div className="w-[12%] px-6 py-4">
        <div className="text-md font-black text-gray-900 tracking-tighter italic">{getDisplayAmount(tx)}</div>
        <div className="text-[8px] font-black text-gray-400 uppercase tracking-widest mt-0.5 font-mono">ID: {tx.id}</div>
      </div>

      {/* A.I. Risk Verdict */}
      <div className="w-[18%] px-6 py-4">
        <div className="flex flex-col gap-1 min-w-[100px]">
          <div className="flex items-center gap-2 text-[10px]">
            <span className={`${band.text} font-black`}>
              {risk.toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden border border-gray-100">
            <div
              className={`${band.bar} h-full transition-all duration-1000`}
              style={{ width: `${Math.min(risk, 100)}%` }}
            ></div>
          </div>
          <span className="text-[8px] font-black text-gray-400 uppercase tracking-tighter">Model Confidence: High</span>
        </div>
      </div>

      {/* Decision */}
      <div className="w-[15%] px-6 py-4">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest shadow-sm border
            ${tx.decision === 'BLOCKED' ? 'bg-red-50 text-red-600 border-red-100' :
                tx.decision === 'REVIEW' || tx.decision === 'REVIEW_NEEDED' || tx.decision === 'FLAGGED' ? 'bg-amber-50 text-amber-600 border-amber-100' :
                    'bg-emerald-50 text-emerald-600 border-emerald-100'}`}>
            {tx.decision === 'BLOCKED' ? '🔴 BLOCKED' :
                tx.decision === 'REVIEW' || tx.decision === 'REVIEW_NEEDED' || tx.decision === 'FLAGGED' ? '🟡 REVIEW' :
                    '🟢 APPROVED'}
        </span>
      </div>

      {/* Intelligence */}
      <div className="w-[15%] px-6 py-4">
        <div className="flex flex-wrap gap-1 max-w-[150px]">
          {tx.intelligence?.labels.slice(0, 2).map((label: string, i: number) => (
            <span key={i} className="px-1.5 py-0.5 bg-gray-100 text-gray-700 text-[8px] font-black rounded border border-gray-200 uppercase tracking-tighter">
              {label}
            </span>
          ))}
          {(!tx.intelligence || tx.intelligence.labels.length === 0) && (
            <span className="text-[10px] text-gray-300 italic">...</span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="w-[6%] px-6 py-4 text-center">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelectTransaction?.(tx);
          }}
          className="w-8 h-8 rounded-xl bg-gray-50 hover:bg-blue-600 hover:text-white text-gray-400 transition-all duration-300 font-black shadow-sm group-hover:shadow-blue-100 hover:-translate-y-0.5"
        >
          🔍
        </button>
      </div>
    </div>
  )
})

Row.displayName = 'TransactionRow'

export default function TransactionsTable({ transactions = [], onSelectTransaction, height = 600 }: Props) {
  // Use useMemo for list data to avoid re-renders
  const listData = {
    transactions,
    onSelectTransaction
  }

  return (
    <div className="card shadow-2xl rounded-3xl overflow-hidden border-0 bg-white">
      {/* Header */}
      <div className="flex bg-gray-900 text-white border-b-4 border-blue-600 font-black text-[10px] uppercase tracking-widest italic">
        <div className="w-[20%] px-6 py-4">User & Metrics</div>
        <div className="w-[14%] px-6 py-4">Merchant</div>
        <div className="w-[12%] px-6 py-4">Payment</div>
        <div className="w-[18%] px-6 py-4">A.I. Verdict</div>
        <div className="w-[15%] px-6 py-4">Decision</div>

        <div className="w-[15%] px-6 py-4 truncate">Intelligence</div>
        <div className="w-[6%] px-6 py-4 text-center">Actions</div>
      </div>

      {transactions && transactions.length > 0 ? (
        <FixedSizeList
          height={height}
          itemCount={transactions.length}
          itemSize={85}
          width="100%"
          itemData={listData}
        >
          {Row}
        </FixedSizeList>
      ) : (
        <div className="px-6 py-20 text-center">
          <div className="flex flex-col items-center gap-3">
            <div className="text-4xl">🌑</div>
            <div className="text-xs font-black text-gray-400 uppercase tracking-[0.2em]">Void Monitor - No Activity Detected</div>
          </div>
        </div>
      )}
    </div>
  )
}
