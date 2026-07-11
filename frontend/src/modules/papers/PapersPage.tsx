import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import * as papersApi from '@/api/papers'
import type { Paper } from '@/api/papers'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Select } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog'
import {
  FileText,
  Eye,
  Download,
  Loader2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Trash2,
  ArrowLeft,
  Pencil,
  Scan,
} from 'lucide-react'

const PAGE_SIZE = 20

const bloomLevelColors: Record<string, 'info' | 'success' | 'warning' | 'secondary' | 'destructive'> = {
  remember: 'info',
  understand: 'success',
  apply: 'warning',
  analyze: 'secondary',
  evaluate: 'destructive',
  create: 'info',
}

const difficultyColors: Record<string, 'success' | 'warning' | 'destructive'> = {
  easy: 'success',
  medium: 'warning',
  hard: 'destructive',
}

const subjectNames: Record<string, string> = {
  '1': 'Science',
  '2': 'Mathematics',
  '3': 'English',
  '4': 'Hindi',
  '5': 'Gujarati',
  '6': 'Social Science',
}

function RenameDialog({
  paper,
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  paper: Paper | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (newName: string) => void
  isPending: boolean
}) {
  const { t } = useTranslation()
  const [name, setName] = useState('')

  useEffect(() => {
    if (paper) {
      setName(paper.name)
    }
  }, [paper])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Rename Paper</DialogTitle>
        </DialogHeader>
        <div className="py-4">
          <Input 
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter new paper name"
            disabled={isPending}
          />
        </div>
        <DialogFooter>
          <DialogClose>
            <Button type="button" variant="outline">{t('common.cancel')}</Button>
          </DialogClose>
          <Button
            onClick={() => onConfirm(name)}
            disabled={isPending || !name.trim()}
          >
            {isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DeleteConfirmDialog({
  paper,
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  paper: Paper | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  isPending: boolean
}) {
  const { t } = useTranslation()
  if (!paper) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('papers.delete')}</DialogTitle>
          <DialogDescription>
            {t('papers.confirm_delete')} &quot;{paper.name}&quot;
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose>
            <Button type="button" variant="outline">{t('common.cancel')}</Button>
          </DialogClose>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            {t('common.delete')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function PaperDetailView({
  paper,
  onBack,
}: {
  paper: Paper | null
  onBack: () => void
}) {
  const { t } = useTranslation()
  const [downloading, setDownloading] = useState(false)
  const [pdfLanguage, setPdfLanguage] = useState('English')

  const handleDownload = useCallback(async () => {
    if (!paper) return
    setDownloading(true)
    try {
      const blob = await papersApi.exportPaperPdf(paper.id, pdfLanguage.toLowerCase())
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${paper.name.replace(/\s+/g, '_')}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => window.URL.revokeObjectURL(url), 1000)
    } catch {
      // fallback: try download endpoint
      try {
        const blob = await papersApi.downloadPaper(paper.id)
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${paper.name.replace(/\s+/g, '_')}.pdf`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        setTimeout(() => window.URL.revokeObjectURL(url), 1000)
      } catch {
        console.error('Failed to download paper')
      }
    } finally {
      setDownloading(false)
    }
  }, [paper])

  if (!paper) return null

  const questions = paper.questions || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-foreground">{paper.name}</h1>
            <p className="text-muted-foreground text-sm">
              Grade {paper.grade} &middot; {subjectNames[String(paper.subject_id)] || `Subject ${paper.subject_id}`}
              &nbsp;&middot; {paper.total_marks} marks &middot; {paper.duration_minutes} min
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Select
            options={[
              { value: 'English', label: 'English' },
              { value: 'Hindi', label: 'Hindi' },
              { value: 'Gujarati', label: 'Gujarati' },
            ]}
            value={pdfLanguage}
            onChange={(e) => setPdfLanguage(e.target.value)}
            className="w-32"
          />
          <Button
            variant="default"
            size="sm"
            onClick={handleDownload}
            disabled={downloading}
          >
            {downloading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            {t('papers.download_pdf')}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            {t('papers.questions')}
            <span className="text-sm font-normal text-muted-foreground ml-2">
              ({t('papers.total_questions', { count: questions.length })})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {questions.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <p className="text-sm text-muted-foreground">No questions loaded for this paper.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {questions.map((q, idx) => (
                <div key={q.id || idx} className="rounded-lg border p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-semibold text-muted-foreground bg-muted px-2 py-0.5 rounded">
                          {t('papers.question_number', { n: q.sequence || idx + 1 })}
                        </span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{q.question_text}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant={bloomLevelColors[q.bloom_level] || 'default'} className="capitalize">
                        {q.bloom_level}
                      </Badge>
                      <Badge variant={difficultyColors[q.difficulty] || 'default'} className="capitalize">
                        {q.difficulty}
                      </Badge>
                      <Badge variant="outline">{q.marks} marks</Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

import { CustomPaperDialog } from './CustomPaperDialog'

export default function PapersPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [customDialogOpen, setCustomDialogOpen] = useState(false)
  const [offset, setOffset] = useState(0)
  const [viewingPaper, setViewingPaper] = useState<Paper | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Paper | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [renameTarget, setRenameTarget] = useState<Paper | null>(null)
  const [renameOpen, setRenameOpen] = useState(false)
  const [downloadTarget, setDownloadTarget] = useState<Paper | null>(null)
  const [downloadLanguage, setDownloadLanguage] = useState<'english' | 'hindi' | 'gujarati'>('english')
  const [isDownloading, setIsDownloading] = useState(false)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['papers', offset],
    queryFn: () => papersApi.getPapers({ limit: PAGE_SIZE, offset }),
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  const deleteMutation = useMutation({
    mutationFn: (id: number) => papersApi.deletePaper(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      setDeleteOpen(false)
      setDeleteTarget(null)
    },
  })

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => papersApi.renamePaper(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      setRenameOpen(false)
      setRenameTarget(null)
    },
  })

  const handleView = useCallback(async (paper: Paper) => {
    try {
      const full = await papersApi.getPaper(paper.id)
      setViewingPaper(full)
    } catch {
      setViewingPaper(paper)
    }
  }, [])

  const handleRenameClick = useCallback((paper: Paper) => {
    setRenameTarget(paper)
    setRenameOpen(true)
  }, [])

  const handleRenameConfirm = useCallback((newName: string) => {
    if (renameTarget) {
      renameMutation.mutate({ id: renameTarget.id, name: newName })
    }
  }, [renameTarget, renameMutation])

  const handleDeleteClick = useCallback((paper: Paper) => {
    setDeleteTarget(paper)
    setDeleteOpen(true)
  }, [])

  const handleDeleteConfirm = useCallback(() => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget.id)
    }
  }, [deleteTarget, deleteMutation])

  if (viewingPaper) {
    return (
      <PaperDetailView
        paper={viewingPaper}
        onBack={() => setViewingPaper(null)}
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('papers.title')}</h1>
          <p className="text-muted-foreground text-sm">
            {data ? `${data.total} papers` : ''}
          </p>
        </div>
        <Button onClick={() => setCustomDialogOpen(true)}>
          Generate Custom Paper
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : isError ? (
            <div className="flex items-center justify-between p-6">
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                {t('common.error')}
              </div>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                {t('common.retry')}
              </Button>
            </div>
          ) : data?.items?.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-4">
              <FileText className="h-12 w-12 text-muted-foreground/30 mb-4" />
              <p className="text-sm text-muted-foreground text-center max-w-md">
                {t('papers.empty')}
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="w-16">Grade</TableHead>
                    <TableHead className="w-28">Subject</TableHead>
                    <TableHead className="w-20">Marks</TableHead>
                    <TableHead className="w-20">Duration</TableHead>
                    <TableHead className="w-20">Questions</TableHead>
                    <TableHead className="w-28">Created</TableHead>
                    <TableHead className="w-32">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.items?.map((paper) => (
                    <TableRow key={paper.id}>
                      <TableCell>
                        <span className="text-sm font-medium">{paper.name}</span>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        Grade {paper.grade}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {subjectNames[String(paper.subject_id)] || `Subject ${paper.subject_id}`}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">{paper.total_marks}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {paper.duration_minutes}m
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {paper.total_questions}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(paper.created_at).toLocaleDateString('en-GB', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleView(paper)}
                            title={t('papers.view')}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title={t('papers.download_pdf')}
                            className="text-blue-500 hover:text-blue-400"
                            onClick={() => {
                              setDownloadLanguage('english')
                              setDownloadTarget(paper)
                            }}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Generate OMR Sheet"
                            className="text-emerald-500 hover:text-emerald-400 hover:bg-emerald-500/10"
                            onClick={() => window.location.href = '/omr'}
                          >
                            <Scan className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRenameClick(paper)}
                            disabled={renameMutation.isPending}
                            title="Rename"
                            className="text-muted-foreground hover:text-primary"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteClick(paper)}
                            disabled={deleteMutation.isPending}
                            title={t('papers.delete')}
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {data && data.total > PAGE_SIZE && (
                <div className="flex items-center justify-between border-t px-6 py-3">
                  <p className="text-sm text-muted-foreground">
                    Showing {offset + 1}-{Math.min(offset + PAGE_SIZE, data.total)} of {data.total}
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                      disabled={offset === 0}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm text-muted-foreground px-2">
                      {currentPage} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setOffset((o) => o + PAGE_SIZE)}
                      disabled={offset + PAGE_SIZE >= data.total}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <RenameDialog
        paper={renameTarget}
        open={renameOpen}
        onOpenChange={(v) => { setRenameOpen(v); if (!v) setRenameTarget(null) }}
        onConfirm={handleRenameConfirm}
        isPending={renameMutation.isPending}
      />
      <DeleteConfirmDialog
        paper={deleteTarget}
        open={deleteOpen}
        onOpenChange={(v) => { setDeleteOpen(v); if (!v) setDeleteTarget(null) }}
        onConfirm={handleDeleteConfirm}
        isPending={deleteMutation.isPending}
      />

      <Dialog open={!!downloadTarget} onOpenChange={(v) => { if (!v) setDownloadTarget(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Download Question Paper</DialogTitle>
            <DialogDescription>
              Select the language you want to generate the PDF in.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3 my-4">
            <Button 
              variant={downloadLanguage === 'english' ? 'default' : 'outline'} 
              onClick={() => setDownloadLanguage('english')}
            >
              English
            </Button>
            <Button 
              variant={downloadLanguage === 'hindi' ? 'default' : 'outline'} 
              onClick={() => setDownloadLanguage('hindi')}
            >
              Hindi
            </Button>
            <Button 
              variant={downloadLanguage === 'gujarati' ? 'default' : 'outline'} 
              onClick={() => setDownloadLanguage('gujarati')}
            >
              Gujarati
            </Button>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDownloadTarget(null)}>Cancel</Button>
            <Button 
              disabled={isDownloading} 
              onClick={async () => {
                if (!downloadTarget) return;
                setIsDownloading(true);
                try {
                  const blob = await papersApi.exportPaperPdf(downloadTarget.id, downloadLanguage);
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${downloadTarget.name.replace(/\s+/g, '_')}_${downloadLanguage}.pdf`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  setTimeout(() => window.URL.revokeObjectURL(url), 1000);
                  setDownloadTarget(null);
                } catch {
                   alert('Failed to download paper');
                } finally {
                  setIsDownloading(false);
                }
              }}
            >
              {isDownloading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
              {isDownloading ? 'Generating...' : 'Download PDF'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <CustomPaperDialog open={customDialogOpen} onOpenChange={setCustomDialogOpen} />
    </div>
  )
}
