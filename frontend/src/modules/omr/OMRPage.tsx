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
import { Scan, Download, Eye, Loader2, ArrowLeft, Plus, CheckCircle2, XCircle, Upload, Camera, AlertCircle, Trash2, FileText } from 'lucide-react'
import api from '@/api/client'
import { ScannerDialog } from './ScannerDialog'
import { useAuthStore } from '@/stores/authStore'
import * as studentsApi from '@/api/students'

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

function StartSessionDialog({ open, onOpenChange, onSuccess }: { open: boolean, onOpenChange: (v: boolean) => void, onSuccess: (batchId: string) => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [paperId, setPaperId] = useState('')
  const [classId, setClassId] = useState('')
  const [totalQuestions, setTotalQuestions] = useState('')
  const user = useAuthStore((s) => s.user)

  const { data: papersData, isLoading: papersLoading } = useQuery({
    queryKey: ['papers'],
    queryFn: () => getPapers({ limit: 200, offset: 0 }),
    enabled: open,
  })

  const { data: classesData, isLoading: classesLoading } = useQuery({
    queryKey: ['classes', user?.school_id],
    queryFn: () => studentsApi.getClasses({ school_id: user?.school_id ? String(user.school_id) : undefined, limit: 200 }),
    enabled: open && !!user?.school_id,
  })

  const generateMutation = useMutation({
    mutationFn: () => omrApi.generateOMR({ 
      paper_id: parseInt(paperId, 10), 
      class_id: parseInt(classId, 10),
      total_questions: totalQuestions ? parseInt(totalQuestions, 10) : undefined
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['omr-sessions'] })
      onOpenChange(false)
      setPaperId('')
      setClassId('')
      setTotalQuestions('')
      onSuccess(data.batch_id)
    },
  })

  const paperOptions = (papersData?.items || []).map((p) => ({ value: String(p.id), label: `${p.name} (Grade ${p.grade})` }))
  const classOptions = (classesData?.items || []).map((c) => ({ 
    value: String(c.id), 
    label: `Class ${c.grade}${c.section ? ' - ' + c.section : ''}` 
  }))

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Generate OMR Sheets</DialogTitle>
          <DialogDescription>Select a paper and class to generate personalized OMR sheets for each student.</DialogDescription>
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
            <Label htmlFor="class">Select Class</Label>
            {classesLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading classes...</div>
            ) : (
              <Select id="class" options={classOptions} placeholder="Select Class (Updated)" value={classId} onChange={(e) => {
                console.log("Class options:", classOptions);
                setClassId(e.target.value);
              }} />
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="totalQuestions">Total Questions (Optional)</Label>
            <Input 
              id="totalQuestions" 
              type="number" 
              placeholder="Leave blank to use default from blueprint" 
              value={totalQuestions} 
              onChange={(e) => setTotalQuestions(e.target.value)} 
              min="1" 
              max="100" 
            />
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button onClick={() => generateMutation.mutate()} disabled={!paperId || !classId || generateMutation.isPending}>
            {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <FileText className="h-4 w-4 mr-2" />}
            Generate Sheets
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ScanSelectDialog({ open, onOpenChange, sessions, onSuccess }: { open: boolean, onOpenChange: (v: boolean) => void, sessions: OMRSession[], onSuccess: (batchId: string) => void }) {
  const { t } = useTranslation()
  const [batchId, setBatchId] = useState('')

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Start Scanning Session</DialogTitle>
          <DialogDescription>Select an OMR session to start scanning sheets.</DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <Select 
            options={sessions.map(s => ({ value: s.batch_id, label: `${s.paper_name} (${new Date(s.created_at).toLocaleDateString()})` }))}
            value={batchId}
            onChange={(e) => setBatchId(e.target.value)}
            placeholder="Select a session"
          />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
          <Button onClick={() => { onOpenChange(false); onSuccess(batchId) }} disabled={!batchId}>
            <Scan className="h-4 w-4 mr-2" /> Start Scanning
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// Removed inline UploadDialog

export default function OMRPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [generateOpen, setGenerateOpen] = useState(false)
  const [scanSelectOpen, setScanSelectOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadBatchId, setUploadBatchId] = useState('')
  const [viewingSession, setViewingSession] = useState<OMRSessionDetail | null>(null)
  const [resultsData, setResultsData] = useState<{ results: EvaluatedAnswer[], summary: OMRSummary } | null>(null)
  const [deleteBatchId, setDeleteBatchId] = useState<string | null>(null)

  const [downloadTarget, setDownloadTarget] = useState<{batchId: string, studentId: number} | null>(null)
  const [downloadLanguage, setDownloadLanguage] = useState<'english' | 'hindi' | 'gujarati'>('english')
  const [isDownloadingReport, setIsDownloadingReport] = useState(false)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['omr-sessions'],
    queryFn: () => omrApi.listSessions(),
  })

  const deleteMutation = useMutation({
    mutationFn: omrApi.deleteSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['omr-sessions'] })
      setDeleteBatchId(null)
    }
  })

  const handleViewResults = useCallback(async (session: OMRSession) => {
    if (!session.batch_id) return
    try {
      const detail = await omrApi.getSession(session.batch_id)
      setViewingSession(detail)
    } catch {
      console.error('Failed to view session details')
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
      setTimeout(() => window.URL.revokeObjectURL(url), 1000)
    } catch {
      console.error('Download failed')
    }
  }, [])

  const handleDownloadReport = useCallback(async () => {
    if (!downloadTarget) return
    const { batchId, studentId } = downloadTarget
    setIsDownloadingReport(true)
    try {
      const response = await api.get(`/omr/${encodeURIComponent(batchId)}/student/${studentId}/download-reports?lang=${downloadLanguage}`, {
        responseType: 'blob'
      })
      const url = window.URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      let filename = `Reports_Student_${studentId}_${downloadLanguage}.zip`
      const disposition = response.headers['content-disposition']
      if (disposition && disposition.indexOf('filename=') !== -1) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition)
        if (matches != null && matches[1]) { 
          filename = matches[1].replace(/['"]/g, '')
        }
      }
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => window.URL.revokeObjectURL(url), 1000)
      setDownloadTarget(null)
    } catch (e) {
      console.error('Failed to download report', e)
      alert('Failed to download report')
    } finally {
      setIsDownloadingReport(false)
    }
  }, [downloadTarget, downloadLanguage])

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
                  <TableHead>Student</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {viewingSession.sheets.map((s, idx) => (
                  <TableRow key={s.id}>
                    <TableCell>{idx + 1}</TableCell>
                    <TableCell className="font-medium">{s.student_name || 'Unknown'}</TableCell>
                    <TableCell>
                      <Badge variant={s.status === 'generated' ? 'secondary' : 'success'}>{s.status}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(s.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </TableCell>
                    <TableCell className="space-x-2">
                      {s.status === 'generated' ? (
                        <Button variant="outline" size="sm" onClick={() => handleUploadClick(viewingSession.batch_id)}>
                          <Upload className="h-4 w-4 mr-2" /> Upload Scanned OMR
                        </Button>
                      ) : (
                        <Button variant="default" size="sm" onClick={() => {
                          setDownloadLanguage('english')
                          setDownloadTarget({ batchId: viewingSession.batch_id, studentId: s.student_id || 1 })
                        }}>
                          <Download className="h-4 w-4 mr-2" /> Download Reports
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      {uploadBatchId && <ScannerDialog open={uploadOpen} onOpenChange={setUploadOpen} batchId={uploadBatchId} grade={viewingSession.grade} initialMode="upload" />}
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">OMR Automation</h1>
          <p className="text-muted-foreground">{data ? `${data.total} assessment sessions` : 'Manage optical mark recognition sessions'}</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => setGenerateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> Generate OMR Sheets
          </Button>
          <Button onClick={() => setScanSelectOpen(true)}>
            <Scan className="mr-2 h-4 w-4" /> Start Scanning Session
          </Button>
        </div>
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
                        <Button variant="ghost" size="icon" onClick={() => setDeleteBatchId(session.batch_id)} disabled={deleteMutation.isPending} title="Delete Session" className="text-destructive hover:text-destructive/80 hover:bg-destructive/10">
                          <Trash2 className="h-4 w-4" />
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

      <StartSessionDialog 
        open={generateOpen} 
        onOpenChange={setGenerateOpen} 
        onSuccess={(batchId) => {
          // Sheets are generated, user can now download them from the table
        }} 
      />
      <ScanSelectDialog
        open={scanSelectOpen}
        onOpenChange={setScanSelectOpen}
        sessions={data?.items || []}
        onSuccess={(batchId) => {
          setUploadBatchId(batchId)
          setUploadOpen(true)
        }}
      />
      {uploadBatchId && <ScannerDialog open={uploadOpen} onOpenChange={setUploadOpen} batchId={uploadBatchId} grade={data?.items.find(s => s.batch_id === uploadBatchId)?.grade} initialMode="upload" />}

      <Dialog open={!!deleteBatchId} onOpenChange={(open) => !open && setDeleteBatchId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center text-destructive">
              <AlertCircle className="h-5 w-5 mr-2" />
              Delete Session
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this session? All associated OMR sheets and evaluation results will be permanently removed.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setDeleteBatchId(null)} disabled={deleteMutation.isPending}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={() => deleteBatchId && deleteMutation.mutate(deleteBatchId)} 
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!downloadTarget} onOpenChange={(v) => { if (!v) setDownloadTarget(null) }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Download Student Report</DialogTitle>
            <DialogDescription>
              Select the language you want to generate the PDF report in.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3 py-4">
            <Button 
              variant={downloadLanguage === 'english' ? 'default' : 'outline'} 
              onClick={() => setDownloadLanguage('english')}
              className="justify-start"
            >
              English
            </Button>
            <Button 
              variant={downloadLanguage === 'hindi' ? 'default' : 'outline'} 
              onClick={() => setDownloadLanguage('hindi')}
              className="justify-start"
            >
              Hindi
            </Button>
            <Button 
              variant={downloadLanguage === 'gujarati' ? 'default' : 'outline'} 
              onClick={() => setDownloadLanguage('gujarati')}
              className="justify-start"
            >
              Gujarati
            </Button>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDownloadTarget(null)}>Cancel</Button>
            <Button 
              type="button" 
              onClick={handleDownloadReport} 
              disabled={isDownloadingReport} 
            >
              {isDownloadingReport ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
              {isDownloadingReport ? 'Generating...' : 'Download PDF'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
