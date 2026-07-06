import { motion } from 'framer-motion'
import { Calendar, Tag, Pencil, Trash2, MoreHorizontal } from 'lucide-react'
import { format, isPast, isToday, differenceInDays } from 'date-fns'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { CategoryBadge } from './CategoryBadge'
import type { Todo, Category } from '@/types/todo'
import { cn } from '@/lib/utils'

interface TodoItemProps {
  todo: Todo
  category?: Category
  onToggle: (id: string) => void
  onEdit: (todo: Todo) => void
  onDelete: (id: string) => void
}

function getDueDateInfo(dueDate: string) {
  const date = new Date(dueDate)
  const now = new Date()

  if (isPast(date) && !isToday(date)) {
    const daysOver = differenceInDays(now, date)
    return { label: `${daysOver}d overdue`, variant: 'destructive' as const, urgent: true }
  }
  if (isToday(date)) {
    return { label: 'Due today', variant: 'default' as const, urgent: true }
  }
  const daysLeft = differenceInDays(date, now)
  if (daysLeft <= 3) {
    return { label: `${daysLeft}d left`, variant: 'default' as const, urgent: false }
  }
  return { label: format(date, 'MMM d'), variant: 'outline' as const, urgent: false }
}

export function TodoItem({ todo, category, onToggle, onEdit, onDelete }: TodoItemProps) {
  const dueDateInfo = todo.dueDate ? getDueDateInfo(todo.dueDate) : null

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'glass-panel group flex items-start gap-3 rounded-lg border border-white/5 p-4 transition-all hover:border-white/10',
        todo.completed && 'opacity-60'
      )}
    >
      <Checkbox
        checked={todo.completed}
        onCheckedChange={() => onToggle(todo.id)}
        className="mt-0.5"
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span
            className={cn(
              'font-medium text-text-primary transition-all duration-300',
              todo.completed && 'line-through text-text-muted'
            )}
          >
            {todo.title}
          </span>
          {category && <CategoryBadge name={category.name} color={category.color} />}
        </div>

        {todo.description && (
          <p className={cn(
            'text-sm text-text-secondary mb-2 line-clamp-2',
            todo.completed && 'text-text-muted'
          )}>
            {todo.description}
          </p>
        )}

        <div className="flex items-center gap-2 flex-wrap">
          {dueDateInfo && (
            <Badge
              variant={dueDateInfo.variant}
              className={cn(
                'text-xs gap-1',
                dueDateInfo.urgent && 'animate-pulse'
              )}
            >
              <Calendar className="h-3 w-3" />
              {dueDateInfo.label}
            </Badge>
          )}
          {todo.tags.map(tag => (
            <Badge key={tag} variant="secondary" className="text-xs gap-1">
              <Tag className="h-3 w-3" />
              {tag}
            </Badge>
          ))}
        </div>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => onEdit(todo)}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => onDelete(todo.id)}
            className="text-destructive focus:text-destructive"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </motion.div>
  )
}
