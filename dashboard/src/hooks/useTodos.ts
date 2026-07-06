import { useState, useEffect, useCallback } from 'react'
import type { Todo, Category, FilterStatus } from '@/types/todo'
import { loadTodos, saveTodos, loadCategories, saveCategories } from '@/lib/storage'

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function useTodos() {
  const [todos, setTodos] = useState<Todo[]>(() => loadTodos())
  const [categories, setCategories] = useState<Category[]>(() => loadCategories())
  const [filter, setFilter] = useState<FilterStatus>('all')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    saveTodos(todos)
  }, [todos])

  useEffect(() => {
    saveCategories(categories)
  }, [categories])

  const addTodo = useCallback((data: Omit<Todo, 'id' | 'completed' | 'createdAt' | 'updatedAt'>) => {
    const now = new Date().toISOString()
    const todo: Todo = {
      ...data,
      id: generateId(),
      completed: false,
      createdAt: now,
      updatedAt: now,
    }
    setTodos(prev => [todo, ...prev])
    return todo
  }, [])

  const updateTodo = useCallback((id: string, data: Partial<Omit<Todo, 'id' | 'createdAt'>>) => {
    setTodos(prev =>
      prev.map(t =>
        t.id === id ? { ...t, ...data, updatedAt: new Date().toISOString() } : t
      )
    )
  }, [])

  const deleteTodo = useCallback((id: string) => {
    setTodos(prev => prev.filter(t => t.id !== id))
  }, [])

  const toggleTodo = useCallback((id: string) => {
    setTodos(prev =>
      prev.map(t =>
        t.id === id ? { ...t, completed: !t.completed, updatedAt: new Date().toISOString() } : t
      )
    )
  }, [])

  const addCategory = useCallback((data: Omit<Category, 'id'>) => {
    const category: Category = { ...data, id: generateId() }
    setCategories(prev => [...prev, category])
    return category
  }, [])

  const updateCategory = useCallback((id: string, data: Partial<Omit<Category, 'id'>>) => {
    setCategories(prev =>
      prev.map(c => (c.id === id ? { ...c, ...data } : c))
    )
  }, [])

  const deleteCategory = useCallback((id: string) => {
    setCategories(prev => prev.filter(c => c.id !== id))
    setTodos(prev =>
      prev.map(t => (t.categoryId === id ? { ...t, categoryId: undefined } : t))
    )
  }, [])

  const filteredTodos = todos.filter(todo => {
    if (filter === 'active' && todo.completed) return false
    if (filter === 'completed' && !todo.completed) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      return (
        todo.title.toLowerCase().includes(q) ||
        todo.description?.toLowerCase().includes(q) ||
        todo.tags.some(t => t.toLowerCase().includes(q))
      )
    }
    return true
  })

  return {
    todos: filteredTodos,
    allTodos: todos,
    categories,
    filter,
    searchQuery,
    setFilter,
    setSearchQuery,
    addTodo,
    updateTodo,
    deleteTodo,
    toggleTodo,
    addCategory,
    updateCategory,
    deleteCategory,
  }
}
