import api from './axios'

export interface FraudRing {
    ring_id: number
    size: number
    avg_risk_score: number
    members: string[]
    member_count: number
}

export interface UserConnection {
    user_id: number
    email: string
    merchants: Array<{
        merchant_name: string
        transaction_count: number
        total_amount: number
        avg_risk_score: number
    }>
    devices: Array<{
        device_id: string
        transaction_count: number
        avg_risk_score: number
    }>
    linked_users: Array<{
        user_id: number
        email: string
    }>
    stats: {
        total_transactions: number
        avg_risk_score: number
        flagged_count: number
        period_days: number
    }
}

export interface RiskHotspot {
    type: string
    name: string
    transaction_count: number
    avg_risk_score: number
    flagged_count: number
    fraud_rate: number
}

export const getFraudRings = async (params?: {
    days?: number
    min_ring_size?: number
    risk_threshold?: number
}) => {
    const { data } = await api.get('/gnn/fraud-rings', { params })
    return data
}

export const getUserConnections = async (userId: number, days = 90) => {
    const { data } = await api.get(`/gnn/user-connections/${userId}`, {
        params: { days }
    })
    return data as UserConnection
}

export const getRiskPropagation = async (days = 30) => {
    const { data } = await api.get('/gnn/risk-propagation', { params: { days } })
    return data
}

export const getGraphData = async (days: number = 30) => {
    const response = await api.get('/gnn/graph-data', {
        params: { days }
    })
    return response.data
}

export const getClusterAnalysis = async (params: {
    days?: number
    min_cluster_size?: number
    risk_threshold?: number
}) => {
    const response = await api.get('/gnn/cluster-analysis', { params })
    return response.data
}

export const explainCluster = async (clusterId: number) => {
    const response = await api.post('/gnn/explain-cluster', { cluster_id: clusterId })
    return response.data
}

export interface SearchParams {
    transaction_id?: number
    merchant_name?: string
    username?: string
}

export const searchGraphData = async (params: SearchParams) => {
    const response = await api.get('/gnn/graph-data/search', { params })
    return response.data
}

export const searchClusterAnalysis = async (params: SearchParams & {
    min_cluster_size?: number
    risk_threshold?: number
}) => {
    const response = await api.get('/gnn/cluster-analysis/search', { params })
    return response.data
}
