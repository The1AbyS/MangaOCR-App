import { useRoute } from 'vue-router'
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useFileCache } from '../composables/useFileCache'

export const useViewerStore = defineStore('viewer', () => {
  const route = useRoute()
  const projectId = route.params.projectId

  const cache = useFileCache(projectId)

  const ocrData = ref(null)  // { boxes, frames } для текущего файла
  const showFrames = ref(false)  // toggle для frames
  const highlightedBlock = ref(-1)  // индекс подсвеченного блока
  const isProcessingOcr = ref(false)  // отслеживание обработки OCR

  const selectedIndex = ref(-1)
  const scale = ref(100)
  const rotation = ref(0)

  // Прокидываем файлы из кэша
  const files = computed(() => {
    if (!cache || !cache.files) {
      console.warn('[useProjectViewer] cache или cache.files undefined!')
      return []
    }
    return cache.files.value ?? []
  })

  // Добавление файлов в кэш
  const addFiles = async (newFiles) => {
    await cache.addFiles(newFiles)
    if (selectedIndex.value === -1 && files.value.length > 0) {
      selectFile(0)
      console.log("Автовыбор первого файла")
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
    console.log ("Принят индекс:", index)
    selectedIndex.value = index
    ocrData.value = files.value[index]?.ocrData || null
    highlightedBlock.value = -1
    console.log("Выбран файл:", files.value[index]?.name)
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
    updateOcrData,
    toggleFrames,
    highlightBlock,
    isProcessingOcr,
  }
})