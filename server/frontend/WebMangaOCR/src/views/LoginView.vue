<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const router = useRouter()

const authStore = useAuthStore()

const submit = async () => {
  error.value = ''
  loading.value = true

  try {
    await authStore.login(username.value, password.value)
    router.push('/')
  } catch {
    error.value = 'Неверный email или пароль'
  } finally {
    loading.value = false
  }
}

const goToRegister = () => {
  router.push('/register')
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
    <div class="w-full max-w-md rounded-2xl bg-slate-800/80 backdrop-blur p-8 shadow-2xl">

      <!-- Заголовок -->
      <h1 class="text-2xl font-semibold text-white text-center mb-2">
        Добро пожаловать
      </h1>
      <p class="text-slate-400 text-center mb-6">
        Войдите в свой аккаунт
      </p>

      <!-- Ошибка -->
      <div
        v-if="error"
        class="mb-4 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-2 text-red-400 text-sm"
      >
        {{ error }}
      </div>

      <!-- Username -->
      <div class="mb-4">
        <label class="block text-sm text-slate-300 mb-1">E-MAIL</label>
        <input
          v-model="username"
          type="username"
          placeholder="you@example.com"
          class="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <!-- Password -->
      <div class="mb-6">
        <label class="block text-sm text-slate-300 mb-1">Пароль</label>
        <input
          v-model="password"
          type="password"
          placeholder="••••••••"
          class="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <!-- Login -->
      <button
        @click="submit"
        :disabled="loading"
        class="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 transition px-4 py-2 text-white font-medium mb-4"
      >
        {{ loading ? 'Входим...' : 'Войти' }}
      </button>

      <!-- Divider -->
      <div class="flex items-center gap-3 mb-4">
        <div class="flex-1 h-px bg-slate-700"></div>
        <span class="text-xs text-slate-500">или</span>
        <div class="flex-1 h-px bg-slate-700"></div>
      </div>

      <!-- Register -->
      <button
        @click="goToRegister"
        class="w-full rounded-lg border border-slate-600 hover:bg-slate-700 transition px-4 py-2 text-slate-200 font-medium"
      >
        Регистрация
      </button>

    </div>
  </div>
</template>
