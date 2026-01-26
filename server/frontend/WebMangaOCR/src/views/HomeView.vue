<script setup>
import { useRoute } from 'vue-router'
import { ref, provide, onMounted, watch } from 'vue'

import Toolbar       from '../components/Toolbar.vue'
import FileListPanel from '../components/FileListPanel.vue'
import MangaViewer   from '../components/MangaViewer.vue'
import TextPanel     from '../components/TextPanel.vue'

import { useViewerStore } from '../stores/viewer'

const projectTitle = ref('Загрузка...')
const route = useRoute()
const projectId = route.params.projectId

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

const store = useViewerStore()

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
        <div v-else class="flex-1 flex items-center justify-center text-gray-500 text-xl">
          Загрузите изображения через кнопку 📁 или перетащите файлы
        </div>

        <!-- Правая панель -->
        
      </div>
      <TextPanel class="w-80 flex-shrink-0 border-l border-gray-800" />
    </div>
  </div>
</template>