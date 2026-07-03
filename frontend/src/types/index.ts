export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'teacher' | 'principal' | 'deo'
  school_id?: string
  school_name?: string
  preferred_language?: string
  is_active: boolean
  created_at: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: User
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface Book {
  id: string
  title: string
  subject_id: string
  subject_name?: string
  grade: string
  processing_status: 'pending' | 'uploading' | 'processing_document' | 'extracting_concepts' | 'mapping_competencies' | 'ready' | 'failed_upload' | 'failed_extraction'
  current_stage?: string
  file_path?: string
  file_type?: string
  file_size?: number
  error_message?: string
  created_at: string
  updated_at: string
}

export interface Question {
  id: string
  question_text_en: string
  question_text_hi?: string
  question_text_gu?: string
  question_type: 'mcq' | 'short_answer' | 'long_answer' | 'true_false' | 'fill_in_the_blank'
  options?: QuestionOption[]
  correct_answer?: string
  marks: number
  difficulty: 'easy' | 'medium' | 'hard'
  bloom_level: 'remember' | 'understand' | 'apply' | 'analyze' | 'evaluate' | 'create'
  concept_id?: string
  competency_id?: string
  approval_status: 'pending_review' | 'approved' | 'rejected'
  generated_by: 'ai' | 'manual'
  subject_id?: string
  chapter_id?: string
  created_by?: string
  created_at: string
  updated_at?: string
}

export interface QuestionOption {
  id: string
  option_text_en: string
  option_text_hi?: string
  option_text_gu?: string
  is_correct: boolean
  sequence: number
}

export interface Blueprint {
  id: string
  title: string
  grade: string
  subject_id: string
  chapter_ids: string[]
  total_questions: number
  total_marks: number
  difficulty_distribution: Record<string, number>
  bloom_distribution: Record<string, number>
  competency_distribution: Record<string, number>
  created_by: string
  created_at: string
  updated_at: string
}

export interface Paper {
  id: string
  blueprint_id: string
  title: string
  variants: PaperVariant[]
  status: 'generating' | 'ready' | 'failed'
  created_by: string
  created_at: string
}

export interface PaperVariant {
  id: string
  label: string
  file_path?: string
  question_count: number
  total_marks: number
}

export interface OMRResult {
  id: string
  student_id: string
  student_name?: string
  paper_id: string
  sheet_path?: string
  scanned_path?: string
  total_marks: number
  obtained_marks: number
  percentage: number
  needs_manual_review: boolean
  confidence_score?: number
  answers: OMRAnswer[]
  status: 'pending' | 'scored' | 'manual_review' | 'corrected'
  created_at: string
}

export interface OMRAnswer {
  question_id: string
  selected_option?: string
  is_correct: boolean
  confidence?: number
}

export interface DashboardStats {
  total_books?: number
  total_questions?: number
  total_papers?: number
  total_assessments?: number
  total_students?: number
  total_schools?: number
  pending_review_count?: number
  recent_activities?: ActivityItem[]
}

export interface ActivityItem {
  id: string
  action: string
  description: string
  user_name: string
  created_at: string
}

export interface JobStatus {
  job_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  result?: any
  error?: string
}
