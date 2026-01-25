<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../services/auth'

const email = ref('')
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const router = useRouter()

const submit = async () => {
  error.value = ''
  loading.value = true

  try {
    await auth.register(email.value, username.value, password.value)
    router.push('/login')
  } catch (e) {
    error.value = 'Не удалось зарегистрироваться. Возможно, email или username уже используется.'
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
    <div class="w-full max-w-md rounded-2xl bg-slate-800/80 backdrop-blur p-8 shadow-2xl">
      <h1 class="text-2xl font-semibold text-white text-center mb-2">Создать аккаунт</h1>
      <p class="text-slate-400 text-center mb-6">Регистрация нового пользователя</p>

      <div v-if="error" class="mb-4 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-2 text-red-400 text-sm">
        {{ error }}
      </div>

      <!-- Email -->
      <div class="mb-4">
        <label class="block text-sm text-slate-300 mb-1">Email</label>
        <input v-model="email" type="email" placeholder="you@example.com"
          class="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
      </div>

      <!-- Username -->
      <div class="mb-4">
        <label class="block text-sm text-slate-300 mb-1">Username</label>
        <input v-model="username" type="text" placeholder="Ваш никнейм"
          class="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
      </div>

      <!-- Password -->
      <div class="mb-6">
        <label class="block text-sm text-slate-300 mb-1">Пароль</label>
        <input v-model="password" type="password" placeholder="Минимум 6 символов"
          class="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
      </div>

      <!-- Register -->
      <button @click="submit" :disabled="loading"
        class="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 transition px-4 py-2 text-white font-medium mb-4">
        {{ loading ? 'Создаём аккаунт...' : 'Зарегистрироваться' }}
      </button>

      <div class="flex items-center gap-3 mb-4">
        <div class="flex-1 h-px bg-slate-700"></div>
        <span class="text-xs text-slate-500">уже есть аккаунт?</span>
        <div class="flex-1 h-px bg-slate-700"></div>
      </div>

      <button @click="goToLogin"
        class="w-full rounded-lg border border-slate-600 hover:bg-slate-700 transition px-4 py-2 text-slate-200 font-medium">
        Войти
      </button>
    </div>
  </div>
</template>
