import client from './client'

export interface ImageAsset {
  id: number
  file_path: string
  tags: string
  subject_id: number | null
  grade_range_min: number | null
  grade_range_max: number | null
  created_at: string | null
}

export interface ListImagesResponse {
  items: ImageAsset[]
  total: number
}

export async function getImages(params?: {
  tags?: string
  subject_id?: number
  grade?: number
}): Promise<ListImagesResponse> {
  const { data } = await client.get('/image-bank', { params })
  return data
}

export async function uploadImage(file: File, tags: string = ''): Promise<{id: number, file_path: string, tags: string, message: string}> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('tags', tags)
  
  const { data } = await client.post('/image-bank/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  
  return data
}
