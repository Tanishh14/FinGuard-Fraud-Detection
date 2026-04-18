import api from './axios'

export interface SystemMetrics {
    timestamp: string
    transactions: {
        total: number
        last_hour: number
        last_24h: number
        hourly_rate: number
        daily_rate: number
    }
    fraud_metrics: {
        flagged_24h: number
        blocked_24h: number
        fraud_rate_24h: number
        avg_risk_score_24h: number
    }
    users: {
        total: number
        by_role: Record<string, number>
    }
    merchants: {
        total: number
        high_risk: Array<{
            name: string
            transaction_count: number
            avg_risk_score: number
        }>
    }
    database: {
        status: string
        connected: boolean
        pool_size?: number
        checked_out?: number
    }
    configuration: {
        risk_thresholds: Record<string, number>
        fusion_weights: Record<string, number>
    }
}

export interface RiskThresholdUpdate {
    approved_max?: number
    flagged_max?: number
    amount_z_score_max?: number
    amount_ratio_max?: number
}

export interface UserListItem {
    id: number
    email: string
    role: string
    transaction_count: number
    avg_amount: number
    created_at: string
}

export const getSystemMetrics = async () => {
    const { data } = await api.get<SystemMetrics>('/admin/metrics')
    return data
}

export const getDetailedHealth = async () => {
    const { data } = await api.get('/admin/health')
    return data
}

export const updateThresholds = async (updates: RiskThresholdUpdate) => {
    const { data } = await api.post('/admin/thresholds', updates)
    return data
}

export const listUsers = async (params?: {
    role?: string
    limit?: number
    offset?: number
}) => {
    const { data } = await api.get('/admin/users', { params })
    return data
}

export const changeUserRole = async (userId: number, role: string) => {
    const { data } = await api.post(`/admin/users/${userId}/role`, { role })
    return data
}
