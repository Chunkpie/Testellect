import api from './client'

export async function getStudentAnalytics(id: string): Promise<any> {
  const { data } = await api.get(`/analytics/student/${id}`)
  return data
}

export async function getClassAnalytics(id: string): Promise<any> {
  const { data } = await api.get(`/analytics/class/${id}`)
  return data
}

export async function getSchoolAnalytics(id: string): Promise<any> {
  const { data } = await api.get(`/analytics/school/${id}`)
  return data
}

export async function getDistrictAnalytics(id: string): Promise<any> {
  const { data } = await api.get(`/analytics/district/${id}`)
  return data
}

export async function getDashboard(): Promise<any> {
  const { data } = await api.get('/dashboard')
  return data
}

export interface DashboardStats {
  total_students: number
  total_teachers: number
  total_assessments: number
  total_questions: number
  average_score: number
  completion_rate: number
}

export interface SubjectPerformance {
  subject_id: number
  subject_name: string
  average_score: number
  student_count: number
}

export interface BloomDistribution {
  level: string
  count: number
  percentage: number
}

export interface TrendData {
  date: string
  score: number
  assessment_count: number
}

export interface Report {
  id: number
  title: string
  report_type: string
  school_id: number
  generated_at: string
  parameters: string
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get('/reports/stats')
  return data
}

export async function getSubjectPerformance(): Promise<SubjectPerformance[]> {
  const { data } = await api.get('/reports/subject-performance')
  return data
}

export async function getBloomDistribution(): Promise<BloomDistribution[]> {
  const { data } = await api.get('/reports/bloom-distribution')
  return data
}

export async function getScoreTrends(days = 30): Promise<TrendData[]> {
  const { data } = await api.get('/reports/score-trends', { params: { days } })
  return data
}

export async function getReports(): Promise<{ items: Report[]; total: number }> {
  const { data } = await api.get('/reports')
  return data
}

export async function generateReport(reportType: string, schoolId?: number): Promise<Report> {
  const { data } = await api.post('/reports/generate', null, {
    params: { report_type: reportType, school_id: schoolId },
  })
  return data
}

export async function downloadReport(reportId: number): Promise<Blob> {
  const { data } = await api.get(`/reports/${reportId}/download`, {
    responseType: 'blob',
  })
  return data
}

export async function deleteReport(reportId: number): Promise<void> {
  await api.delete(`/reports/${reportId}`)
}
