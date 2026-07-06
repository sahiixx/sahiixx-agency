import { Search, X } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import type { FilterStatus } from '@/types/todo'

interface TodoFiltersProps {
  filter: FilterStatus
  searchQuery: string
  counts: { all: number; active: number; completed: number }
  onFilterChange: (filter: FilterStatus) => void
  onSearchChange: (query: string) => void
}

export function TodoFilters({
  filter,
  searchQuery,
  counts,
  onFilterChange,
  onSearchChange,
}: TodoFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
      <Tabs value={filter} onValueChange={v => onFilterChange(v as FilterStatus)}>
        <TabsList>
          <TabsTrigger value="all">
            All ({counts.all})
          </TabsTrigger>
          <TabsTrigger value="active">
            Active ({counts.active})
          </TabsTrigger>
          <TabsTrigger value="completed">
            Completed ({counts.completed})
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="relative flex-1 w-full sm:max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
        <Input
          placeholder="Search todos..."
          value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          className="pl-9 pr-8"
        />
        {searchQuery && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
            onClick={() => onSearchChange('')}
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    </div>
  )
}
