import api from './client'
import type { PaginatedResponse } from '@/types'

export interface School {
  id: string
  name: string
  address?: string
  medium?: string
  board?: string
  udise_code?: string
  created_at: string
  updated_at: string
}

export interface SchoolUser {
  id: string
  email: string
  name: string
  role: string
  school_id?: string
  is_active: boolean
  created_at: string
}

export interface Backup {
  id: string
  filename: string
  size: number
  created_at: string
}

export async function getSchool(id: string): Promise<School> {
  const { data } = await api.get(`/schools/${id}`)
  return data
}

export async function updateSchool(
  id: string,
  payload: Partial<School>
): Promise<School> {
  const { data } = await api.patch(`/schools/${id}`, payload)
  return data
}

export async function getSchoolUsers(params?: {
  school_id?: string
  limit?: number
  offset?: number
}): Promise<PaginatedResponse<SchoolUser>> {
  const { data } = await api.get('/schools/users', { params })
  return data
}

export async function createUser(payload: {
  email: string
  name: string
  role: string
  school_id: string
}): Promise<SchoolUser> {
  const { data } = await api.post('/schools/users', payload)
  return data
}

export async function triggerBackup(): Promise<{ job_id: string }> {
  const { data } = await api.post('/schools/backup')
  return data
}

export async function listBackups(): Promise<Backup[]> {
  const { data } = await api.get('/schools/backups')
  return data
}
