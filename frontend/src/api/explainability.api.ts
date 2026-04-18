import api from './axios'

export interface ExplanationResponse {
    transaction_id: number
    explanation: string
    timestamp: string
    model_version: string
}

export const getTransactionExplanation = async (transactionId: number) => {
    const { data } = await api.get<ExplanationResponse>(`/explainability/transaction/${transactionId}`)
    return data
}
