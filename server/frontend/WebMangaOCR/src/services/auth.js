import axios from 'axios'

const API_URL = 'http://192.168.0.31:8000/v1'

const api = axios.create({
  baseURL: API_URL
})

// 🔑 request interceptor — добавляем access_token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 🔁 response interceptor — ловим 401 и пробуем обновить access_token
api.interceptors.response.use(
  res => res,
  async error => {
    const original = error.config

    // проверяем что это первый retry
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        return Promise.reject(error)
      }

      try {
        const { data } = await api.post('/refresh', { refresh_token: refreshToken })
        localStorage.setItem('access_token', data.access_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return api(original) // повторяем исходный запрос
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  }
)

export const auth = {
  async login(username, password) {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)

    const { data } = await api.post('/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    console.log("login data:", data, data.access_token, data.refresh_token)
    return data
  },

  async register(email, username, password) {
    const { data } = await api.post('/register', { email, username, password })
    return data
  },

  async me() {
    const { data } = await api.get('/me')
    return data
  },

  async logout() {
    try {
      await api.post('/logout')
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }
}
