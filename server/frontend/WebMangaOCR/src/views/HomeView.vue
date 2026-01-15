<script setup>
import Toolbar       from '../components/Toolbar.vue'
import FileListPanel from '../components/FileListPanel.vue'
import MangaViewer   from '../components/MangaViewer.vue'
import TextPanel     from '../components/TextPanel.vue'

import { useViewerStore } from '../stores/viewer'

const store = useViewerStore()
</script>

<template>
  <div class="h-screen w-screen flex flex-col bg-gray-950 text-gray-100 overflow-hidden">
    <!-- Верхняя панель -->
    <Toolbar />

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

        <!-- Правая панель (пока статичная, можно позже связать с OCR) -->
        
      </div>
      <TextPanel class="w-80 flex-shrink-0 border-l border-gray-800" />
    </div>
  </div>
</template>