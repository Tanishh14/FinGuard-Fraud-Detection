import api from './axios'

export const fetchRiskGauges = async (threshold: number = 0.9) =>
    (await api.get(`/analytics/gauges?threshold=${threshold}`)).data

export const fetchFraudTrends = async (days: number = 30, threshold: number = 0.75) =>
    (await api.get(`/analytics/trends?days=${days}&threshold=${threshold}`)).data

export const fetchGeoStats = async (days: number = 30) =>
    (await api.get(`/analytics/geo?days=${days}`)).data



export const fetchTopMerchants = async (limit: number = 5) =>
    (await api.get(`/analytics/merchants?limit=${limit}`)).data

export const fetchForensics = async () =>
    (await api.get('/analytics/forensics')).data

export const fetchDashboardStats = async () =>
    (await api.get('/analytics/dashboard/stats')).data

export const fetchModelPerformance = async () =>
    (await api.get('/analytics/dashboard/model-performance')).data

export const fetchTopEntities = async (limit: number = 5) =>
    (await api.get(`/analytics/dashboard/top-entities?limit=${limit}`)).data

export const fetchCaseStats = async () =>
    (await api.get('/analytics/dashboard/case-stats')).data
