const TODO_STORAGE_KEY = 'ai-nexus-todos'
const CATEGORY_STORAGE_KEY = 'ai-nexus-categories'

export function loadTodos() {
  try {
    const data = localStorage.getItem(TODO_STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

export function saveTodos(todos: unknown[]) {
  localStorage.setItem(TODO_STORAGE_KEY, JSON.stringify(todos))
}

export function loadCategories() {
  try {
    const data = localStorage.getItem(CATEGORY_STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

export function saveCategories(categories: unknown[]) {
  localStorage.setItem(CATEGORY_STORAGE_KEY, JSON.stringify(categories))
}
