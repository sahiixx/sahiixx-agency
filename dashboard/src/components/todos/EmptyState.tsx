import { motion } from 'framer-motion'
import { CheckCircle2, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  filter: string
  onAdd: () => void
}

export function EmptyState({ filter, onAdd }: EmptyStateProps) {
  const messages = {
    all: "You don't have any todos yet",
    active: 'No active todos',
    completed: 'No completed todos',
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <div className="mb-6 rounded-full bg-accent-cyan/10 p-4">
        <CheckCircle2 className="h-10 w-10 text-accent-cyan" />
      </div>
      <h3 className="font-display text-lg text-text-primary mb-2">
        {messages[filter as keyof typeof messages] || messages.all}
      </h3>
      <p className="text-sm text-text-muted mb-6 max-w-sm">
        {filter === 'all'
          ? 'Create your first todo to get started with task management.'
          : 'Try changing the filter to see other todos.'}
      </p>
      {filter === 'all' && (
        <Button onClick={onAdd} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Todo
        </Button>
      )}
    </motion.div>
  )
}
