<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import MenuBar from '../components/MenuBar.vue'


const STORAGE_KEY = 'my-manga-projects' // уникальный ключ, чтобы не конфликтовать с другими приложениями

const projects = ref([
])

const showCreateModal = ref(false)
const newProjectName = ref('')
const selectedModel = ref('')

const availableModels = [
  { value: 'MangaOCR', label: 'MangaOCR — быстро и дёшево' },
  { value: 'Padle',    label: 'Padle — мощно, но долго' },
]

const hasProjects = computed(() => projects.value.length > 0)

// ── Загрузка из localStorage при монтировании ───────────────────────────────
onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      projects.value = JSON.parse(saved)
    } catch (e) {
      console.error('Ошибка парсинга проектов из localStorage:', e)
    }
  }
})

// ── Автосохранение при изменении массива проектов ───────────────────────────
watch(
  projects,
  (newProjects) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newProjects))
  },
  { deep: true }
)

const createProject = () => {
  if (!newProjectName.value.trim() || !selectedModel.value) {
    alert('Введите название и выберите модель')
    return
  }

  const newProj = {
    id: Date.now(),
    title: newProjectName.value.trim(),
    model: selectedModel.value,
    createdAt: new Date().toISOString().split('T')[0],
  }

  projects.value.push(newProj)
  newProjectName.value = ''
  selectedModel.value = ''
  showCreateModal.value = false
}

const cancelCreate = () => {
  newProjectName.value = ''
  selectedModel.value = ''
  showCreateModal.value = false
}

// ── Модальное окно удаления ────────────────────────────────────────────────
const showDeleteConfirm = ref(false)
const projectToDelete = ref(null)

// ── Удаление проекта ───────────────────────────────────────────
const requestDelete = (project) => {
  projectToDelete.value = project
  showDeleteConfirm.value = true
}

const confirmDelete = () => {
  if (projectToDelete.value) {
    projects.value = projects.value.filter(p => p.id !== projectToDelete.value.id)
  }
  showDeleteConfirm.value = false
  projectToDelete.value = null
}

const cancelDelete = () => {
  showDeleteConfirm.value = false
  projectToDelete.value = null
}

const router = useRouter()

const openProject = (projectId) => {
  router.push(`/home/${projectId}`)
}
</script>

<template>
  <div class="min-h-screen w-full flex flex-col bg-gray-950 text-gray-100">
    <!-- Верхняя панель (MenuBar) -->
    <MenuBar />

    <!-- Основной контент -->
    <main class="flex-1 flex flex-col px-4 sm:px-6 lg:px-8 py-6 md:py-8">
      <!-- Заголовок + кнопка -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 md:mb-8">
        <h1 class="text-2xl sm:text-3xl font-bold">Мои проекты</h1>

        <button
          v-if="hasProjects"
          @click="showCreateModal = true"
          class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 
                 rounded-lg font-medium transition-colors flex items-center justify-center gap-2
                 sm:self-start"
        >
          <span class="text-xl leading-none">+</span>
          Новый проект
        </button>
      </div>

      <!-- Нет проектов → большой плюс по центру -->
      <div
        v-if="!hasProjects"
        class="flex-1 flex items-center justify-center min-h-[50vh]"
      >
        <button
          @click="showCreateModal = true"
          class="group w-72 sm:w-80 lg:w-96 aspect-square rounded-2xl 
                 bg-gray-800/40 border-2 border-dashed border-gray-600 
                 hover:border-indigo-500/70 hover:bg-gray-800/60 
                 transition-all duration-300
                 flex flex-col items-center justify-center gap-6
                 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-950"
        >
          <div class="text-8xl sm:text-9xl text-gray-500 group-hover:text-indigo-400 transition-colors">
            +
          </div>
          <div class="text-xl sm:text-2xl font-medium text-gray-400 group-hover:text-gray-200">
            Создать первый проект
          </div>
        </button>
      </div>

      <!-- Есть проекты → адаптивная сетка -->
      <div v-else class="flex-1">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-5 sm:gap-6">
          <!-- Карточки проектов -->
          <div
            v-for="project in projects"
            :key="project.id"
            class="group bg-gray-800 rounded-xl overflow-hidden border border-gray-700 
                   hover:border-indigo-600/70 hover:shadow-xl hover:shadow-indigo-950/30 
                   transition-all duration-300 cursor-pointer flex flex-col"
            @click="openProject(project.id)"
          >
            <div class="h-2 sm:h-3 bg-gradient-to-r from-indigo-500 via-purple-600 to-indigo-600"></div>
                <div class="p-4 sm:p-5 flex-1 flex flex-col">
                    <div class="flex justify-between items-start mb-1.5">
                        <h3 class="text-base sm:text-lg font-semibold truncate flex-1 pr-2">
                        {{ project.title }}
                        </h3>
                        
                        <!-- Кнопка удаления -->
                        <button
                        @click.stop="requestDelete(project)"
                        class="text-gray-500 hover:text-red-400 focus:text-red-400 
                                transition-colors p-1 rounded-full hover:bg-gray-700/50"
                        title="Удалить проект"
                        >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                        </button>
                    </div>
              <p class="text-sm text-gray-400 mb-3 sm:mb-4">
                {{ project.model }}
              </p>
              <div class="text-xs text-gray-500 mt-auto">
                Создан: {{ project.createdAt }}
              </div>
            </div>
          </div>

          <!-- Плитка "Создать новый" -->
          <button
            @click="showCreateModal = true"
            class="group bg-gray-800/30 rounded-xl border-2 border-dashed border-gray-600 
                   hover:border-indigo-500/70 hover:bg-gray-800/50 
                   transition-all duration-300
                   flex flex-col items-center justify-center gap-4 sm:gap-5 min-h-[160px] sm:min-h-[180px]"
          >
            <div class="text-6xl sm:text-7xl text-gray-500 group-hover:text-indigo-400 transition-colors">
              +
            </div>
            <div class="text-base sm:text-lg font-medium text-gray-500 group-hover:text-gray-200">
              Новый проект
            </div>
          </button>
        </div>
      </div>
    </main>

    <!-- Модальное окно -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 sm:p-6"
      @click.self="cancelCreate"
    >
      <div
        class="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg sm:max-w-md lg:max-w-lg 
               shadow-2xl max-h-[90vh] overflow-y-auto"
        @click.stop
      >
        <div class="p-5 sm:p-6 md:p-7">
          <h2 class="text-xl sm:text-2xl font-bold mb-5 sm:mb-6">Создать новый проект</h2>

          <!-- Название -->
          <div class="mb-5 sm:mb-6">
            <label class="block text-sm font-medium text-gray-300 mb-2">
              Название проекта
            </label>
            <input
              v-model="newProjectName"
              type="text"
              placeholder="Например: Распознавание манги 2025"
              class="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg 
                     focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500
                     text-white placeholder-gray-500 text-base"
              autofocus
            />
          </div>

          <!-- Выбор модели -->
          <div class="mb-6 sm:mb-8">
            <label class="block text-sm font-medium text-gray-300 mb-2">
              Модель распознавания
            </label>
            <div class="space-y-2.5 sm:space-y-3">
              <label
                v-for="model in availableModels"
                :key="model.value"
                class="flex items-center gap-3 px-4 py-3.5 bg-gray-800 border border-gray-700 rounded-lg 
                       cursor-pointer hover:border-indigo-600/50 transition-colors text-sm sm:text-base"
                :class="{ 'border-indigo-500 bg-indigo-950/20': selectedModel === model.value }"
              >
                <input
                  type="radio"
                  v-model="selectedModel"
                  :value="model.value"
                  class="w-5 h-5 text-indigo-500 focus:ring-indigo-500 bg-gray-700 border-gray-600"
                />
                <div>
                  <div class="font-medium">{{ model.label.split(' — ')[0] }}</div>
                  <div class="text-xs sm:text-sm text-gray-400">{{ model.label.split(' — ')[1] }}</div>
                </div>
              </label>
            </div>
          </div>

          <!-- Кнопки -->
          <div class="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-end">
            <button
              @click="cancelCreate"
              class="px-6 py-2.5 text-gray-300 hover:text-white hover:bg-gray-800 rounded-lg transition-colors order-2 sm:order-1"
            >
              Отмена
            </button>
            <button
              @click="createProject"
              :disabled="!newProjectName.trim() || !selectedModel"
              class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 
                     disabled:cursor-not-allowed rounded-lg font-medium transition-colors order-1 sm:order-2"
            >
              Создать
            </button>
          </div>
        </div>
      </div>
    </div>
    <!-- Модальное окно ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ -->
    <div
      v-if="showDeleteConfirm"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      @click.self="cancelDelete"
    >
      <div
        class="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-sm sm:max-w-md shadow-2xl p-6"
        @click.stop
      >
        <h2 class="text-xl font-bold mb-4 text-red-400">Удалить проект?</h2>
        
        <p class="text-gray-300 mb-6">
          Вы уверены, что хотите удалить проект 
          <span class="font-semibold text-white">«{{ projectToDelete?.title }}»</span>?
          <br />
          Это действие нельзя отменить.
        </p>

        <div class="flex gap-4 justify-end">
          <button
            @click="cancelDelete"
            class="px-5 py-2.5 text-gray-300 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            Отмена
          </button>
          <button
            @click="confirmDelete"
            class="px-5 py-2.5 bg-red-600 hover:bg-red-700 active:bg-red-800 
                   text-white rounded-lg font-medium transition-colors"
          >
            Удалить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>