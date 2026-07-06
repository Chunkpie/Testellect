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
