import { ref, computed } from 'vue'
import { get, set, del, entries, clear } from 'idb-keyval'

export function useFileCache() {
  const files = ref([])           // массив объектов { id, name, size, preview, ocrText }
  
  const isLoading = ref(false)

  // Загрузка всех файлов из IndexedDB при старте
  const loadFromCache = async () => {
    isLoading.value = true
    try {
      const allEntries = await entries()
      files.value = allEntries
        .filter(([key]) => key.startsWith('mangaocr_file:'))
        .map(([key, value]) => ({
          id: key.replace('mangaocr_file:', ''),
          ...value
        }))
    } catch (err) {
      console.error('Ошибка загрузки кэша:', err)
    } finally {
      isLoading.value = false
    }
  }

  // Сохранение одного файла в IndexedDB
  const saveFile = async (fileObj) => {
    const key = `mangaocr_file:${fileObj.id}`
    await set(key, {
      name: fileObj.name,
      size: fileObj.size,
      preview: fileObj.preview,        // URL.createObjectURL остаётся валидным только в сессии
      ocrText: fileObj.ocrText || ''
    })
  }

  // Добавление новых файлов (с сохранением в кэш)
  const addFiles = async (newFiles) => {
    for (const file of newFiles) {
      if (!file.type.startsWith('image/')) continue
    
      // Полифилл для randomUUID
        function generateUUID() {
        if (crypto.randomUUID) {
            return crypto.randomUUID()
        }
        // fallback: простой UUID v4-like
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
            const r = Math.random() * 16 | 0
            const v = c === 'x' ? r : (r & 0x3 | 0x8)
            return v.toString(16)
        })
        }
        const id = generateUUID()
      //const id = crypto.randomUUID() || Date.now() + Math.random()
      const preview = URL.createObjectURL(file)

      const fileObj = {
        id,
        name: file.name,
        size: (file.size / 1024 / 1024).toFixed(2) + ' MB',
        preview,
        ocrText: '' // пока пусто, потом заполнится после OCR
      }

      files.value.push(fileObj)
      await saveFile(fileObj)
    }
  }

  // Обновление OCR-текста для конкретного файла
  const updateOcrText = async (fileId, text) => {
    const file = files.value.find(f => f.id === fileId)
    if (!file) return

    file.ocrText = text
    await saveFile(file)
  }

  // Удаление файла
  const removeFile = async (fileId) => {
    const index = files.value.findIndex(f => f.id === fileId)
    if (index === -1) return

    const removed = files.value.splice(index, 1)[0]
    URL.revokeObjectURL(removed.preview)

    await del(`mangaocr_file:${fileId}`)
  }

  // Очистить весь кэш (для отладки)
  const clearCache = async () => {
    await clear()
    files.value = []
  }

  // Автозагрузка при монтировании
  loadFromCache()

  return {
    files,
    isLoading,
    addFiles,
    removeFile,
    updateOcrText,
    clearCache
  }
}