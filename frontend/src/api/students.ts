import api from './client'
import type { PaginatedResponse } from '@/types'

export interface Student {
  id: string
  full_name: string
  roll_number?: string
  class_id?: string
  class_name?: string
  gender?: string
  school_id?: string
  school_name?: string
  created_at: string
}

export interface CreateStudentPayload {
  full_name: string
  roll_number?: string
  class_id?: string
  gender?: string
  school_id: string
}

export interface Class {
  id: string
  grade: number
  section?: string
  school_id: string
}

export async function getStudents(params?: {
  class_id?: string
  school_id?: string
  grade?: number
  search?: string
  limit?: number
  offset?: number
}): Promise<PaginatedResponse<Student>> {
  const { data } = await api.get('/students', { params })
  return data
}

export async function getStudent(id: string): Promise<Student> {
  const { data } = await api.get(`/students/${id}`)
  return data
}

export async function createStudent(
  payload: CreateStudentPayload
): Promise<Student> {
  const { data } = await api.post('/students', payload)
  return data
}

export async function updateStudent(
  id: string,
  payload: Partial<Student>
): Promise<Student> {
  const { data } = await api.patch(`/students/${id}`, payload)
  return data
}

export async function deleteStudent(id: string): Promise<void> {
  await api.delete(`/students/${id}`)
}

export async function bulkImportStudents(
  formData: FormData
): Promise<{ imported: number; errors?: string[] }> {
  const { data } = await api.post('/students/bulk-import', formData)
  return data
}

export async function getClasses(params?: {
  school_id?: string
  limit?: number
  offset?: number
}): Promise<PaginatedResponse<Class>> {
  const { data } = await api.get('/classes', { params })
  return data
}
