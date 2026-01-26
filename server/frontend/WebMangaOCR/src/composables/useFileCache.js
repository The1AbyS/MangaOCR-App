import { ref } from 'vue'
import { set, del, entries } from 'idb-keyval'

export function useFileCache(projectId = null) {
  const files = ref([])
  const isLoading = ref(false)

  const PREFIX = projectId 
    ? `mangaocr_proj:${projectId}:file:` 
    : 'mangaocr_file:'

  // ── Загрузка всех файлов проекта из IndexedDB ───────────────────────────────
  const loadFromCache = async () => {
    isLoading.value = true
    files.value = []
    try {
      const allEntries = await entries()
      const loadedFiles = []

      for (const [key, value] of allEntries) {
        if (!key.startsWith(PREFIX)) continue

        const id = key.replace(PREFIX, '')

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
          ocrData: value.ocrData || null,
        })
      }

      files.value = loadedFiles.filter(f => f && f.id)
    } catch (err) {
    } finally {
      isLoading.value = false
    }
  }

  // ── Сохранение одного файла ─────────────────────────────────────────────────
  const saveFile = async (fileObj) => {
    const key = `${PREFIX}${fileObj.id}`

    const cleanOcrData = fileObj.ocrData 
      ? JSON.parse(JSON.stringify(fileObj.ocrData)) 
      : null

    const cleanObj = {
      name: fileObj.name,
      size: fileObj.size,
      fileData: fileObj.fileData,
      mimeType: fileObj.mimeType,
      ocrText: fileObj.ocrText || null,
      ocrData: cleanOcrData
    }

    await set(key, cleanObj)
  }

  // ── Обработка очереди OCR  ─────────────────────
  const processOcrQueue = async (onOcrComplete = null) => {
    const pendingFiles = files.value.filter(f => f.file && !f.ocrData)

    for (const file of pendingFiles) {
      if (!file.file) continue

      const formData = new FormData()
      formData.append('file', file.file)

      try {
        const res = await fetch('http://192.168.0.31:8000/v1/ocr', {
          method: 'POST',
          body: formData
        })

        if (!res.ok) {
          throw new Error(`OCR сервер вернул ${res.status}`)
        }

        const data = await res.json()
        const cleanData = JSON.parse(JSON.stringify(data))

        // Обновляем объект в памяти
        file.ocrData = cleanData
        file.ocrText = cleanData.boxes?.map(b => b.text).join('\n') || ''

        // Удаляем временные поля
        delete file.file
        delete file.preview 

        // Сохраняем в IndexedDB
        await saveFile(file)

        if (typeof onOcrComplete === 'function') {
          onOcrComplete(file)
        }

      } catch (err) {
        console.error(`Ошибка OCR для файла ${file.name}:`, err)
      }
    }
  }

  // ── Добавление новых файлов ─────────────────────────────────────────────────
  const addFiles = async (newFiles) => {
    for (const file of newFiles) {
      if (!file.type.startsWith('image/')) continue

      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
      const arrayBuffer = await file.arrayBuffer()
      const preview = URL.createObjectURL(file)

      const fileObj = {
        id,
        name: file.name,
        size: (file.size / 1024 / 1024).toFixed(2) + ' MB',
        fileData: arrayBuffer,
        mimeType: file.type,
        preview,
        file,           // временно храним оригинальный File
        ocrText: '',
        ocrData: null
      }

      files.value.push(fileObj)
      await saveFile(fileObj)  // сохраняем сразу
    }

    // Запускаем обработку очереди
    await processOcrQueue((processedFile) => {
      console.log(`OCR завершён для ${processedFile.name}`)
    })
    loadFromCache()
  }

  const updateOcrText = async (fileId, text) => {
    const file = files.value.find(f => f.id === fileId)
    if (!file) return
    file.ocrText = text
    await saveFile(file)
  }

  const removeFile = async (fileId) => {
    await del(`${PREFIX}${fileId}`)
    const idx = files.value.findIndex(f => f.id === fileId)
    if (idx !== -1) {
      if (files.value[idx].preview) {
        URL.revokeObjectURL(files.value[idx].preview)
      }
      files.value.splice(idx, 1)
    }
  }

  const clearCache = async () => {
    const all = await entries()
    for (const [key] of all) {
      if (key.startsWith(PREFIX)) {
        await del(key)
      }
    }
    files.value = []
  }

  // Автозагрузка только если projectId передан
  if (projectId) {
    console.log('[useFileCache] projectId есть → запускаем loadFromCache')
    loadFromCache()
  } else {
    console.log('[useFileCache] projectId falsy → автозагрузка ПРОПУЩЕНА')
  }

  return {
    files,
    isLoading,
    addFiles,
    removeFile,
    updateOcrText,
    clearCache,
    loadFromCache,
    processOcrQueue
  }
}