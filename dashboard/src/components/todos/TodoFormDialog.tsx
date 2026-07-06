import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { format } from 'date-fns'
import { CalendarIcon, X, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import { todoSchema, type TodoFormData } from '@/lib/todo-schemas'
import type { Todo, Category } from '@/types/todo'

interface TodoFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  todo?: Todo | null
  categories: Category[]
  onSubmit: (data: TodoFormData) => void
}

export function TodoFormDialog({
  open,
  onOpenChange,
  todo,
  categories,
  onSubmit,
}: TodoFormDialogProps) {
  const [tags, setTags] = useState<string[]>(todo?.tags || [])
  const [tagInput, setTagInput] = useState('')
  const [dateOpen, setDateOpen] = useState(false)

  const form = useForm<TodoFormData>({
    resolver: zodResolver(todoSchema),
    defaultValues: {
      title: '',
      description: '',
      categoryId: undefined,
      tags: [],
      dueDate: undefined,
    },
  })

  useEffect(() => {
    if (open) {
      if (todo) {
        form.reset({
          title: todo.title,
          description: todo.description || '',
          categoryId: todo.categoryId,
          tags: todo.tags,
          dueDate: todo.dueDate,
        })
        setTags(todo.tags)
      } else {
        form.reset({ title: '', description: '', categoryId: undefined, tags: [], dueDate: undefined })
        setTags([])
      }
      setTagInput('')
    }
  }, [open, todo, form])

  const handleAddTag = () => {
    const tag = tagInput.trim()
    if (tag && !tags.includes(tag)) {
      const newTags = [...tags, tag]
      setTags(newTags)
      form.setValue('tags', newTags)
      setTagInput('')
    }
  }

  const handleRemoveTag = (tag: string) => {
    const newTags = tags.filter(t => t !== tag)
    setTags(newTags)
    form.setValue('tags', newTags)
  }

  const handleSubmit = form.handleSubmit((data) => {
    onSubmit({ ...data, tags })
    onOpenChange(false)
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="font-display">
            {todo ? 'Edit Todo' : 'Add Todo'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-text-primary">Title</label>
            <Input
              {...form.register('title')}
              placeholder="What needs to be done?"
            />
            {form.formState.errors.title && (
              <p className="text-xs text-destructive">
                {form.formState.errors.title.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-text-primary">Description</label>
            <Textarea
              {...form.register('description')}
              placeholder="Add details (optional)"
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">Category</label>
              <Select
                value={form.watch('categoryId') || 'none'}
                onValueChange={v =>
                  form.setValue('categoryId', v === 'none' ? undefined : v)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No category</SelectItem>
                  {categories.map(cat => (
                    <SelectItem key={cat.id} value={cat.id}>
                      <span className="flex items-center gap-2">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: cat.color }}
                        />
                        {cat.name}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">Due Date</label>
              <Popover open={dateOpen} onOpenChange={setDateOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left font-normal"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {form.watch('dueDate')
                      ? format(new Date(form.watch('dueDate')!), 'MMM d, yyyy')
                      : 'Pick a date'}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0">
                  <Calendar
                    mode="single"
                    selected={
                      form.watch('dueDate') ? new Date(form.watch('dueDate')!) : undefined
                    }
                    onSelect={date => {
                      form.setValue('dueDate', date ? date.toISOString() : undefined)
                      setDateOpen(false)
                    }}
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-text-primary">Tags</label>
            <div className="flex gap-2">
              <Input
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                placeholder="Add a tag"
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleAddTag()
                  }
                }}
              />
              <Button type="button" variant="outline" size="icon" onClick={handleAddTag}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {tags.map(tag => (
                  <Badge key={tag} variant="secondary" className="gap-1">
                    {tag}
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">{todo ? 'Save Changes' : 'Add Todo'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
