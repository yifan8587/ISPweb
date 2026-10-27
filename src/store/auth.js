import { defineStore } from 'pinia'
import { getMe, login as loginApi } from '@/api'
import { clearActivity, markActivity } from '@/utils/idleSession'

const LS_ACCESS = 'ispweb_access'
const LS_REFRESH = 'ispweb_refresh'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem(LS_ACCESS) || '',
    refreshToken: localStorage.getItem(LS_REFRESH) || '',
    user: null,
    capabilities: null,
  }),
  getters: {
    isLoggedIn: (s) => !!s.accessToken,
    displayName: (s) => s.user?.customer_name || s.user?.full_name || s.user?.username || '用户',
    isCustomer: (s) => s.user?.account_type === 'customer' || s.user?.is_superuser,
  },
  actions: {
    setTokens(access, refresh) {
      this.accessToken = access
      this.refreshToken = refresh
      localStorage.setItem(LS_ACCESS, access)
      localStorage.setItem(LS_REFRESH, refresh)
    },
    setAccess(access) {
      this.accessToken = access
      localStorage.setItem(LS_ACCESS, access)
    },
    async login(username, password) {
      const res = await loginApi({ username, password })
      const data = res.data || res
      this.setTokens(data.access, data.refresh)
      this.user = data.user
      this.capabilities = null
      markActivity()
      return data.user
    },
    setCapabilities(capabilities) {
      this.capabilities = capabilities || null
    },
    async fetchMe() {
      if (!this.accessToken) return null
      const res = await getMe()
      this.user = res.data || res
      return this.user
    },
    logout() {
      this.accessToken = ''
      this.refreshToken = ''
      this.user = null
      this.capabilities = null
      localStorage.removeItem(LS_ACCESS)
      localStorage.removeItem(LS_REFRESH)
      clearActivity()
    },
  },
})
