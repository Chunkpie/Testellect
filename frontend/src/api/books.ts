import api from './client'
import type { Book, PaginatedResponse } from '@/types'

export async function getBooks(params?: {
  grade?: string
  subject_id?: string
  processing_status?: string
}): Promise<PaginatedResponse<Book>> {
  const { data } = await api.get('/chapters', { params })
  return data
}

export async function getBook(id: string): Promise<Book> {
  const { data } = await api.get(`/chapters/${id}`)
  return data
}

export async function getBookStatus(id: string): Promise<{
  id: number
  processing_status: string
  processing_error?: string
}> {
  const { data } = await api.get(`/chapters/${id}/status`)
  return data
}

export async function uploadBook(
  formData: FormData,
  onProgress?: (progress: number) => void
): Promise<any> {
  const { data } = await api.post('/chapters/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total))
      }
    },
  })
  return data
}

export async function extractBook(id: string): Promise<any> {
  const { data } = await api.post(`/chapters/${id}/extract`)
  return data
}

export async function analyzeBook(id: string): Promise<any> {
  const { data } = await api.post(`/chapters/${id}/analyze`)
  return data
}

export async function generateQuestions(
  id: string,
  params?: { concept_id?: number; count?: number; bloom_level?: string; difficulty?: string; question_type?: string }
): Promise<any> {
  const { data } = await api.post(`/chapters/${id}/generate-questions`, null, { params })
  return data
}

export async function deleteBook(id: string): Promise<void> {
  await api.delete(`/chapters/${id}`)
}
