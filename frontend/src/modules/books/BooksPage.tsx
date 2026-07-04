import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import * as subjectsApi from '@/api/subjects'
import { useBooks, useUploadBook, useExtractBook, useAnalyzeBook, useGenerateQuestions, useDeleteBook } from '@/hooks/useBooks'
import { useAuthStore } from '@/stores/authStore'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog'
import { Select } from '@/components/ui/select'
import { BookOpen, Upload, Loader2, AlertCircle, Trash2, FileText, Brain, Sparkles } from 'lucide-react'

function timeAgo(dateStr: string): string {
  const now = Date.now()
  const d = new Date(dateStr).getTime()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}


const statusColor: Record<string, string> = {
  uploaded: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  processing: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  ready: 'bg-green-500/10 text-green-400 border-green-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  failed_upload: 'bg-red-500/10 text-red-400 border-red-500/20',
  failed_extraction: 'bg-red-500/10 text-red-400 border-red-500/20',
}

export default function BooksPage() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [grade, setGrade] = useState('10')
  const [subjectId, setSubjectId] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const { data: booksData, isLoading, isError } = useBooks()
  const { data: subjectsData } = useQuery({ queryKey: ['subjects'], queryFn: () => subjectsApi.getSubjects() })

  const uploadMutation = useUploadBook()
  const extractMutation = useExtractBook()
  const analyzeMutation = useAnalyzeBook()
  const generateMutation = useGenerateQuestions()
  const deleteMutation = useDeleteBook()

  const handleUpload = () => {
    const file = fileRef.current?.files?.[0]
    if (!file || !title || !subjectId) return
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', title)
    formData.append('grade', grade)
    formData.append('subject_id', subjectId)
    uploadMutation.mutate(
      { formData, onProgress: undefined },
      {
        onSuccess: () => {
          alert('Book uploaded successfully')
          setUploadOpen(false)
          setTitle('')
          setGrade('10')
          setSubjectId('')
          if (fileRef.current) fileRef.current.value = ''
        },
        onError: (err: any) => alert(err?.response?.data?.detail || 'Upload failed'),
      }
    )
  }

  const handleDelete = (id: string) => {
    if (!confirm('Delete this book?')) return
    deleteMutation.mutate(id, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['books'] })
      },
      onError: (err: any) => alert(err?.response?.data?.detail || 'Delete failed'),
    })
  }

  const handleExtract = (id: string) => {
    extractMutation.mutate(id, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['books'] })
      },
      onError: (err: any) => alert(err?.response?.data?.detail || 'Extraction failed'),
    })
  }

  const handleAnalyze = (id: string) => {
    analyzeMutation.mutate(id, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['books'] })
      },
      onError: (err: any) => alert(err?.response?.data?.detail || 'Analysis failed'),
    })
  }

  const handleGenerateQuestions = (id: string) => {
    generateMutation.mutate(
      { id, params: { count: 10 } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ['books'] })
        },
        onError: (err: any) => alert(err?.response?.data?.detail || 'Generation failed'),
      }
    )
  }

  const books = booksData?.items ?? []
  const subjects = subjectsData?.items ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('nav.books')}</h1>
          <p className="text-muted-foreground text-sm mt-1">Upload and manage textbooks for AI analysis</p>
        </div>
        <Button onClick={() => setUploadOpen(true)}>
          <Upload className="h-4 w-4 mr-2" />
          Upload Textbook
        </Button>
      </div>

      {isLoading && (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      )}

      {isError && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive flex-1">{t('common.error')}</p>
          </CardContent>
        </Card>
      )}

      {!isLoading && !isError && (
        <>
          {books.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-16 gap-3">
                <BookOpen className="h-12 w-12 text-muted-foreground/40" />
                <p className="text-muted-foreground text-sm">No textbooks uploaded yet</p>
                <Button variant="outline" onClick={() => setUploadOpen(true)}>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload your first textbook
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Textbooks ({books.length})</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Subject</TableHead>
                      <TableHead>Grade</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Uploaded</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {books.map((book: any) => {
                      const subject = subjects.find((s: any) => s.id === book.subject_id)
                      const statusLabel = book.processing_status || 'uploaded'
                      const statusClass = statusColor[statusLabel] || 'bg-gray-500/10 text-gray-400 border-gray-500/20'
                      return (
                        <TableRow key={book.id}>
                          <TableCell className="font-medium">{book.title}</TableCell>
                          <TableCell>{subject?.name_en ?? `Subject #${book.subject_id}`}</TableCell>
                          <TableCell>Grade {book.grade}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className={statusClass}>
                              {statusLabel}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {book.created_at ? timeAgo(book.created_at) : '-'}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button variant="ghost" size="icon" title="Extract text" onClick={() => handleExtract(book.id)} disabled={extractMutation.isPending}>
                                <FileText className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="icon" title="AI Analysis" onClick={() => handleAnalyze(book.id)} disabled={analyzeMutation.isPending}>
                                <Brain className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="icon" title="Generate questions" onClick={() => handleGenerateQuestions(book.id)} disabled={generateMutation.isPending}>
                                <Sparkles className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="icon" title="Delete" onClick={() => handleDelete(book.id)} disabled={deleteMutation.isPending}>
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      )}

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload Textbook</DialogTitle>
            <DialogDescription>Upload a PDF textbook for AI-powered analysis and question generation.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Title</label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Mathematics Textbook Grade 10" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Subject</label>
              <Select
                value={subjectId}
                placeholder="Select subject"
                options={subjects.map((s: any) => ({ value: String(s.id), label: s.name_en }))}
                onChange={(e) => setSubjectId(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Grade</label>
              <Select
                value={grade}
                placeholder="Select grade"
                options={[1,2,3,4,5,6,7,8,9,10,11,12].map((g) => ({ value: String(g), label: `Grade ${g}` }))}
                onChange={(e) => setGrade(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">PDF File</label>
              <Input ref={fileRef} type="file" accept=".pdf" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUploadOpen(false)}>Cancel</Button>
            <Button onClick={handleUpload} disabled={!title || !subjectId || uploadMutation.isPending}>
              {uploadMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Upload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
