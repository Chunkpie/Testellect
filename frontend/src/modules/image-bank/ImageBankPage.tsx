import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2, Upload, Trash2, Image as ImageIcon } from 'lucide-react'

export interface ImageAsset {
  id: number
  file_path: string
  tags: string
  subject_id: number | null
  grade_range_min: number | null
  grade_range_max: number | null
  created_at: string
}

export default function ImageBankPage() {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [tags, setTags] = useState('')
  const [uploading, setUploading] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['image-assets'],
    queryFn: async () => {
      const { data } = await api.get('/image-bank')
      return data.items as ImageAsset[]
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/image-bank/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['image-assets'] })
    },
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('tags', tags)
      
      await api.post('/image-bank/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      
      setFile(null)
      setTags('')
      queryClient.invalidateQueries({ queryKey: ['image-assets'] })
    } catch (e) {
      console.error(e)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Image Bank</h1>
          <p className="text-muted-foreground text-sm">Upload images for lower grade questions</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload New Image</CardTitle>
          <CardDescription>Tag images so AI can automatically find them.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div className="grid w-full max-w-sm items-center gap-1.5">
              <Label htmlFor="picture">Image File</Label>
              <Input id="picture" type="file" accept="image/*" onChange={handleFileChange} />
            </div>
            <div className="grid w-full max-w-sm items-center gap-1.5">
              <Label htmlFor="tags">Tags (comma separated)</Label>
              <Input id="tags" placeholder="e.g. apple, tree, house" value={tags} onChange={e => setTags(e.target.value)} />
            </div>
            <Button onClick={handleUpload} disabled={!file || uploading}>
              {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
              Upload
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Image Library</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center p-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {data?.length === 0 ? (
                <div className="col-span-full py-12 flex flex-col items-center justify-center text-muted-foreground">
                  <ImageIcon className="h-12 w-12 mb-2 opacity-20" />
                  <p>No images uploaded yet.</p>
                </div>
              ) : (
                data?.map(img => (
                  <div key={img.id} className="relative group rounded-md border overflow-hidden bg-muted flex flex-col aspect-square">
                    <img
                      src={`http://localhost:8000/api/v1${img.file_path}`}
                      alt={img.tags}
                      className="object-cover w-full h-full"
                    />
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-2">
                      <p className="text-xs text-white truncate mb-1">Tags: {img.tags}</p>
                      <Button size="sm" variant="destructive" className="h-7 w-full text-xs" onClick={() => deleteMutation.mutate(img.id)}>
                        <Trash2 className="h-3 w-3 mr-1" /> Delete
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
