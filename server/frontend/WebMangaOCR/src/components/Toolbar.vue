<script setup>
import { ref } from 'vue'
import { useViewerStore } from '../stores/viewer'
import { useAuthStore } from '../stores/auth'

const store = useViewerStore()
const authStore = useAuthStore()

const fileInput = ref(null)

const openFileDialog = () => {
  fileInput.value?.click()
}

const handleFileSelect = (e) => {
  const files = e.target.files
  if (!files || files.length === 0) return

  store.addFiles(Array.from(files))
  e.target.value = ''
}

// SPA-logout через Pinia
const logout = () => {
  authStore.logout()
}
</script>

<template>
  <header class="h-14 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-3 flex-shrink-0">
    <!-- Кнопка открытия файлов -->
    <button @click="openFileDialog" class="p-2 hover:bg-gray-800 rounded transition duration-200" title="Открыть файл(ы)">
      <span class="text-xl">📁</span>
    </button>
    <input ref="fileInput" type="file" accept="image/*" multiple class="hidden" @change="handleFileSelect" />

    <div class="flex-1"></div>

    <!-- Кнопки управления изображением -->
    <button @click="store.zoomIn" class="p-2 hover:bg-gray-800 rounded transition duration-200" title="Увеличить">+</button>
    <button @click="store.zoomOut" class="p-2 hover:bg-gray-800 rounded transition duration-200" title="Уменьшить">-</button>
    <button @click="store.rotate" class="p-2 hover:bg-gray-800 rounded transition duration-200" title="Повернуть на 90°">↻</button>

    <div class="flex items-center gap-2 ml-4">
      <span class="text-sm text-gray-400">Масштаб:</span>
      <span class="text-sm font-medium">{{ store.scale }}%</span>
    </div>

    <!-- Кнопка выхода -->
    <button 
      @click="logout" 
      class="ml-4 px-4 py-1 bg-red-600 text-white rounded hover:bg-red-500 transition duration-200"
    >
      Выйти
    </button>
  </header>
</template>
