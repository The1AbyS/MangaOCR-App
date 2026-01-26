<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { UserCircleIcon } from '@heroicons/vue/24/outline'

const authStore = useAuthStore()

const showMenu = ref(false)

const logout = () => {
  authStore.logout()
}

const toggleMenu = () => {
  showMenu.value = !showMenu.value
}
</script>

<template>
  <header class="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4 flex-shrink-0">
    <!-- Левая часть: кнопка "Мои проекты" -->
    <button class="px-4 py-1 bg-blue-600 text-white rounded hover:bg-blue-500 transition duration-200">
      Мои проекты
    </button>

    <!-- Правая часть: иконка пользователя с подменю -->
    <div class="relative">
        <button 
            @click="toggleMenu" 
            class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center 
                text-gray-300 hover:bg-gray-600 transition duration-200 
                hover:ring-2 hover:ring-offset-2 hover:ring-offset-gray-900 hover:ring-blue-500/60"
        >
            <img 
            v-if="authStore.user?.avatar" 
            :src="authStore.user.avatar" 
            class="w-full h-full object-cover"
            alt="Avatar"
            >
            <UserCircleIcon 
            v-else 
            class="w-8 h-8 text-gray-400"
            />
        </button>

      <!-- Выпадающее меню -->
      <div 
        v-if="showMenu" 
        class="absolute right-0 mt-2 w-40 bg-gray-800 border border-gray-700 rounded shadow-lg flex flex-col"
      >
        <button 
          class="px-4 py-2 text-white hover:bg-gray-700 transition duration-200 text-left"
        >
          Изменить пароль
        </button>
        <button 
          @click="logout" 
          class="px-4 py-2 text-white hover:bg-red-600 transition duration-200 text-left"
        >
          Выйти
        </button>
      </div>
    </div>
  </header>
</template>
