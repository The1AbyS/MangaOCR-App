<script setup>
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useViewerStore } from '../stores/viewer.js'
import { useFileCache } from '../composables/useFileCache.js'

const route = useRoute()
const viewer = useViewerStore()
const cache = useFileCache(route.params.projectId)

const imgRef = ref(null)

// Коэффициенты масштабирования
const scaleX = ref(1)
const scaleY = ref(1)

// Текущее изображение
const currentImage = computed(() => {
  const idx = viewer.selectedIndex ?? -1

  if (idx < 0 || idx >= (viewer.files.length ?? 0)) {
    return null
  }

  const file = viewer.files[idx]
  if (!file?.preview) {
    console.log('[MangaViewer currentImage] preview отсутствует у файла')
    return null
  }

  return file.preview
})

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
  viewer.handleDrop(e)
  isDraggingOver.value = false
}

const clickBlock = (index) => {
  viewer.highlightBlock(index)
}

const currentOcrData = computed(() => {
  const data = viewer.ocrData
  console.log('Текущие OCR данные:', data)
  return data || { boxes: [], frames: [] }
})

// Функция пересчёта масштаба
const updateScale = () => {
  if (!imgRef.value) return

  const img = imgRef.value
  const naturalW = img.naturalWidth
  const naturalH = img.naturalHeight
  const displayedW = img.clientWidth
  const displayedH = img.clientHeight

  if (naturalW > 0 && naturalH > 0) {
    scaleX.value = displayedW / naturalW
    scaleY.value = displayedH / naturalH
  }
}

// Обновляем масштаб после монтирования и при ресайзе окна
onMounted(() => {
  // Если изображение уже загружено
  if (imgRef.value?.complete) {
    updateScale()
  }
  window.addEventListener('resize', updateScale)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateScale)
})

// При загрузке изображения
const onImageLoad = () => {
  updateScale()
}
</script>

<template>
  <div class="h-full flex items-center justify-center p-4 relative overflow-auto" @dragover="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
    <div v-if="currentImage" class="relative max-w-full max-h-full inline-block">
      <div
        class="transition-transform duration-200 ease-out inline-block"
        :style="{ transform: `scale(${viewer.scale / 100}) rotate(${viewer.rotation}deg)` }"
      >
        <!-- Основное изображение с ref -->
        <img
          ref="imgRef"
          :src="currentImage"
          alt="Manga page"
          class="max-h-[90vh] max-w-full object-contain select-none"
          draggable="false"
          @load="onImageLoad"
        />

        <!-- Контейнер оверлеев — привязан к размерам изображения -->
        <div
          class="absolute inset-0 pointer-events-none"
          :style="{
            width: imgRef?.clientWidth ? `${imgRef.clientWidth}px` : '100%',
            height: imgRef?.clientHeight ? `${imgRef.clientHeight}px` : '100%'
          }"
        >
          <!-- Боксы -->
          <div
            v-for="(box, index) in currentOcrData.boxes"
            :key="'box-' + index"
            class="absolute border-2 border-blue-500 hover:border-blue-400 cursor-pointer bg-blue-500/10 pointer-events-auto"
            :style="{
              left: `${box.x * scaleX}px`,
              top: `${box.y * scaleY}px`,
              width: `${box.w * scaleX}px`,
              height: `${box.h * scaleY}px`
            }"
            @click="clickBlock(index)"
            title="Клик → подсветить текст"
          ></div>

          <!-- Фреймы -->
          <div v-if="viewer.showFrames">
            <div
              v-for="(frame, index) in currentOcrData.frames"
              :key="'frame-' + index"
              class="absolute border-3 border-red-500 bg-red-500/10 pointer-events-auto"
              :style="{
                left: `${frame.x * scaleX}px`,
                top: `${frame.y * scaleY}px`,
                width: `${frame.w * scaleX}px`,
                height: `${frame.h * scaleY}px`
              }"
            ></div>
          </div>
        </div>
      </div>

      <!-- Кнопка toggle фреймов -->
      <button
        @click="viewer.toggleFrames"
        class="absolute top-4 right-4 z-10 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded shadow-lg"
      >
        {{ viewer.showFrames ? 'Скрыть фреймы' : 'Показать фреймы' }}
      </button>
    </div>

    <div v-else class="text-gray-500 text-xl">
      Выберите изображение из списка
    </div>

    <div v-if="isDraggingOver" class="absolute inset-0 bg-indigo-500/20 border-2 border-indigo-500 rounded-lg flex items-center justify-center text-xl font-bold pointer-events-none">
      Перетащите изображения сюда
    </div>

    <!-- Лоадер OCR обработки -->
    <div v-if="cache.isProcessingOcr.value" class="absolute inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center pointer-events-none">
      <div class="flex flex-col items-center gap-4">
        <div class="spinner">
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
        </div>
        <p class="text-white text-lg font-semibold">Обработка OCR...</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.spinner {
  position: relative;
  width: 80px;
  height: 80px;
}

.spinner-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 4px solid transparent;
  border-radius: 50%;
  border-top-color: #3b82f6;
  animation: spin 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
}

.spinner-ring:nth-child(1) {
  animation-delay: -0.45s;
}

.spinner-ring:nth-child(2) {
  animation-delay: -0.3s;
}

.spinner-ring:nth-child(3) {
  animation-delay: -0.15s;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>