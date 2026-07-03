import api from './client'
import { useAuthStore } from '@/stores/authStore'

export interface Blueprint {
  id: number
  name: string
  grade: number
  subject_id: number
  school_id: number
  total_marks: number
  total_questions: number
  duration_minutes: number
  bloom_distribution: Record<string, number>
  difficulty_distribution: Record<string, number>
  competency_distribution?: Record<string, number>
  created_by?: number
  created_at: string
  updated_at: string
}

export async function getBlueprints(params?: {
  page?: number
  per_page?: number
  limit?: number
  offset?: number
}): Promise<{ items: Blueprint[]; total: number; limit: number; offset: number }> {
  const { data } = await api.get('/blueprints', { params })
  return data
}

export async function getBlueprint(id: number): Promise<Blueprint> {
  const { data } = await api.get(`/blueprints/${id}`)
  return data
}

export async function createBlueprint(input: {
  name: string
  grade: number
  subject_id: number
  total_marks: number
  total_questions: number
  duration_minutes: number
  bloom_distribution: Record<string, number>
  difficulty_distribution: Record<string, number>
  competency_ids?: number[]
}): Promise<Blueprint> {
  const user = useAuthStore.getState().user
  const school_id = user?.school_id || 1
  const { data: result } = await api.post('/blueprints', {
    ...input,
    school_id,
    bloom_distribution: JSON.stringify(input.bloom_distribution),
    difficulty_distribution: JSON.stringify(input.difficulty_distribution),
  })
  return result
}

export async function updateBlueprint(
  id: number,
  input: Partial<{
    name: string
    grade: number
    subject_id: number
    total_marks: number
    total_questions: number
    duration_minutes: number
    bloom_distribution: Record<string, number>
    difficulty_distribution: Record<string, number>
    competency_ids?: number[]
  }>
): Promise<Blueprint> {
  const body: Record<string, unknown> = { ...input }
  if (input.bloom_distribution) {
    body.bloom_distribution = JSON.stringify(input.bloom_distribution)
  }
  if (input.difficulty_distribution) {
    body.difficulty_distribution = JSON.stringify(input.difficulty_distribution)
  }
  const { data: result } = await api.patch(`/blueprints/${id}`, body)
  return result
}

export async function deleteBlueprint(id: number): Promise<void> {
  await api.delete(`/blueprints/${id}`)
}

export async function generatePaperFromBlueprint(
  blueprintId: number,
  paperName?: string
): Promise<{ paper_id: number; name: string; total_questions: number; total_marks: number }> {
  const { data } = await api.post(`/blueprints/${blueprintId}/generate`, { name: paperName })
  return data
}

export async function checkCoverage(id: number): Promise<any> {
  const { data } = await api.post(`/blueprints/${id}/check-coverage`)
  return data
}
