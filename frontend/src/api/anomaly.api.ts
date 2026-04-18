import api from './axios'

export interface AnomalyDetectionRequest {
    user_id: number
    merchant: string
    amount: number
    device_id?: string
    location?: string
    ip_address?: string
    timestamp?: string
}

export interface AnomalyDetectionResponse {
    status: string
    ae_score: number
    if_score: number
    combined_score: number
    is_anomaly: boolean
    interpretation: string
    user_baseline: {
        avg_amount: number | null
        std_amount: number | null
        tx_count: number
    }
    timestamp: string
}

export interface AnomalyPattern {
    transaction_id: number
    user_id: number
    amount: number
    merchant: string
    anomaly_score: number
    decision: string
    pattern_type: string
    timestamp: string
}

export const detectAnomaly = async (request: AnomalyDetectionRequest) => {
    const { data } = await api.post<AnomalyDetectionResponse>(
        '/anomaly/detection',
        request
    )
    return data
}

export async function getAnomalyPatterns(days: number = 30, limit: number = 50) {
    const response = await api.get(`/anomaly/patterns?days=${days}&limit=${limit}`)
    return response.data
}

export async function explainTransaction(transactionId: number) {
    const response = await api.post(`/anomaly/${transactionId}/explain`)
    return response.data
}

export async function generateSAR(transactionId: number) {
    const response = await api.post(`/anomaly/${transactionId}/generate-sar`)
    return response.data
}

export const getUserAnomalyHistory = async (
    userId: number,
    days = 90,
    limit = 100
) => {
    const { data } = await api.get(`/anomaly/user/${userId}`, {
        params: { days, limit }
    })
    return data
}
