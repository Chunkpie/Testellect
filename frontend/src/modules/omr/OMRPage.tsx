import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import * as omrApi from '@/api/omr'
import type { OMRSession, OMRSessionDetail, EvaluatedAnswer, OMRSummary } from '@/api/omr'
import { getPapers } from '@/api/papers'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from '@/components/ui/dialog'
import { Scan, Download, Eye, Loader2, AlertCircle, ArrowLeft, Plus, CheckCircle2, XCircle, Upload } from 'lucide-react'
import api from '@/api/client'

function ResultsView({ results, summary, onBack }: { results: EvaluatedAnswer[], summary: OMRSummary, onBack: () => void }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('omr.results.title')}</h1>
        </div>
      </div>
      <Card className="border-none shadow-md bg-gradient-to-br from-green-500/10 to-transparent">
        <CardContent className="py-8 text-center">
          <p className="text-4xl font-bold text-foreground">
            {t('omr.results.score', { correct: summary.correct, total: summary.total, percentage: summary.percentage.toFixed(1) })}
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            {summary.correct} / {summary.total} ({summary.percentage.toFixed(1)}%)
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">{t('omr.results.question', { n: '' })}</TableHead>
                <TableHead>{t('omr.results.student_answer')}</TableHead>
                <TableHead>{t('omr.results.correct_answer')}</TableHead>
                <TableHead>{t('omr.results.result')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.length === 0 ? (
                <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground">No results found.</TableCell></TableRow>
              ) : (
                results.map((r) => (
                  <TableRow key={r.sequence}>
                    <TableCell className="font-medium">{t('omr.results.question', { n: r.sequence })}</TableCell>
                    <TableCell>{r.student_answer || '-'}</TableCell>
                    <TableCell>{r.correct_answer || '-'}</TableCell>
                    <TableCell>
                      {r.is_correct ? (
                        <Badge variant="success" className="gap-1 bg-green-500/10 text-green-600"><CheckCircle2 className="h-3 w-3" />{t('omr.results.correct')}</Badge>
                      ) : (
                        <Badge variant="destructive" className="gap-1 bg-red-500/10 text-red-600"><XCircle className="h-3 w-3" />{t('omr.results.incorrect')}</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function GenerateDialog({ open, onOpenChange }: { open: boolean, onOpenChange: (v: boolean) => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [paperId, setPaperId] = useState('')
  const [studentCount, setStudentCount] = useState('30')

  const { data: papersData, isLoading: papersLoading } = useQuery({
    queryKey: ['papers'],
    queryFn: () => getPapers({ limit: 200, offset: 0 }),
    enabled: open,
  })

  const generateMutation = useMutation({
    mutationFn: () => omrApi.generateOMR({ paper_id: parseInt(paperId, 10), student_count: parseInt(studentCount, 10) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['omr-sessions'] })
      onOpenChange(false)
      setPaperId('')
      setStudentCount('30')
    },
  })

  const paperOptions = (papersData?.items || []).map((p) => ({ value: String(p.id), label: `${p.name} (Grade ${p.grade})` }))

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('omr.generate')}</DialogTitle>
          <DialogDescription>Generate OMR answer sheets for a paper.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="paper">{t('omr.form.select_paper')}</Label>
            {papersLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading papers...</div>
            ) : (
              <Select id="paper" options={paperOptions} placeholder={t('omr.form.select_paper')} value={paperId} onChange={(e) => setPaperId(e.target.value)} />
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="count">{t('omr.form.student_count')}</Label>
            <Input id="count" type="number" min={1} max={200} value={studentCount} onChange={(e) => setStudentCount(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <DialogClose><Button type="button" variant="outline">{t('common.cancel')}</Button></DialogClose>
          <Button onClick={() => generateMutation.mutate()} disabled={!paperId || generateMutation.isPending}>
            {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Scan className="h-4 w-4 mr-2" />}
            {t('omr.form.generate')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function UploadDialog({ open, onOpenChange, batchId }: { open: boolean, onOpenChange: (v: boolean) => void, batchId: string }) {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  
  const uploadMutation = useMutation({
    mutationFn: async (f: File) => {
      const formData = new FormData()
      formData.append('file', f)
      await api.post(`/omr/${batchId}/scan-upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['omr-sessions'] })
      onOpenChange(false)
      setFile(null)
    }
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload Scanned OMR Sheet</DialogTitle>
          <DialogDescription>Upload an image or PDF of the completed OMR sheet for AI evaluation.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <Input type="file" accept="image/*,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={() => file && uploadMutation.mutate(file)} disabled={!file || uploadMutation.isPending}>
            {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Upload className="h-4 w-4 mr-2" />}
            Upload & Evaluate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default function OMRPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [generateOpen, setGenerateOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadBatchId, setUploadBatchId] = useState('')
  const [viewingSession, setViewingSession] = useState<OMRSessionDetail | null>(null)
  const [resultsData, setResultsData] = useState<{ results: EvaluatedAnswer[], summary: OMRSummary } | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['omr-sessions'],
    queryFn: () => omrApi.listSessions(),
  })

  const handleViewResults = useCallback(async (session: OMRSession) => {
    if (!session.batch_id) return
    try {
      const res = await omrApi.getResults(session.batch_id)
      if (res.results.length > 0) {
        setResultsData({ results: res.results, summary: res.summary })
      } else {
        const detail = await omrApi.getSession(session.batch_id)
        setViewingSession(detail)
      }
    } catch {
      try {
        const detail = await omrApi.getSession(session.batch_id)
        setViewingSession(detail)
      } catch {}
    }
  }, [])

  const handleDownload = useCallback(async (session: OMRSession) => {
    if (!session.batch_id) return
    try {
      const blob = await omrApi.downloadOMR(session.batch_id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `omr_${session.paper_name.replace(/\s+/g, '_')}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch {
      console.error('Download failed')
    }
  }, [])

  const handleUploadClick = (batchId: string) => {
    if (!batchId) return
    setUploadBatchId(batchId)
    setUploadOpen(true)
  }

  if (resultsData) {
    return <ResultsView results={resultsData.results} summary={resultsData.summary} onBack={() => setResultsData(null)} />
  }

  if (viewingSession) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setViewingSession(null)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-foreground">{viewingSession.paper_name}</h1>
            <p className="text-sm text-muted-foreground">{viewingSession.student_count} students &middot; {viewingSession.status}</p>
          </div>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Sheets</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {viewingSession.sheets.map((s, idx) => (
                  <TableRow key={s.id}>
                    <TableCell>{idx + 1}</TableCell>
                    <TableCell>
                      <Badge variant={s.status === 'generated' ? 'secondary' : 'success'}>{s.status}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(s.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" onClick={() => handleUploadClick(viewingSession.batch_id)}>
                        <Upload className="h-4 w-4 mr-2" /> Upload Scanned OMR
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">OMR Automation</h1>
          <p className="text-muted-foreground text-sm mt-1">{data ? `${data.total} assessment sessions` : 'Manage optical mark recognition sessions'}</p>
        </div>
        <Button onClick={() => setGenerateOpen(true)} className="shadow-lg shadow-primary/20">
          <Plus className="h-4 w-4 mr-2" />
          {t('omr.generate')}
        </Button>
      </div>

      <Card className="border-none shadow-md overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : isError ? (
            <div className="flex items-center justify-between p-6"><div className="flex items-center gap-2 text-sm text-destructive"><AlertCircle className="h-4 w-4" />{t('common.error')}</div><Button variant="outline" size="sm" onClick={() => refetch()}>{t('common.retry')}</Button></div>
          ) : data?.items?.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-4">
              <Scan className="h-12 w-12 text-muted-foreground/30 mb-4" />
              <p className="text-sm text-muted-foreground text-center max-w-md">{t('omr.empty')}</p>
            </div>
          ) : (
            <Table>
              <TableHeader className="bg-muted/10">
                <TableRow>
                  <TableHead className="w-16">{t('omr.table.id')}</TableHead>
                  <TableHead>{t('omr.table.paper')}</TableHead>
                  <TableHead className="w-32">{t('omr.table.created')}</TableHead>
                  <TableHead className="w-20">{t('omr.table.students')}</TableHead>
                  <TableHead className="w-24">{t('omr.table.status')}</TableHead>
                  <TableHead className="w-40">{t('omr.table.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items?.map((session, idx) => (
                  <TableRow key={session.batch_id || idx} className="hover:bg-muted/5">
                    <TableCell className="text-xs text-muted-foreground font-mono">{session.batch_id ? session.batch_id.slice(-8) : 'N/A'}</TableCell>
                    <TableCell><span className="text-sm font-medium">{session.paper_name}</span></TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(session.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </TableCell>
                    <TableCell className="text-sm">{session.student_count}</TableCell>
                    <TableCell><Badge variant={session.has_results ? 'success' : 'secondary'}>{session.has_results ? 'Evaluated' : 'Generated'}</Badge></TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" onClick={() => handleDownload(session)} title={t('omr.download_pdf')} className="text-blue-500 hover:text-blue-400 hover:bg-blue-500/10">
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleUploadClick(session.batch_id)} title="Upload Scanned Sheet" className="text-amber-500 hover:text-amber-400 hover:bg-amber-500/10">
                          <Upload className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleViewResults(session)} title={t('omr.view_results')} className="text-primary hover:text-primary/80 hover:bg-primary/10">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <GenerateDialog open={generateOpen} onOpenChange={setGenerateOpen} />
      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} batchId={uploadBatchId} />
    </div>
  )
}
