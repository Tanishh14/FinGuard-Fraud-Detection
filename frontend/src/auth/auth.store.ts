import { create } from 'zustand'
import { getMeApi, logoutApi } from '../api/auth.api'

export type Role = 'admin' | 'user' | 'fraud_analyst' | 'auditor' | 'end_user'

interface AuthState {
  token: string | null
  role: Role | null
  username: string | null
  email: string | null
  user_id: number | null
  is_2fa_enabled: boolean
  is_loading: boolean
  login: (token: string, role: Role, username: string, email: string, user_id: number, is_2fa_enabled: boolean) => void
  logout: () => void
  set2faEnabled: (enabled: boolean) => void
  initializeFromStorage: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => {
  // Initialize from sessionStorage on first load
  const loadFromStorage = () => {
    try {
      const stored = sessionStorage.getItem('auth')
      if (stored) {
        const { token, role, username, email, user_id, is_2fa_enabled } = JSON.parse(stored)
        // Restore token from storage if available
        return { token: token || null, role, username, email, user_id, is_2fa_enabled: !!is_2fa_enabled }
      }
    } catch (e) {
      console.error('Failed to load auth from storage:', e)
    }
    return { token: null, role: null, username: null, email: null, user_id: null, is_2fa_enabled: false }
  }

  const initialState = loadFromStorage()

  return {
    token: initialState.token,
    role: initialState.role,
    username: initialState.username,
    email: initialState.email,
    user_id: initialState.user_id,
    is_2fa_enabled: initialState.is_2fa_enabled,
    is_loading: true,

    login: (token, role, username, email, user_id, is_2fa_enabled) => {
      // Store token in sessionStorage so it stays within this tab
      // This allows different roles in different tabs
      sessionStorage.setItem('auth', JSON.stringify({ token, role, username, email, user_id, is_2fa_enabled }))
      set({ token, role, username, email, user_id, is_2fa_enabled, is_loading: false })
    },

    logout: () => {
      sessionStorage.removeItem('auth')
      logoutApi().catch(() => { }) // Best effort to clear cookie
      set({ token: null, role: null, username: null, email: null, user_id: null, is_2fa_enabled: false, is_loading: false })
    },

    set2faEnabled: (enabled) => {
      const stored = sessionStorage.getItem('auth')
      if (stored) {
        const parsed = JSON.parse(stored)
        sessionStorage.setItem('auth', JSON.stringify({ ...parsed, is_2fa_enabled: enabled, token: parsed.token }))
      }
      set({ is_2fa_enabled: enabled })
    },

    initializeFromStorage: async () => {
      const state = loadFromStorage()
      if (state.user_id) {
        set({ ...state, is_loading: true })
        try {
          // If we have local info, verify it with the server
          const user = await getMeApi()
          set({
            token: state.token,  // Preserve the token from storage
            role: user.role as Role,
            username: user.username,
            email: user.email,
            user_id: user.id,
            is_2fa_enabled: user.is_2fa_enabled,
            is_loading: false
          })
        } catch (e) {
          console.error('Session verification failed on init:', e)
          sessionStorage.removeItem('auth')
          set({ token: null, role: null, username: null, email: null, user_id: null, is_loading: false })
        }
      } else {
        set({ ...state, is_loading: false })
      }
    }
  }
})
