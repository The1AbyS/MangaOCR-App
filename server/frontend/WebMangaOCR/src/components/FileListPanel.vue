<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useFileCache } from '../composables/useFileCache'
import { useViewerStore } from '../stores/viewer.js'


const route = useRoute()

const projectId = route.params.projectId
const cache = useFileCache(projectId)

// Состояние viewer (selectedIndex, scale и т.д.)
const viewer = useViewerStore()

// Drag & drop
const isDraggingOver = ref(false)

const onDragOver = (e) => {
  e.preventDefault()
  isDraggingOver.value = true
}

const onDragLeave = () => {
  isDraggingOver.value = false
}

const onDrop = async (e) => {
  e.preventDefault()
  isDraggingOver.value = false
  
  const droppedFiles = Array.from(e.dataTransfer.files)
  if (droppedFiles.length === 0) return

  await viewer.addFiles(droppedFiles)

  // Автоматический выбор первого файла после добавления, если ничего не выбрано
  if (viewer.selectedIndex.value < 0 && viewer.files.value.length > 0) {
    viewer.selectFile(0)
  }
}

// Выбор файла
const selectAndOcr = (index) => {
  viewer.selectFile(index)
}


// Запуск очереди OCR после монтирования (если есть необработанные файлы)
cache.processOcrQueue((processedFile) => {
  // Когда файл обработан OCR → если он сейчас выбран, обновляем данные
  const currentIndex = viewer.selectedIndex.value
  if (
    currentIndex >= 0 &&
    cache.files.value[currentIndex]?.id === processedFile.id
  ) {
    // Здесь обновляем ocrData в viewer (если у тебя есть такая функция)
    viewer.ocrData = processedFile.ocrData  // или viewer.updateOcrData(...)
  }
})
</script>

<template>
  <div
    class="h-full bg-gray-950 p-4 flex flex-col gap-4 overflow-y-auto relative"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <h3 class="text-lg font-semibold">Файлы</h3>

    <div class="flex-1 space-y-2 overflow-y-auto">
      <!-- Список файлов из cache -->
      <div
        v-for="(item, index) in viewer.files"
        
        :key="item.id"
        class="relative flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all hover:bg-gray-800/70 group"
        :class="{
          'bg-indigo-900/40 border border-indigo-600': viewer.selectedIndex === index,
          'bg-gray-800/40': viewer.selectedIndex !== index
        }"
        @click="selectAndOcr(index)"
      >
        <div class="w-14 h-20 flex-shrink-0 rounded overflow-hidden bg-gray-700">
          <img
            v-if="item.preview"
            :src="item.preview"
            alt="preview"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full flex items-center justify-center text-gray-500 text-xs">
            ...
          </div>
        </div>

        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium truncate">{{ item.name }}</p>
          <p class="text-xs text-gray-500">{{ item.size }}</p>
        </div>

        <button
          @click.stop="viewer.removeFile(index)"
          class="absolute top-1 right-1 opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition p-1 rounded-full hover:bg-gray-900/60"
          title="Удалить"
        >
          ×
        </button>
      </div>

      <!-- Пустое состояние -->
      <div
        v-if="viewer.files.length === 0"
        class="text-center text-gray-500 py-8"
      >
        Нет загруженных файлов<br />
        <span class="text-xs">Перетащите изображения сюда или используйте кнопку в тулбаре</span>
      </div>
    </div>

    <!-- Оверлей при драге -->
    <div
      v-if="isDraggingOver"
      class="absolute inset-0 bg-indigo-500/20 border-2 border-indigo-500 rounded-lg flex items-center justify-center text-xl font-bold pointer-events-none"
    >
      Перетащите файлы сюда
    </div>
  </div>
</template>