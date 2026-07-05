export type FieldType = 'text' | 'textarea' | 'number' | 'boolean' | 'select'

export interface PatternField {
  name: string
  label: string
  type: FieldType
  default: string | number | boolean
  required?: boolean
  min?: number
  max?: number
  options?: string[]
}

export type PatternCategory = 'Core' | 'Extended' | 'Advanced'

export interface Pattern {
  id: number
  name: string
  description: string
  category: PatternCategory
  fields: PatternField[]
}

export type MessageRole = 'user' | 'assistant' | 'error'

export interface ChatMessage {
  id: string
  role: MessageRole
  /** Human-readable summary shown in the bubble */
  content: string
  patternId?: number
  patternName?: string
  /** Full structured result from the API */
  result?: Record<string, unknown>
  timestamp: Date
  isLoading?: boolean
}
