<script setup>
import { ref } from 'vue'
import { useViewerStore } from '../stores/viewer'

const store = useViewerStore()

// Drag & drop
const isDraggingOver = ref(false)

const onDragOver = (e) => {
  e.preventDefault()
  isDraggingOver.value = true
}

const onDragLeave = () => {
  isDraggingOver.value = false
}

const onDrop = (e) => {
  store.handleDrop(e)
  isDraggingOver.value = false
}

// Отправка на сервер при выборе файла
const selectAndOcr = async (index) => {
  store.selectFile(index)
  
  const file = store.files[index]?.file  // оригинальный File
  if (!file || store.files[index].ocrData) return  // если уже есть OCR — не отправляем

  const formData = new FormData()
  formData.append('file', file)

}
</script>

<template>
  <div class="h-full bg-gray-950 p-4 flex flex-col gap-4 overflow-y-auto relative" @dragover="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
    <h3 class="text-lg font-semibold">Файлы</h3>

    <div class="flex-1 space-y-2 overflow-y-auto">
      <div
        v-for="(item, index) in store.files"
        :key="item.id"
        class="relative flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all hover:bg-gray-800/70 group"
        :class="{ 'bg-indigo-900/40 border border-indigo-600': store.selectedIndex === index, 'bg-gray-800/40': store.selectedIndex !== index }"
        @click="selectAndOcr(index)"
      >
        <div class="w-14 h-20 flex-shrink-0 rounded overflow-hidden bg-gray-700">
          <img :src="item.preview" alt="preview" class="w-full h-full object-cover" />
        </div>

        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium truncate">{{ item.name }}</p>
          <p class="text-xs text-gray-500">{{ item.size }}</p>
        </div>

        <button @click.stop="store.removeFile(index)" class="absolute top-1 right-1 opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition p-1 rounded-full hover:bg-gray-900/60" title="Удалить">
          ×
        </button>
      </div>

      <div v-if="store.files.length === 0" class="text-center text-gray-500 py-8">
        Нет загруженных файлов
      </div>
    </div>

    <div v-if="isDraggingOver" class="absolute inset-0 bg-indigo-500/20 border-2 border-indigo-500 rounded-lg flex items-center justify-center text-xl font-bold">
      Перетащите файлы сюда
    </div>
  </div>
</template>