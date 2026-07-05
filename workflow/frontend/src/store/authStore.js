import { create } from 'zustand'
import axios from 'axios'

const BASE = 'http://localhost:8000'

const useAuthStore = create((set, get) => ({
  user: null,
  token: null,
  isLoading: false,
  error: null,

  init() {
    const token = localStorage.getItem('wf-token')
    const user  = JSON.parse(localStorage.getItem('wf-user') || 'null')
    if (token && user) {
      set({ token, user })
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    }
  },

  async login(email, password) {
    set({ isLoading: true, error: null })
    try {
      const { data } = await axios.post(`${BASE}/auth/login`, { email, password })
      localStorage.setItem('wf-token', data.token)
      localStorage.setItem('wf-user', JSON.stringify(data.user))
      axios.defaults.headers.common['Authorization'] = `Bearer ${data.token}`
      set({ token: data.token, user: data.user, isLoading: false })
      return true
    } catch (err) {
      set({ isLoading: false, error: err.response?.data?.detail || 'Login failed' })
      return false
    }
  },

  async logout() {
    const { token } = get()
    if (token) {
      try { await axios.post(`${BASE}/auth/logout`) } catch (_) {}
    }
    localStorage.removeItem('wf-token')
    localStorage.removeItem('wf-user')
    delete axios.defaults.headers.common['Authorization']
    set({ user: null, token: null })
  },

  // Update the logged-in user's display name
  async updateProfile(name) {
    const { user } = get()
    if (!user) return false
    try {
      const { data } = await axios.put(`${BASE}/users/${user.id}`, {
        name,
        email: user.email,
        role:  user.role,
      })
      const updated = { ...user, name: data.name ?? name }
      localStorage.setItem('wf-user', JSON.stringify(updated))
      set({ user: updated })
      return true
    } catch (_) {
      return false
    }
  },

  // Change the logged-in user's password
  async updatePassword(newPassword) {
    const { user } = get()
    if (!user) return false
    try {
      await axios.patch(
        `${BASE}/users/${user.id}/password`,
        null,
        { params: { new_password: newPassword } },
      )
      return true
    } catch (_) {
      return false
    }
  },

  isAuthenticated: () => !!get().token,
  hasRole:         (...roles) => roles.includes(get().user?.role),
  isAdmin:         () => ['product_admin', 'process_admin'].includes(get().user?.role),
  isProductAdmin:  () => get().user?.role === 'product_admin',
}))

export default useAuthStore
