import axios from 'axios'

const API_URL = 'http://192.168.0.31:8000/v1'

const api = axios.create({
  baseURL: API_URL
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const auth = {
  async login(username, password) {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)

    const { data } = await api.post('/login', form, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })

    localStorage.setItem('token', data.access_token)
    return data
  },

  async register(email, username, password) {
    const { data } = await api.post('/register', {
      email,
      username,
      password
    })
    return data
  },

  // 👤 ME
  async me() {
    const { data } = await api.get('/me')
    return data
  },

  // 🚪 LOGOUT
  async logout() {
    try {
      await api.post('/logout')
    } finally {
      localStorage.removeItem('token')
    }
  },

  getToken() {
    return localStorage.getItem('token')
  },

  isAuthenticated() {
    return !!this.getToken()
  }
}
