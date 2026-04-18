import api from './axios'

export interface UserProfile {
    user_id: number
    email: string
    role: string
    profile: {
        avg_amount: number
        std_amount: number
        tx_count: number
        tx_per_day: number
        night_tx_ratio: number
        geo_entropy: number
        primary_location: string | null
        merchant_category_distribution: Record<string, number>
        last_updated: string
    }
    recent_activity: {
        transactions_30d: number
        flagged_30d: number
        fraud_rate_30d: number
    }
    created_at: string
}

export interface ProfileStatistics {
    user_id: number
    email: string
    period_days: number
    spending_stats: {
        total_amount: number
        avg_amount: number
        median_amount: number
        std_amount: number
        min_amount: number
        max_amount: number
        transaction_count: number
    }
    risk_stats: {
        avg_risk_score: number
        max_risk_score: number
        flagged_count: number
        blocked_count: number
        approved_count: number
    }
    merchant_distribution: Record<string, number>
    device_distribution: Record<string, number>
    hourly_pattern: Record<number, number>
}

export interface DriftAlert {
    user_id: number
    email: string
    baseline_avg: number
    recent_avg: number
    z_score: number
    drift_type: 'increase' | 'decrease'
    recent_tx_count: number
}

export const getUserProfile = async (userId: number) => {
    const { data } = await api.get<UserProfile>(`/profiles/user/${userId}`)
    return data
}

export const getProfileStatistics = async (userId: number, days = 90) => {
    const { data } = await api.get<ProfileStatistics>(
        `/profiles/statistics/${userId}`,
        { params: { days } }
    )
    return data
}

export const resetUserProfile = async (userId: number) => {
    const { data } = await api.post(`/profiles/reset/${userId}`)
    return data
}

export const getDriftAlerts = async (threshold = 3.0) => {
    const { data } = await api.get('/profiles/drift-alerts', {
        params: { threshold }
    })
    return data
}
