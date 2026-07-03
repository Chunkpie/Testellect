import api from './client'

export interface PaperQuestion {
  id: number
  paper_id: number
  question_id: number
  sequence: number
  marks: number
  question_text: string
  bloom_level: string
  difficulty: string
}

export interface Paper {
  id: number
  name: string
  grade: number
  subject_id: number
  blueprint_id?: number
  total_marks: number
  duration_minutes: number
  total_questions: number
  school_id: number
  created_by?: number
  created_at: string
  questions?: PaperQuestion[]
}

export async function getPapers(params?: {
  page?: number
  per_page?: number
  limit?: number
  offset?: number
}): Promise<{ items: Paper[]; total: number; limit: number; offset: number }> {
  const { data } = await api.get('/papers', { params })
  return data
}

export async function getPaper(id: number): Promise<Paper> {
  const { data } = await api.get(`/papers/${id}`)
  return data
}

export async function createPaper(data: {
  blueprint_id: number
  name: string
  variant_count?: number
}): Promise<Paper> {
  const { data: result } = await api.post('/papers/generate', data)
  return result
}

export async function deletePaper(id: number): Promise<void> {
  await api.delete(`/papers/${id}`)
}

export async function exportPaperPdf(id: number, lang?: string): Promise<Blob> {
  const { data } = await api.get(`/papers/${id}/export`, {
    params: { lang },
    responseType: 'blob',
  })
  return data
}

export async function downloadPaper(id: number): Promise<Blob> {
  const { data } = await api.get(`/papers/${id}/download`, {
    responseType: 'blob',
  })
  return data
}
