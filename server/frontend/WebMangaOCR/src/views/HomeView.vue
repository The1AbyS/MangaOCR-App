<script setup>
import { useRoute } from 'vue-router'
import { ref, provide, onMounted, watch } from 'vue'

import Toolbar       from '../components/Toolbar.vue'
import FileListPanel from '../components/FileListPanel.vue'
import MangaViewer   from '../components/MangaViewer.vue'
import TextPanel     from '../components/TextPanel.vue'

import { useViewerStore } from '../stores/viewer'
import { useFileCache } from '../composables/useFileCache'
import shigureGif from '../assets/shigure.gif'

const projectTitle = ref('Загрузка...')
const route = useRoute()
const projectId = route.params.projectId
const cache = useFileCache(projectId)
const store = useViewerStore()

const loadTitle = () => {
  const saved = localStorage.getItem('my-manga-projects')
  if (!saved) {
    projectTitle.value = 'Нет проектов'
    return
  }

  try {
    const projects = JSON.parse(saved)
    const found = projects.find(p => String(p.id) === projectId)
    console.log('Загруженный проект:', found, 'И porjectId=', projectId)
    projectTitle.value = found ? found.title : 'Проект не найден'
  } catch (e) {
    console.error('Ошибка:', e)
    projectTitle.value = 'Ошибка'
  }
}

onMounted(loadTitle)

watch(route.params.projectId, loadTitle)

</script>

<template>
  <div class="h-screen w-screen flex flex-col bg-gray-950 text-gray-100 overflow-hidden">
    <!-- Верхняя панель -->
    <Toolbar :project-title="projectTitle"/>

    <!-- Основной контент -->
    <div class="flex flex-1 overflow-hidden">
      <FileListPanel class="w-64 flex-shrink-0 border-r border-gray-800" />

      <div class="flex-1 flex flex-col bg-gray-900">
        <!-- Показываем выбранное изображение или заглушку -->
        <div v-if="store.selectedIndex >= 0" class="flex-1 overflow-auto p-4">
          <MangaViewer class="flex-1 overflow-hidden bg-gray-900"/>
        </div>
        <div v-else class="flex-1 flex items-center justify-center">
          <!-- Лоадер OCR обработки -->
          <div v-if="store.isProcessingOcr" class="flex flex-col items-center gap-4">
            <img :src="shigureGif" alt="Loading" class="w-64 h-64 object-contain rounded-lg shadow-lg" />
            <p class="text-white text-lg font-semibold">Обработка OCR...</p>
          </div>
          <!-- Текст при отсутствии файлов -->
          <div v-else class="text-gray-500 text-xl">
            Загрузите изображения через кнопку 📁 или перетащите файлы
          </div>
        </div>

        <!-- Правая панель -->
        
      </div>
      <TextPanel class="w-80 flex-shrink-0 border-l border-gray-800" />
    </div>
  </div>
</template>

<style scoped>
/* Красивый скролбар */
.overflow-auto::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.overflow-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-auto::-webkit-scrollbar-thumb {
  background: #4b5563;
  border-radius: 3px;
  transition: background 0.3s ease;
}

.overflow-auto::-webkit-scrollbar-thumb:hover {
  background: #6b7280;
}

/* Для Firefox */
.overflow-auto {
  scrollbar-width: thin;
  scrollbar-color: #4b5563 transparent;
}
</style>