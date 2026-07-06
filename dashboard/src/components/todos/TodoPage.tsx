import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Plus, Settings2, Keyboard } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useTodos } from '@/hooks/useTodos'
import { TodoList } from './TodoList'
import { TodoFilters } from './TodoFilters'
import { TodoFormDialog } from './TodoFormDialog'
import { CategoryManagerDialog } from './CategoryManagerDialog'
import type { Todo, TodoFormData } from '@/types/todo'

export function TodoPage() {
  const {
    todos,
    allTodos,
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
  } = useTodos()

  const [formOpen, setFormOpen] = useState(false)
  const [categoryOpen, setCategoryOpen] = useState(false)
  const [editingTodo, setEditingTodo] = useState<Todo | null>(null)

  const counts = {
    all: allTodos.length,
    active: allTodos.filter(t => !t.completed).length,
    completed: allTodos.filter(t => t.completed).length,
  }

  const handleAdd = () => {
    setEditingTodo(null)
    setFormOpen(true)
  }

  const handleEdit = (todo: Todo) => {
    setEditingTodo(todo)
    setFormOpen(true)
  }

  const handleFormSubmit = (data: TodoFormData) => {
    if (editingTodo) {
      updateTodo(editingTodo.id, data)
      toast.success('Todo updated', { description: data.title })
    } else {
      addTodo(data)
      toast.success('Todo created', { description: data.title })
    }
  }

  const handleDelete = (id: string) => {
    const todo = allTodos.find(t => t.id === id)
    deleteTodo(id)
    toast.success('Todo deleted', { description: todo?.title })
  }

  const handleToggle = (id: string) => {
    toggleTodo(id)
    const todo = allTodos.find(t => t.id === id)
    if (todo) {
      toast(todo.completed ? 'Marked as active' : 'Marked as complete', {
        description: todo.title,
      })
    }
  }

  const handleAddCategory = (data: { name: string; color: string }) => {
    addCategory(data)
    toast.success('Category created', { description: data.name })
  }

  const handleUpdateCategory = (id: string, data: { name?: string; color?: string }) => {
    updateCategory(id, data)
    toast.success('Category updated')
  }

  const handleDeleteCategory = (id: string) => {
    const cat = categories.find(c => c.id === id)
    deleteCategory(id)
    toast.success('Category deleted', { description: cat?.name })
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

      // Ctrl/Cmd + N = New todo
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault()
        handleAdd()
      }
      // 1, 2, 3 = Switch filters
      if (e.key === '1') setFilter('all')
      if (e.key === '2') setFilter('active')
      if (e.key === '3') setFilter('completed')
      // / = Focus search
      if (e.key === '/') {
        e.preventDefault()
        document.querySelector<HTMLInputElement>('[placeholder="Search todos..."]')?.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [setFilter])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="min-h-[100dvh] px-4 py-8 md:px-8"
    >
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-display text-3xl font-bold text-text-primary mb-1">
              Todos
            </h1>
            <p className="text-text-secondary">
              {counts.active} active · {counts.completed} completed
            </p>
          </div>
          <div className="flex gap-2">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setCategoryOpen(true)}
                  >
                    <Settings2 className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Manage Categories</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="icon" className="hidden sm:inline-flex">
                    <Keyboard className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="text-xs space-y-1">
                    <p><kbd className="px-1 py-0.5 rounded bg-white/10">Ctrl+N</kbd> New todo</p>
                    <p><kbd className="px-1 py-0.5 rounded bg-white/10">/</kbd> Search</p>
                    <p><kbd className="px-1 py-0.5 rounded bg-white/10">1-3</kbd> Switch filter</p>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <Button onClick={handleAdd} className="gap-2">
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">Add Todo</span>
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-6">
          <TodoFilters
            filter={filter}
            searchQuery={searchQuery}
            counts={counts}
            onFilterChange={setFilter}
            onSearchChange={setSearchQuery}
          />
        </div>

        {/* Todo List */}
        <TodoList
          todos={todos}
          categories={categories}
          filter={filter}
          onToggle={handleToggle}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onAdd={handleAdd}
        />
      </div>

      {/* Dialogs */}
      <TodoFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        todo={editingTodo}
        categories={categories}
        onSubmit={handleFormSubmit}
      />
      <CategoryManagerDialog
        open={categoryOpen}
        onOpenChange={setCategoryOpen}
        categories={categories}
        onAdd={handleAddCategory}
        onUpdate={handleUpdateCategory}
        onDelete={handleDeleteCategory}
      />
    </motion.div>
  )
}
