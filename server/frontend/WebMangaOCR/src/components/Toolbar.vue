<script setup>
import { ref } from 'vue'
import { useViewerStore } from '../stores/viewer'
import { useAuthStore } from '../stores/auth'
import { useRoute } from 'vue-router'

const props = defineProps({
  projectTitle: {
    type: String,
    default: 'Без названия'
  }
})

const store = useViewerStore()

const authStore = useAuthStore()

const fileInput = ref()
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

const goProjectView = () => {
  window.location.href = '/'
}


</script>

<template>
<header class="h-14 bg-gray-900 border-b border-gray-800 flex items-center px-4 flex-shrink-0">
  <!-- Левая часть (кнопки навигации и открытия) -->
  <div class="flex items-center gap-3">
    <button @click="goProjectView" class="p-2 hover:bg-gray-800 rounded transition" title="Назад к проектам">
      <span class="text-xl">⬅️</span>
    </button>
    <button @click="openFileDialog" class="p-2 hover:bg-gray-800 rounded transition" title="Открыть файлы">
      <span class="text-xl">📁</span>
    </button>
  </div>

  <!-- Центр — название проекта (полная ширина, центрировано) -->
  <div class="flex-1 flex justify-center items-center min-w-0">
    <h2 class="text-lg font-semibold truncate max-w-[60vw] text-center">
      {{ projectTitle || 'Проект без названия' }}
    </h2>
  </div>

  <!-- Правая часть (управление + выход) -->
  <div class="flex items-center gap-3">
    <button @click="store.zoomIn" class="p-2 hover:bg-gray-800 rounded transition" title="Увеличить">+</button>
    <button @click="store.zoomOut" class="p-2 hover:bg-gray-800 rounded transition" title="Уменьшить">-</button>
    <button @click="store.rotate" class="p-2 hover:bg-gray-800 rounded transition" title="Повернуть">↻</button>

    <div class="flex items-center gap-2 ml-2">
      <span class="text-sm text-gray-400">Масштаб:</span>
      <span class="text-sm font-medium">{{ store.scale }}%</span>
    </div>

    <button @click="logout" class="ml-4 px-4 py-1 bg-red-600 text-white rounded hover:bg-red-500 transition">
      Выйти
    </button>
  </div>

  <input ref="fileInput" type="file" accept="image/*" multiple class="hidden" @change="handleFileSelect" />
</header>
</template>
