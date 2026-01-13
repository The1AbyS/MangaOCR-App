<script setup>
import { ref } from 'vue'
import { computed } from 'vue'
import { useViewerStore } from '../stores/viewer'

const store = useViewerStore()

// Вычисляем текущий файл
const currentImage = computed(() => {
  const idx = store.selectedIndex
  if (idx < 0 || idx >= store.files.length || !store.files) {
    return null
  }
  return store.files[idx]?.preview
})

// Drag & drop на viewer
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
</script>

<template>
  <div
    class="h-full flex items-center justify-center p-4 relative overflow-auto"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <div v-if="currentImage" class="max-w-full max-h-full">
      <div
        class="transition-transform duration-200 ease-out"
        :style="{
          transform: `scale(${store.scale / 100}) rotate(${store.rotation}deg)`
        }"
      >
        <img
          :src="currentImage"
          alt="Manga page"
          class="max-h-[90vh] object-contain select-none"
          draggable="false"
        />
      </div>
    </div>

    <div v-else class="text-gray-500 text-xl">
      Выберите изображение из списка
    </div>

    <!-- Оверлей для drag & drop -->
    <div
      v-if="isDraggingOver"
      class="absolute inset-0 bg-indigo-500/20 border-2 border-indigo-500 rounded-lg flex items-center justify-center text-xl font-bold"
    >
      Перетащите изображения сюда
    </div>
  </div>
</template>