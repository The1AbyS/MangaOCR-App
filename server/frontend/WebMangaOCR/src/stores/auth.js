import { defineStore } from 'pinia'
import { auth } from '../services/auth'
import router from '../router'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    initialized: false
  }),

  getters: {
    isAuthenticated: state => !!state.user
  },

  actions: {
    async init() {
      const accessToken = localStorage.getItem('access_token')
      if (!accessToken) {
        this.initialized = true
        return
      }

      try {
        this.user = await auth.me()
      } catch (e) {
        this.logout()
      } finally {
        this.initialized = true
      }
    },

    async login(username, password) {
      await auth.login(username, password)
      this.user = await auth.me() // получаем данные пользователя
      router.push('/')
    },

    async logout() {
      await auth.logout()
      this.user = null
      router.push('/login')
    }
  }
})
