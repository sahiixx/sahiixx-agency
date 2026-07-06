import { AnimatePresence } from 'framer-motion'
import { TodoItem } from './TodoItem'
import { EmptyState } from './EmptyState'
import type { Todo, Category, FilterStatus } from '@/types/todo'

interface TodoListProps {
  todos: Todo[]
  categories: Category[]
  filter: FilterStatus
  onToggle: (id: string) => void
  onEdit: (todo: Todo) => void
  onDelete: (id: string) => void
  onAdd: () => void
}

export function TodoList({
  todos,
  categories,
  filter,
  onToggle,
  onEdit,
  onDelete,
  onAdd,
}: TodoListProps) {
  if (todos.length === 0) {
    return <EmptyState filter={filter} onAdd={onAdd} />
  }

  return (
    <div className="space-y-2">
      <AnimatePresence mode="popLayout">
        {todos.map(todo => (
          <TodoItem
            key={todo.id}
            todo={todo}
            category={categories.find(c => c.id === todo.categoryId)}
            onToggle={onToggle}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}
