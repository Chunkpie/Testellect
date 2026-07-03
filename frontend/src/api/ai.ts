import api from './client'

export interface GenerateRequest {
  concept_ids: number[]
  bloom_level?: string
  difficulty?: string
  question_type?: string
  total_count?: number
  batch_size?: number
  language?: string
}

export interface JobStatus {
  id: string
  type: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  progress: number
  total: number
  error: string | null
  is_running: boolean
}

export async function startGeneration(params: GenerateRequest): Promise<{ job_id: string; status: string }> {
  const { data } = await api.post('/ai/generate-questions', params)
  return data
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const { data } = await api.get(`/ai/generate-questions/${jobId}`)
  return data
}
