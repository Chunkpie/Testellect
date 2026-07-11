import api from './client'

export interface OMRAnswerSubmission {
  question_id: number
  answer: string
}

export interface EvaluatedAnswer {
  question_id: number
  sequence: number
  student_answer: string
  correct_answer: string
  is_correct: boolean
}

export interface OMRSummary {
  correct: number
  total: number
  percentage: number
}

export interface OMRSession {
  batch_id: string
  paper_id: number
  paper_name: string
  grade: number
  subject_id: number
  student_count: number
  created_at: string
  has_results: boolean
}

export interface OMRSessionDetail {
  batch_id: string
  paper_id: number
  paper_name: string
  grade: number
  subject_id: number
  total_questions: number
  student_count: number
  status: string
  created_at: string
  sheets: Array<{
    id: number
    student_id: number | null
    student_name?: string
    status: string
    created_at: string
  }>
}

export interface OMRGenerateResponse {
  batch_id: string
  paper_id: number
  paper_name: string
  student_count: number
  file_path: string
  sheets_created: Array<{ id: number; student_number: number }>
}

export interface OMRResultsResponse {
  batch_id: string
  paper_id: number
  paper_name?: string
  results: EvaluatedAnswer[]
  summary: OMRSummary
}

export interface ListOMRSessionsResponse {
  items: OMRSession[]
  total: number
}

export async function listSessions(): Promise<ListOMRSessionsResponse> {
  const { data } = await api.get('/omr')
  return data
}

export async function generateOMR(params: {
  paper_id: number
  class_id: number
  total_questions?: number
}): Promise<OMRGenerateResponse> {
  const { data } = await api.post('/omr/generate', params)
  return data
}

export async function getSession(batchId: string): Promise<OMRSessionDetail> {
  const { data } = await api.get(`/omr/${encodeURIComponent(batchId)}`)
  return data
}

export async function downloadOMR(batchId: string): Promise<Blob> {
  const { data } = await api.get(`/omr/${encodeURIComponent(batchId)}/download`, {
    responseType: 'blob',
  })
  return data
}

export async function submitResults(
  batchId: string,
  answers: OMRAnswerSubmission[]
): Promise<OMRResultsResponse> {
  const { data } = await api.post(
    `/omr/${encodeURIComponent(batchId)}/results`,
    answers
  )
  return data
}

export async function getResults(batchId: string): Promise<OMRResultsResponse> {
  const { data } = await api.get(`/omr/${encodeURIComponent(batchId)}/results`)
  return data
}

export async function deleteSession(batchId: string): Promise<void> {
  await api.delete(`/omr/${encodeURIComponent(batchId)}`)
}
