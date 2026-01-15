import { defineStore } from 'pinia'
import { ref } from 'vue'
import { computed } from 'vue'
import { useFileCache } from '../composables/useFileCache'

export const useViewerStore = defineStore('viewer', () => {

  const ocrData = ref(null)  // { boxes, frames } для текущего файла
  const showFrames = ref(false)  // toggle для frames
  const highlightedBlock = ref(-1)  // индекс подсвеченного блока

  const cache = useFileCache()

  const selectedIndex = ref(-1)
  const scale = ref(100)
  const rotation = ref(0)

  // Прокидываем файлы из кэша
  const files = computed(() => cache.files.value ?? [])

  // Добавление файлов в кэш
  const addFiles = async (newFiles) => {
    await cache.addFiles(newFiles)
    if (selectedIndex.value === -1 && files.value.length > 0) {
      selectedIndex.value = 0
    }
  }
  // Удаление файлов из кэша
  const removeFile = async (index) => {
    const fileId = files.value[index]?.id
    if (!fileId) return
    await cache.removeFile(fileId)

    if (selectedIndex.value === index) {
      selectedIndex.value = Math.min(files.value.length - 1, index)
    } else if (selectedIndex.value > index) {
      selectedIndex.value--
    }
  }

  // Обновляем данные боксов и фреймов из IndexedDB
  const updateOcrData = (data) => {
      ocrData.value = data
    }

  // Переключатель фреймов (False по умолчанию)
  const toggleFrames = () => {
    showFrames.value = !showFrames.value
  }

  // Подсветка текста выбранного блока
  const highlightBlock = (blockIndex) => {
    highlightedBlock.value = blockIndex
  }

  // Выбор файлов
  const selectFile = (index) => {
    selectedIndex.value = index
    ocrData.value = files.value[index]?.ocrData || null
    highlightedBlock.value = -1
  }

  // Обновление текста OCR
  const updateOcrText = async (index, text) => {
    const fileId = files.value[index]?.id
    if (fileId) {
      await cache.updateOcrText(fileId, text)
    }
  }

  // Управление зумом и поворотом (без изменений)
  const zoomIn = () => { scale.value = Math.min(scale.value + 25, 500) }
  const zoomOut = () => { scale.value = Math.max(scale.value - 25, 25) }
  const fitToWidth = () => { scale.value = 100 }
  const rotate = () => { rotation.value = (rotation.value + 90) % 360 }

  return {
    files,
    selectedIndex,
    scale,
    rotation,
    addFiles,
    removeFile,
    selectFile,
    updateOcrText,
    zoomIn,
    zoomOut,
    fitToWidth,
    rotate,
    ocrData,
    showFrames,
    highlightedBlock,
    ocrBoxes,
    ocrFrames,
    updateOcrData,
    toggleFrames,
    highlightBlock,
  }
})