export interface Todo {
  id: string
  title: string
  description?: string
  completed: boolean
  categoryId?: string
  tags: string[]
  dueDate?: string
  createdAt: string
  updatedAt: string
}

export interface Category {
  id: string
  name: string
  color: string
}

export type FilterStatus = 'all' | 'active' | 'completed'
