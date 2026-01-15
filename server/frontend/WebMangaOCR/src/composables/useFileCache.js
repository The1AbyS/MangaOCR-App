<<<<<<< HEAD
import { ref } from 'vue'
import { get, set, del, entries, clear } from 'idb-keyval'
import { useViewerStore } from '../stores/viewer'

export function useFileCache() {
  const files = ref([])
  const store = useViewerStore()
  const isLoading = ref(false)

  // Загрузка из кэша + восстановление в store
=======
import { ref, computed } from 'vue'
import { get, set, del, entries, clear } from 'idb-keyval'

export function useFileCache() {
  const files = ref([])           // массив объектов { id, name, size, preview, ocrText }
  
  const isLoading = ref(false)

  // Загрузка всех файлов из IndexedDB при старте
>>>>>>> 9687aaefb0b21d2076411fc990dc30dd88558f8f
  const loadFromCache = async () => {
    isLoading.value = true
    try {
      const allEntries = await entries()
<<<<<<< HEAD
      const loadedFiles = []

      for (const [key, value] of allEntries) {
        if (!key.startsWith('mangaocr_file:')) continue

        const id = key.replace('mangaocr_file:', '')

        let preview = null
        if (value.fileData) {
          const blob = new Blob([value.fileData], { type: value.mimeType || 'image/jpeg' })
          preview = URL.createObjectURL(blob)
        }

        loadedFiles.push({
          id,
          name: value.name,
          size: value.size,
          fileData: value.fileData,
          mimeType: value.mimeType,
          preview,
          ocrText: value.ocrText || '',
          ocrData: value.ocrData || null  // весь JSON-ответ
        })
      }

      files.value = loadedFiles

      // Восстанавливаем в store выбранный файл
      if (loadedFiles.length > 0 && store.selectedIndex >= 0) {
        const selected = loadedFiles[store.selectedIndex]
        if (selected && selected.ocrData) {
          store.updateOcrData(selected.ocrData)
          console.log('Восстановлено из кэша ocrData:', selected.ocrData)
        }
      }
=======
      files.value = allEntries
        .filter(([key]) => key.startsWith('mangaocr_file:'))
        .map(([key, value]) => ({
          id: key.replace('mangaocr_file:', ''),
          ...value
        }))
>>>>>>> 9687aaefb0b21d2076411fc990dc30dd88558f8f
    } catch (err) {
      console.error('Ошибка загрузки кэша:', err)
    } finally {
      isLoading.value = false
    }
  }

<<<<<<< HEAD
  // Сохранение — чистая копия
  const saveFile = async (fileObj) => {
    const key = `mangaocr_file:${fileObj.id}`

    // Чистим ocrData от Proxy и любых несериализуемых штук
    const cleanOcrData = fileObj.ocrData ? JSON.parse(JSON.stringify(fileObj.ocrData)) : null

    const cleanObj = {
      name: fileObj.name,
      size: fileObj.size,
      fileData: fileObj.fileData,
      mimeType: fileObj.mimeType,
      ocrText: fileObj.ocrText || null,
      ocrData: cleanOcrData
    }

    console.log('Сохраняем в IndexedDB:', {
      key,
      hasOcrData: !!cleanOcrData,
      boxesCount: cleanOcrData?.boxes?.length || 0,
      framesCount: cleanOcrData?.frames?.length || 0
    })

    await set(key, cleanObj)
  }

  const processOcrQueue = async () => {
    const pendingFiles = files.value.filter(f => !f.ocrData && f.file)

    for (const file of pendingFiles) {
      if (!file.file) continue

      const formData = new FormData()
      formData.append('file', file.file)

      try {
        const res = await fetch('http://localhost:8000/v1/ocr', {
          method: 'POST',
          body: formData
        })

        if (!res.ok) throw new Error(`HTTP ${res.status}`)

        const data = await res.json()

        // Чистим от Proxy
        const cleanData = JSON.parse(JSON.stringify(data))

        file.ocrData = cleanData
        file.ocrText = cleanData.boxes?.map(b => b.text).join('\n') || ''

        delete file.file
        delete file.preview

        await saveFile(file)

        if (store.selectedIndex >= 0 && store.files[store.selectedIndex]?.id === file.id) {
          store.updateOcrData(file.ocrData)
        }
      } catch (err) {
        console.error(`Ошибка OCR для ${file.name}:`, err)
      }
    }
  }

  // Добавление файлов
  const addFiles = async (newFiles) => {
    for (const file of newFiles) {
      if (!file.type.startsWith('image/')) continue

      const id = file.name  
      const arrayBuffer = await file.arrayBuffer()
=======
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
>>>>>>> 9687aaefb0b21d2076411fc990dc30dd88558f8f
      const preview = URL.createObjectURL(file)

      const fileObj = {
        id,
        name: file.name,
        size: (file.size / 1024 / 1024).toFixed(2) + ' MB',
<<<<<<< HEAD
        fileData: arrayBuffer,
        mimeType: file.type,
        preview,
        file,
        ocrText: '',
        ocrData: null
=======
        preview,
        ocrText: '' // пока пусто, потом заполнится после OCR
>>>>>>> 9687aaefb0b21d2076411fc990dc30dd88558f8f
      }

      files.value.push(fileObj)
      await saveFile(fileObj)
    }
<<<<<<< HEAD

    await processOcrQueue()
=======
>>>>>>> 9687aaefb0b21d2076411fc990dc30dd88558f8f
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