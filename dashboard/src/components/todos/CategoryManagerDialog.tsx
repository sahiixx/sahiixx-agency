import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { Category } from '@/types/todo'

interface CategoryManagerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  categories: Category[]
  onAdd: (data: Omit<Category, 'id'>) => void
  onUpdate: (id: string, data: Partial<Omit<Category, 'id'>>) => void
  onDelete: (id: string) => void
}

const PRESET_COLORS = [
  '#00d4ff', '#8b5cf6', '#e879f9', '#22c55e',
  '#f59e0b', '#ef4444', '#06b6d4', '#ec4899',
]

export function CategoryManagerDialog({
  open,
  onOpenChange,
  categories,
  onAdd,
  onUpdate,
  onDelete,
}: CategoryManagerDialogProps) {
  const [name, setName] = useState('')
  const [color, setColor] = useState(PRESET_COLORS[0])
  const [editingId, setEditingId] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      setName('')
      setColor(PRESET_COLORS[0])
      setEditingId(null)
    }
  }, [open])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    if (editingId) {
      onUpdate(editingId, { name: name.trim(), color })
    } else {
      onAdd({ name: name.trim(), color })
    }
    setName('')
    setColor(PRESET_COLORS[0])
    setEditingId(null)
  }

  const handleEdit = (category: Category) => {
    setEditingId(category.id)
    setName(category.name)
    setColor(category.color)
  }

  const handleCancel = () => {
    setEditingId(null)
    setName('')
    setColor(PRESET_COLORS[0])
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle className="font-display">Manage Categories</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-text-primary">Name</label>
            <div className="flex gap-2">
              <Input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Category name"
                className="flex-1"
              />
              {editingId && (
                <Button type="button" variant="ghost" size="icon" onClick={handleCancel}>
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-text-primary">Color</label>
            <div className="flex gap-2 flex-wrap">
              {PRESET_COLORS.map(c => (
                <button
                  key={c}
                  type="button"
                  className={`h-8 w-8 rounded-full transition-all ${
                    color === c ? 'ring-2 ring-offset-2 ring-offset-background' : ''
                  }`}
                  style={{ backgroundColor: c, '--tw-ring-color': c } as React.CSSProperties}
                  onClick={() => setColor(c)}
                />
              ))}
            </div>
          </div>

          <Button type="submit" className="w-full gap-2">
            <Plus className="h-4 w-4" />
            {editingId ? 'Update Category' : 'Add Category'}
          </Button>
        </form>

        {categories.length > 0 && (
          <div className="space-y-2 mt-4">
            <label className="text-sm font-medium text-text-primary">Existing Categories</label>
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {categories.map(cat => (
                <div
                  key={cat.id}
                  className="flex items-center justify-between rounded-lg border border-white/5 p-3"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: cat.color }}
                    />
                    <span className="text-sm text-text-primary">{cat.name}</span>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => handleEdit(cat)}
                    >
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:text-destructive"
                      onClick={() => onDelete(cat.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
