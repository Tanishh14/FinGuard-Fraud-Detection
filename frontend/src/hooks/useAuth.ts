import { useAuthStore } from '../auth/auth.store'

export const useAuth = () => ({
  token: useAuthStore(s => s.token),
  role: useAuthStore(s => s.role),
  username: useAuthStore(s => s.username),
  email: useAuthStore(s => s.email),
  user_id: useAuthStore(s => s.user_id),
  is_loading: useAuthStore(s => s.is_loading),
  login: useAuthStore(s => s.login),
  logout: useAuthStore(s => s.logout)
})
