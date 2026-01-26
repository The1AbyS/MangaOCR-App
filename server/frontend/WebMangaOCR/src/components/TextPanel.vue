<script setup>
import { computed } from 'vue'
import { useViewerStore} from '../stores/viewer'
import { useRoute } from 'vue-router'

const route = useRoute()
const store = useViewerStore()

// Текущий текст = текст выбранного файла или заглушка
const currentOcrData = computed(() => store.ocrData)
</script>

<template>
  <div class="h-full bg-gray-950 p-4 flex flex-col gap-4 overflow-y-auto">
    <h3 class="text-lg font-semibold">Извлечённый текст</h3>

    <div class="flex-1 bg-gray-900 rounded-lg p-4 text-gray-200 whitespace-pre-wrap font-mono text-sm leading-relaxed overflow-auto">
      <p v-for="(box, index) in currentOcrData?.boxes" :key="index" :class="{ 'bg-yellow-600/50': index === store.highlightedBlock }">
        {{ box.text }}
      </p>

      <p v-if="!currentOcrData">Нет распознанного текста</p>
    </div>

    <div class="flex gap-2">
      <button class="flex-1 py-2 bg-gray-800 hover:bg-gray-700 rounded">Копировать</button>
      <button class="flex-1 py-2 bg-indigo-700 hover:bg-indigo-600 rounded">Перевести</button>
    </div>
  </div>
</template>