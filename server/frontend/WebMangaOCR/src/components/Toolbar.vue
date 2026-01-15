<script setup>
import { ref } from 'vue'
import { useViewerStore } from '../stores/viewer'

const store = useViewerStore()

const fileInput = ref(null)

// Открытие диалога файлов
const openFileDialog = () => {
  fileInput.value?.click()
}

// Обработка выбранных файлов (добавляем в store)
const handleFileSelect = (e) => {
  const files = e.target.files
  if (!files || files.length === 0) return

  store.addFiles(Array.from(files))
  e.target.value = ''
}
</script>

<template>
  <header class="h-14 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-3 flex-shrink-0">
    <!-- Кнопка открытия файлов -->
    <button @click="openFileDialog" class="p-2 hover:bg-gray-800 rounded transition" title="Открыть файл(ы)">
      <span class="text-xl">📁</span>
    </button>

    <input ref="fileInput" type="file" accept="image/*" multiple class="hidden" @change="handleFileSelect" />

    <!-- Кнопка настроек (временно пустышка)
    <button class="p-2 hover:bg-gray-800 rounded transition" title="Настройки">
      <span class="text-xl">⚙️</span>
    </button>
    -->
    <div class="flex-1"></div>
    <!-- Управление изображением (зум, поворот) -->
    <button @click="store.zoomIn" class="p-2 hover:bg-gray-800 rounded transition" title="Увеличить">
      <span class="text-xl">+</span>
    </button>

    <button @click="store.zoomOut" class="p-2 hover:bg-gray-800 rounded transition" title="Уменьшить">
      <span class="text-xl">-</span>
    </button>

    <button @click="store.rotate" class="p-2 hover:bg-gray-800 rounded transition" title="Повернуть на 90°">
      <span class="text-xl">↻</span>
    </button>

    <div class="flex items-center gap-2 ml-4">
      <span class="text-sm text-gray-400">Масштаб:</span>
      <span class="text-sm font-medium">{{ store.scale }}%</span>
    </div>
  </header>
</template>