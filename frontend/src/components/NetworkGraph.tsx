import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface Node {
    id: string;
    label: string;
    type: 'user' | 'merchant' | 'device';
    val: number;
    x?: number;
    y?: number;
    risk_score?: number;
    merchant_count?: number;
    device_count?: number;
    user_count?: number;
    avg_amount?: number;
    anomaly_rate?: number;
    risk_amplifier?: number;
    risk_contribution?: number;
    tx_count?: number;
    color?: string;
    opacity?: number;
}

interface Link {
    source: string;
    target: string;
    tx_count?: number;
    avg_amount?: number;
    risk?: number;
    risk_contribution?: number;
}

interface GraphData {
    nodes: Node[];
    links: Link[];
}

interface ClusterSummary {
    cluster_id: number;
    risk_score: number;
    user_count: number;
    merchant_count: number;
    device_count: number;
    flagged_tx_count: number;
    total_tx_count: number;
    dominant_pattern: string;
}

export default function NetworkGraph({ data }: { data: GraphData }) {
    const fgRef = useRef<any>();
    const [showLabels, setShowLabels] = useState(true);
    const [selectedCluster, setSelectedCluster] = useState<ClusterSummary | null>(null);
    const [highlightedNode, setHighlightedNode] = useState<string | null>(null);
    const [hoveredLink, setHoveredLink] = useState<Link | null>(null);

    // Calculate top 10% risk threshold - memoized
    const top10Threshold = useMemo(() => {
        const riskScores = data?.nodes?.map(n => n.risk_score || 0) || [];
        const sortedRisks = [...riskScores].sort((a, b) => b - a);
        return sortedRisks[Math.floor(sortedRisks.length * 0.1)] || 70;
    }, [data]);

    // Process data with colors and opacity - memoized to prevent re-renders on hover
    const processedData = useMemo(() => {
        return {
            nodes: (data?.nodes || []).map(node => {
                const isHighRisk = (node.risk_score || 0) >= top10Threshold;
                const baseColor = node.type === 'user' ? '#3B82F6' : (node.type === 'merchant' ? '#EF4444' : '#10B981');

                return {
                    ...node,
                    color: baseColor,
                    opacity: isHighRisk ? 1.0 : 0.7  // Increased opacity for visibility
                };
            }),
            links: (data?.links || []).map(link => ({
                ...link,
                color: (link.risk || 0) > 0.7 ? '#EF4444' :
                    (link.risk || 0) > 0.4 ? '#F59E0B' : '#3B82F6',
                width: Math.max(1, (link.tx_count || 1) * 0.5)
            }))
        };
    }, [data, top10Threshold]);

    // Center on highest-risk node + DISABLE PHYSICS after stabilization
    useEffect(() => {
        if (fgRef.current && processedData.nodes.length > 0) {
            const highestRiskNode = processedData.nodes[0];
            if (highestRiskNode) {
                setTimeout(() => {
                    fgRef.current?.centerAt(highestRiskNode.x, highestRiskNode.y, 1000);
                    fgRef.current?.zoom(2, 1000);

                    // PERFORMANCE: Stop physics simulation after initial layout
                    setTimeout(() => {
                        fgRef.current?.d3Force('charge', null);
                        fgRef.current?.d3Force('link', null);
                    }, 3000);  // Allow 3s for stabilization
                }, 500);
            }
        }
    }, [data]);

    const getNodeLabel = useCallback((node: any) => {
        if (!showLabels) return '';

        // Removed the top 10% restriction so all nodes show info when labels are ON
        if (node.type === 'user') {
            return `${node.label}\nRisk: ${node.risk_score || 0} | M: ${node.merchant_count || 0} | D: ${node.device_count || 0}`;
        } else if (node.type === 'merchant') {
            return `${node.label}\nAvg ₹${(node.avg_amount || 0).toLocaleString()} | Anomaly: ${node.anomaly_rate || 0}%`;
        } else if (node.type === 'device') {
            return `${node.label}\nUsers: ${node.user_count || 0} | Risk +${node.risk_amplifier || 0}%`;
        }
        return node.label || 'Unknown Entity';
    }, [showLabels]);

    const renderNodeCanvas = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const label = getNodeLabel(node);
        const fontSize = 12 / globalScale;
        const isHighlighted = node.id === highlightedNode;

        // Draw node circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.val || 5, 0, 2 * Math.PI, false);
        ctx.fillStyle = node.color;
        ctx.globalAlpha = node.opacity;
        ctx.fill();

        // Highlight border
        if (isHighlighted) {
            ctx.strokeStyle = '#FBBF24';
            ctx.lineWidth = 4 / globalScale;
            ctx.stroke();
        }

        ctx.globalAlpha = 1.0;

        // Draw label with background
        if (label && showLabels) {
            ctx.font = `bold ${fontSize}px Inter, system-ui, sans-serif`;
            const lines = label.split('\n');
            const lineHeight = fontSize * 1.2;

            lines.forEach((line: string, i: number) => {
                const textWidth = ctx.measureText(line).width;
                const bckgDimensions = [textWidth + fontSize * 0.5, fontSize + 2];

                ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
                ctx.beginPath();
                const radius = 4 / globalScale;
                const x = node.x - bckgDimensions[0] / 2;
                const y = node.y - node.val - (lines.length - i) * lineHeight - 2;
                const w = bckgDimensions[0];
                const h = bckgDimensions[1];

                // Rounded rect for label
                ctx.moveTo(x + radius, y);
                ctx.lineTo(x + w - radius, y);
                ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
                ctx.lineTo(x + w, y + h - radius);
                ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
                ctx.lineTo(x + radius, y + h);
                ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
                ctx.lineTo(x, y + radius);
                ctx.quadraticCurveTo(x, y, x + radius, y);
                ctx.closePath();
                ctx.fill();

                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#111827';
                ctx.fillText(line, node.x, node.y - node.val - (lines.length - i - 0.5) * lineHeight - 2);
            });
        }
    }, [highlightedNode, showLabels, getNodeLabel]);

    return (
        <div className="relative w-full h-[700px] bg-gray-50 rounded-3xl overflow-hidden shadow-inner border border-gray-200">


            {/* Link Hover Info */}
            {hoveredLink && (
                <div className="absolute bottom-6 left-6 z-10 bg-white/90 backdrop-blur-xl p-4 rounded-2xl shadow-2xl border border-blue-100 w-64 animate-in fade-in slide-in-from-bottom duration-300">
                    <div className="text-[9px] font-black text-blue-600 uppercase tracking-widest mb-2">Connection Metadata</div>
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <div className="text-[8px] text-gray-400 font-bold uppercase">Transactions</div>
                            <div className="text-sm font-black text-gray-900">{hoveredLink.tx_count || 0}</div>
                        </div>
                        <div>
                            <div className="text-[8px] text-gray-400 font-bold uppercase">Avg Amount</div>
                            <div className="text-sm font-black text-gray-900">₹{Math.round(hoveredLink.avg_amount || 0).toLocaleString()}</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Force Graph */}
            <ForceGraph2D
                ref={fgRef}
                graphData={processedData as any}
                nodeRelSize={6}
                nodeCanvasObject={renderNodeCanvas}
                nodePointerAreaPaint={(node: any, color, ctx) => {
                    ctx.fillStyle = color;
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, (node.val || 5) + 2, 0, 2 * Math.PI, false);
                    ctx.fill();
                }}
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={1}
                linkCurvature={0.2}
                linkColor={(link: any) => link.color}
                linkWidth={(link: any) => link.width}
                onNodeClick={(node: any) => {
                    setHighlightedNode(node.id);
                    fgRef.current?.centerAt(node.x, node.y, 800);
                    fgRef.current?.zoom(3, 800);
                }}
                onLinkHover={setHoveredLink}
                backgroundColor="#f8fafc"
                d3AlphaDecay={0.02}
                d3VelocityDecay={0.3}
            />
        </div>
    );
}
