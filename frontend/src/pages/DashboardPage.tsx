import { useState, useEffect } from 'react';
import AdminLayout from '../layouts/AdminLayout';
import StatCard from '../components/StatCard';
import RiskGauge from '../components/RiskGauge';
import {
  fetchDashboardStats,
  fetchModelPerformance,
  fetchTopEntities,
  fetchCaseStats,
  fetchFraudTrends
} from '../api/analytics.api';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { exportTransactionPDF } from '../api/reports.api';
import type { ReportParams } from '../api/reports.api';

// Types
interface DashboardStats {
  kpi: {
    total_24h: number;
    approved_rate: number;
    blocked_rate: number;
    review_rate: number;
    avg_anomaly_score: number;
    active_high_risk_users: number;
    active_fraud_rings: number;
  };
  live_graph: {
    time: string;
    APPROVED: number;
    BLOCKED: number;
    FLAGGED: number;
  }[];
}

interface ModelPerf {
  autoencoder_deviation: number;
  gnn_risk_intensity: number;
  isolation_forest_anomaly: number;
  avg_final_risk: number;
}

interface TopEntities {
  users: any[];
  merchants: any[];
  devices: any[];
}

interface CaseStats {
  open_cases: number;
  pending_reviews: number;
  resolved_today: number;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [modelPerf, setModelPerf] = useState<ModelPerf | null>(null);
  const [topEntities, setTopEntities] = useState<TopEntities | null>(null);
  const [caseStats, setCaseStats] = useState<CaseStats | null>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Reporting State
  const [reportParams, setReportParams] = useState<ReportParams>({
    time_range: '7d',
    username: ''
  });
  const [generating, setGenerating] = useState(false);

  const loadAll = async () => {
    try {
      const [statsData, modelData, entityData, caseData, trendData] = await Promise.all([
        fetchDashboardStats(),
        fetchModelPerformance(),
        fetchTopEntities(),
        fetchCaseStats(),
        fetchFraudTrends(7, 0.5) // Last 7 days for trend view
      ]);
      setStats(statsData || null);
      setModelPerf(modelData || null);
      setTopEntities(entityData || null);
      setCaseStats(caseData || null);
      setTrends(trendData || []);
    } catch (err) {
      console.error("Dashboard load failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) return (
    <AdminLayout>
      <div className="flex flex-col items-center justify-center h-[80vh]">
        <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
        <p className="text-gray-500 font-bold uppercase tracking-widest">Loading Unified Intelligence...</p>
      </div>
    </AdminLayout>
  );

  if (!stats && !loading) return (
    <AdminLayout>
      <div className="flex flex-col items-center justify-center h-[80vh] text-center">
        <div className="text-6xl mb-4">⚠️</div>
        <h3 className="text-xl font-black text-gray-900 uppercase">Dashboard Unavailable</h3>
        <p className="text-gray-500 mb-6">Unable to load real-time intelligence streams.</p>
        <button
          onClick={() => { setLoading(true); loadAll(); }}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg font-bold uppercase tracking-widest hover:bg-blue-700 transition-colors"
        >
          Retry Connection
        </button>
      </div>
    </AdminLayout>
  );

  // Live Graph Helper: Max Value for Scaling
  const liveGraph = stats?.live_graph || [];
  const maxGraphVal = Math.max(...liveGraph.map(d => (d.APPROVED || 0) + (d.BLOCKED || 0) + (d.FLAGGED || 0)), 5);

  return (
    <AdminLayout>
      {/* Header */}
      <div className="flex justify-between items-end mb-8">
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-[10px] font-bold uppercase tracking-widest">
            Last Update: {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* A. SYSTEM HEALTH SUMMARY (KPI CARDS) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="24h Transactions"
          value={(stats?.kpi?.total_24h || 0).toLocaleString()}
          icon="📊"
          color="blue"
        />
        <StatCard
          title="Block Rate (24h)"
          value={`${stats?.kpi?.blocked_rate || 0}%`}
          icon="🛡️"
          color={(stats?.kpi?.blocked_rate || 0) > 5 ? 'red' : 'green'}
        />
        <StatCard
          title="Active Fraud Rings"
          value={(stats?.kpi?.active_fraud_rings || 0).toString()}
          icon="🔗"
          color="orange"
        />
        <StatCard
          title="High Risk Users"
          value={(stats?.kpi?.active_high_risk_users || 0).toString()}
          icon="⚠️"
          color="red"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* B. REAL-TIME TRANSACTION FLOW (LIVE GRAPH) */}
        <div className="lg:col-span-2 card p-6 bg-white shadow-lg border border-gray-100 rounded-3xl">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest">Real-Time Transaction Flow (Last 60m)</h3>
            <div className="flex gap-4 text-[10px] font-bold uppercase">
              <span className="flex items-center gap-1"><span className="w-2 h-2 bg-green-400 rounded-full"></span> Approved</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 bg-yellow-400 rounded-full"></span> Review</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-500 rounded-full"></span> Blocked</span>
            </div>
          </div>

          <div className="h-64 flex items-end justify-between gap-1 relative pt-6">
            {/* Y-Axis Grid Lines (Mock) */}
            <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-10">
              {[1, 0.75, 0.5, 0.25, 0].map((p, i) => (
                <div key={i} className="w-full border-t border-gray-500 h-0"></div>
              ))}
            </div>

            {(liveGraph).map((pt, i) => {
              const total = (pt.APPROVED || 0) + (pt.BLOCKED || 0) + (pt.FLAGGED || 0);
              const hApp = ((pt.APPROVED || 0) / maxGraphVal) * 100;
              const hRev = ((pt.FLAGGED || 0) / maxGraphVal) * 100;
              const hBlk = ((pt.BLOCKED || 0) / maxGraphVal) * 100;

              return (
                <div key={i} className="flex-1 flex flex-col justify-end h-full gap-[1px] group relative min-w-[4px]">
                  {/* Tooltip */}
                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-[10px] p-2 rounded opacity-0 group-hover:opacity-100 z-10 whitespace-nowrap pointer-events-none">
                    <div className="font-bold border-b border-gray-700 pb-1 mb-1">{pt.time}</div>
                    <div>✅ {pt.APPROVED || 0}</div>
                    <div>⚠️ {pt.FLAGGED || 0}</div>
                    <div>⛔ {pt.BLOCKED || 0}</div>
                  </div>

                  {/* Stacked Bars */}
                  {(pt.BLOCKED || 0) > 0 && <div style={{ height: `${hBlk}%` }} className="w-full bg-red-500 rounded-t-sm opacity-90 hover:opacity-100"></div>}
                  {(pt.FLAGGED || 0) > 0 && <div style={{ height: `${hRev}%` }} className="w-full bg-yellow-400 opacity-90 hover:opacity-100"></div>}
                  {(pt.APPROVED || 0) > 0 && <div style={{ height: `${hApp}%` }} className="w-full bg-green-400 rounded-b-sm opacity-90 hover:opacity-100"></div>}
                </div>
              );
            })}
          </div>
        </div>

        {/* F. ALERT & CASE OVERVIEW */}
        <div className="flex flex-col gap-6">
          <div className="card p-6 bg-slate-900 text-white rounded-3xl shadow-xl relative overflow-hidden">
            <div className="absolute -right-6 -top-6 w-32 h-32 bg-blue-500/20 rounded-full blur-2xl"></div>
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Investigator Status</h3>
            <div className="space-y-4 relative z-10">
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-xl border border-slate-700">
                <span className="text-sm font-bold text-slate-300">Open Cases</span>
                <span className="text-xl font-black text-white">{caseStats?.open_cases || 0}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-xl border border-slate-700">
                <span className="text-sm font-bold text-slate-300">Pending Reviews</span>
                <span className="text-xl font-black text-yellow-400">{caseStats?.pending_reviews || 0}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-xl border border-slate-700">
                <span className="text-sm font-bold text-slate-300">Resolved Today</span>
                <span className="text-xl font-black text-green-400">{caseStats?.resolved_today || 0}</span>
              </div>
            </div>
            <button onClick={() => navigate('/live-transactions')} className="w-full mt-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-xs font-black uppercase tracking-widest transition-all">
              Review Transactions
            </button>
          </div>

          {/* D. MODEL PERFORMANCE SNAPSHOT */}
          <div className="card p-6 bg-white rounded-3xl shadow-lg border border-gray-100">
            <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-4">AI Model Health</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-gray-600">Avg Risk Level</span>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-24 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500" style={{ width: `${(modelPerf?.avg_final_risk || 0) * 100}%` }}></div>
                  </div>
                  <span className="text-xs font-bold text-blue-600">{(modelPerf?.avg_final_risk || 0).toFixed(2)}</span>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-gray-600">GNN Intensity</span>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-24 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500" style={{ width: `${(modelPerf?.gnn_risk_intensity || 0) * 100}%` }}></div>
                  </div>
                  <span className="text-xs font-bold text-purple-600">{(modelPerf?.gnn_risk_intensity || 0).toFixed(2)}</span>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-gray-600">Anomaly Deviation</span>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-24 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-orange-500" style={{ width: `${(modelPerf?.autoencoder_deviation || 0) * 100}%` }}></div>
                  </div>
                  <span className="text-xs font-bold text-orange-600">{(modelPerf?.autoencoder_deviation || 0).toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* REPORTING SECTION */}
        <div className="card p-6 bg-white rounded-3xl shadow-lg border border-gray-100 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xl">📄</span>
              <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Generate Transaction Report</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-[9px] font-black text-gray-400 uppercase mb-1 block">Time Range</label>
                <select
                  value={reportParams.time_range}
                  onChange={(e) => setReportParams({ ...reportParams, time_range: e.target.value as any })}
                  className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2 text-xs font-bold focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <option value="24h">Last 24 Hours</option>
                  <option value="7d">Last 7 Days</option>
                  <option value="monthly">Monthly Report</option>
                  <option value="yearly">Yearly Summary</option>
                </select>
              </div>

              <div>
                <label className="text-[9px] font-black text-gray-400 uppercase mb-1 block">Filter by Username (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. jsmith"
                  value={reportParams.username}
                  onChange={(e) => setReportParams({ ...reportParams, username: e.target.value })}
                  className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2 text-xs font-bold focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>
            </div>
          </div>

          <button
            onClick={async () => {
              setGenerating(true);
              try {
                await exportTransactionPDF(reportParams, token);
              } catch (err) {
                console.error("Report generation failed:", err);
                alert("Failed to generate report. Please ensure you have Admin/Analyst privileges.");
              } finally {
                setGenerating(false);
              }
            }}
            disabled={generating}
            className={`w-full mt-6 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${generating
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-[0.98]'
              }`}
          >
            {generating ? (
              <>
                <div className="w-3 h-3 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
                Generating...
              </>
            ) : (
              <>
                <span>📥</span> Generate PDF Report
              </>
            )}
          </button>
        </div>

        {/* E. TOP RISK ENTITIES */}
        <div className="card p-6 bg-white rounded-3xl shadow-lg border border-gray-100 h-96 overflow-hidden flex flex-col lg:col-span-2">
          <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-4">Top 5 Risk Contributors (Last 7 Days)</h3>

          <div className="flex-1 overflow-y-auto pr-2">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-white">
                <tr>
                  <th className="text-[9px] font-black uppercase text-gray-400 pb-2 border-b border-gray-100">Entity</th>
                  <th className="text-[9px] font-black uppercase text-gray-400 pb-2 border-b border-gray-100 text-right">Count</th>
                  <th className="text-[9px] font-black uppercase text-gray-400 pb-2 border-b border-gray-100 text-right">Max Risk</th>
                </tr>
              </thead>
              <tbody className="text-xs font-medium text-gray-700">
                {/* Users */}
                {topEntities?.users.map((u) => (
                  <tr key={`u-${u.id}`} className="group hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0 cursor-pointer" onClick={() => navigate('/gnn-fraud-rings')}>
                    <td className="py-3 flex items-center gap-2">
                      <span className="w-6 h-6 rounded bg-blue-100 text-blue-600 flex items-center justify-center text-[10px] font-bold">U</span>
                      User #{u.id}
                    </td>
                    <td className="py-3 text-right">{u.count}</td>
                    <td className="py-3 text-right font-bold text-red-600">{(u.risk * 100).toFixed(0)}</td>
                  </tr>
                ))}
                {/* Merchants */}
                {topEntities?.merchants.map((m) => (
                  <tr key={`m-${m.name}`} className="group hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0">
                    <td className="py-3 flex items-center gap-2">
                      <span className="w-6 h-6 rounded bg-orange-100 text-orange-600 flex items-center justify-center text-[10px] font-bold">M</span>
                      {m.name}
                    </td>
                    <td className="py-3 text-right">{m.count}</td>
                    <td className="py-3 text-right font-bold text-red-600">{(m.risk * 100).toFixed(0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* C. FRAUD TREND ANALYTICS (Historical) */}
        <div className="card p-6 bg-white rounded-3xl shadow-lg border border-gray-100 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Fraud Block Rate (Last 7 Days)</h3>
            <span className="text-[10px] bg-gray-100 px-2 py-1 rounded text-gray-600 font-bold">Historical</span>
          </div>

          <div className="flex-1 flex items-end gap-3 pb-2 border-b border-gray-100 relative">
            {trends.length > 0 ? trends.map((day, i) => {
              const maxTotal = Math.max(...trends.map(t => t.total), 1);
              const hTotal = (day.total / maxTotal) * 100;
              const hBlock = (day.blocked / dailyMax(day)) * 100; // Relative to bar height

              function dailyMax(d: any) { return Math.max(d.total, 1); }

              return (
                <div key={i} className="flex-1 flex flex-col justify-end group h-full relative">
                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-[10px] p-2 rounded opacity-0 group-hover:opacity-100 z-10 whitespace-nowrap">
                    {new Date(day.date).toLocaleDateString()}<br />
                    Total: {day.total}<br />
                    Blocked: {day.blocked}
                  </div>
                  <div style={{ height: `${hTotal}%` }} className="w-full bg-blue-100 rounded-lg relative overflow-hidden transition-all hover:bg-blue-200">
                    <div style={{ height: `${(day.blocked / day.total) * 100}%` }} className="absolute bottom-0 w-full bg-red-400 transition-all"></div>
                  </div>
                  <span className="text-[8px] text-gray-400 font-bold text-center mt-2 uppercase">{new Date(day.date).toLocaleDateString(undefined, { weekday: 'short' })}</span>
                </div>
              );
            }) : (
              <div className="w-full h-full flex items-center justify-center text-gray-300 font-black text-xs uppercase">No Data Available</div>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
