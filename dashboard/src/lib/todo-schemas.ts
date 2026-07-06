import { z } from 'zod'

export const todoSchema = z.object({
  title: z.string().min(1, 'Title is required').max(200),
  description: z.string().max(1000).optional(),
  categoryId: z.string().optional(),
  tags: z.array(z.string()).optional(),
  dueDate: z.string().optional(),
})

export type TodoFormData = z.infer<typeof todoSchema>

export const categorySchema = z.object({
  name: z.string().min(1, 'Name is required').max(50),
  color: z.string().regex(/^#[0-9A-Fa-f]{6}$/, 'Must be a valid hex color'),
})

export type CategoryFormData = z.infer<typeof categorySchema>
