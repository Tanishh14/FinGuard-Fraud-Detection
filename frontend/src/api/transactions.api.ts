import api from './axios'

export const sendTransaction = async (payload: any) =>
  (await api.post('/transactions/', payload)).data

export interface TransactionFilters {
  username?: string
  merchant?: string
  min_amount?: number
  max_amount?: number
  risk_level?: string
}

export const getTransactionCount = async (filters: TransactionFilters = {}) =>
  (await api.get('/transactions/count', { params: filters })).data

export const fetchTransactions = async (page = 1, pageSize = 200, filters: TransactionFilters = {}) =>
  (await api.get('/transactions/all', { params: { page, page_size: pageSize, ...filters } })).data

export const approveTransaction = async (txId: number) =>
  (await api.post(`/transactions/${txId}/approve`)).data

export const blockTransaction = async (txId: number) =>
  (await api.post(`/transactions/${txId}/block`)).data

export const verifyTransaction = async (txId: number) =>
  (await api.post(`/transactions/${txId}/verify`)).data

export const appealTransaction = async (txId: number, payload: { reason: string, urgency: string }) =>
  (await api.post(`/transactions/${txId}/appeal`, payload)).data

export const reportTransaction = async (txId: number, payload: { reason: string, urgency: string }) =>
  (await api.post(`/transactions/${txId}/report`, payload)).data

export const verifyReportAppealOTP = async (payload: { email: string, otp_code: string, otp_type: string }) =>
  (await api.post(`/transactions/verify-report-appeal-otp`, payload)).data
