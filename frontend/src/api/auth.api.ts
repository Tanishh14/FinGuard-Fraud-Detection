import api from './axios'

export const loginApi = async (email: string, password: string) =>
  (await api.post('/auth/login', { email, password })).data

export const registerApi = async (payload: any) =>
  (await api.post('/auth/register', payload)).data

export const toggle2faApi = async () =>
  (await api.post('/auth/toggle-2fa')).data

export const verifyOtpApi = async (email: string, otp_code: string, otp_type: string) =>
  (await api.post('/auth/verify-otp', { email, otp_code, otp_type })).data

export const verifyAppealOtpApi = async (email: string, otp_code: string, otp_type: string = 'appeal') =>
  (await api.post('/transactions/verify-report-appeal-otp', { email, otp_code, otp_type })).data

export const getMeApi = async () =>
  (await api.get('/auth/me')).data

export const logoutApi = async () =>
  (await api.post('/auth/logout')).data
