<script setup>
import { ref } from 'vue'
import { computed } from 'vue'
import { useViewerStore } from '../stores/viewer'  // подкорректируй путь если нужно

const store = useViewerStore()

// Текущий текст = текст выбранного файла или заглушка
const currentOcrText = computed(() => {
  if (store.selectedIndex < 0 || !store.files.length) {
    return 'Выберите изображение слева, чтобы увидеть распознанный текст'
  }
  return store.files[store.selectedIndex]?.ocrText || 'Текст ещё не распознан'
})
</script>

<template>
  <div class="h-full bg-gray-950 p-4 flex flex-col gap-4 overflow-y-auto border-l border-gray-800">
    <h3 class="text-lg font-semibold">Извлечённый текст</h3>

    <div 
      class="flex-1 bg-gray-900 rounded-lg p-5 text-gray-200 whitespace-pre-wrap font-mono text-sm leading-relaxed overflow-auto"
    >
      {{ currentOcrText }}
    </div>

    <div class="flex gap-2">
      <button class="flex-1 py-2.5 bg-gray-800 hover:bg-gray-700 rounded transition">
        Копировать
      </button>
      <button class="flex-1 py-2.5 bg-indigo-700 hover:bg-indigo-600 rounded transition">
        Перевести
      </button>
    </div>
  </div>
</template>