import api from './client'

export async function getSubjects(params?: { grade?: string }): Promise<any> {
  const { data } = await api.get('/subjects', { params })
  return data
}
