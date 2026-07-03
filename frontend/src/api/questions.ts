import api from './client'
import type { Question, PaginatedResponse } from '@/types'

export async function getQuestions(params?: {
  subject_id?: string
  concept_id?: string
  competency_id?: string
  bloom_level?: string
  difficulty?: string
  approval_status?: string
  question_type?: string
  book_id?: string
  limit?: number
  offset?: number
}): Promise<PaginatedResponse<Question>> {
  const { data } = await api.get('/questions', { params })
  return data
}

export async function getQuestion(id: string): Promise<Question> {
  const { data } = await api.get(`/questions/${id}`)
  return data
}

export async function createQuestion(
  question: Partial<Question>
): Promise<Question> {
  const { data } = await api.post('/questions', question)
  return data
}

export async function updateQuestion(
  id: string,
  question: Partial<Question>
): Promise<Question> {
  const { data } = await api.patch(`/questions/${id}`, question)
  return data
}

export async function approveQuestion(id: string): Promise<Question> {
  const { data } = await api.post(`/questions/${id}/approve`)
  return data
}

export async function rejectQuestion(id: string): Promise<Question> {
  const { data } = await api.post(`/questions/${id}/reject`)
  return data
}

export async function deleteQuestion(id: string): Promise<void> {
  await api.delete(`/questions/${id}`)
}
