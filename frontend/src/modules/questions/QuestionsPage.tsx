import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import * as questionsApi from '@/api/questions'
import * as aiApi from '@/api/ai'
import { useBooks } from '@/hooks/useBooks'
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
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog'
import { GenerationProgress } from '@/components/GenerationProgress'
import {
  Brain,
  Eye,
  Loader2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  ThumbsUp,
  ThumbsDown,
  Trash2,
  Sparkles,
  Plus,
} from 'lucide-react'
import type { Question } from '@/types'

const PAGE_SIZE = 20

const bloomLevelColors: Record<string, 'info' | 'success' | 'warning' | 'destructive' | 'secondary'> = {
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

const statusColors: Record<string, 'warning' | 'success' | 'destructive'> = {
  pending_review: 'warning',
  approved: 'success',
  rejected: 'destructive',
}

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'pending_review', label: 'Draft' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
]

const bloomOptions = [
  { value: '', label: 'All Bloom Levels' },
  { value: 'remember', label: 'Remember' },
  { value: 'understand', label: 'Understand' },
  { value: 'apply', label: 'Apply' },
  { value: 'analyze', label: 'Analyze' },
  { value: 'evaluate', label: 'Evaluate' },
  { value: 'create', label: 'Create' },
]

const difficultyOptions = [
  { value: '', label: 'All Difficulties' },
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
]

const statusDisplay: Record<string, string> = {
  pending_review: 'Draft',
  approved: 'Approved',
  rejected: 'Rejected',
}

function ViewQuestionDialog({
  question,
  open,
  onOpenChange,
}: {
  question: Question | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useTranslation()
  if (!question) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('questions.actions.view')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-1">{t('questions.table.question')}</p>
            <p className="text-sm whitespace-pre-wrap">{question.question_text_en}</p>
          </div>
          {question.options && question.options.length > 0 && (
            <div>
              <p className="text-sm text-muted-foreground mb-2">Options</p>
              <div className="space-y-2">
                {question.options.map((opt, i) => (
                  <div
                    key={opt.id}
                    className={`rounded-md border p-3 text-sm ${
                      opt.is_correct
                        ? 'border-green-500/30 bg-green-500/10 text-green-400'
                        : 'border-border'
                    }`}
                  >
                    <span className="mr-2 font-medium">{String.fromCharCode(65 + i)}.</span>
                    {opt.option_text_en}
                    {opt.is_correct && (
                      <Badge variant="success" className="ml-2">Correct</Badge>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {(() => {
            const correctOpt = question.options?.find(o => o.is_correct);
            return correctOpt ? (
              <div>
                <p className="text-sm text-muted-foreground mb-1">Correct Answer</p>
                <p className="text-sm text-green-400">{correctOpt.option_text_en}</p>
              </div>
            ) : null;
          })()}
          <div className="flex flex-wrap gap-2">
            <Badge variant={bloomLevelColors[question.bloom_level] || 'default'}>
              {question.bloom_level}
            </Badge>
            <Badge variant={difficultyColors[question.difficulty] || 'default'}>
              {question.difficulty}
            </Badge>
            <Badge variant={statusColors[question.approval_status] || 'default'}>
              {statusDisplay[question.approval_status] || question.approval_status}
            </Badge>
            <Badge variant="outline">{question.question_type}</Badge>
            <Badge variant="outline">{question.marks} marks</Badge>
          </div>
        </div>
        <DialogFooter>
          <DialogClose>
            <Button variant="outline">{t('common.close') || 'Close'}</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function RejectDialog({
  questionId,
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  questionId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (feedback: string) => void
  isPending: boolean
}) {
  const { t } = useTranslation()
  const [feedback, setFeedback] = useState('')

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('questions.actions.reject')}</DialogTitle>
          <DialogDescription>{t('questions.actions.reject_feedback')}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <Input
            placeholder="Provide reason for rejection..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />
        </div>
        <DialogFooter>
          <DialogClose>
            <Button type="button" variant="outline">{t('common.cancel')}</Button>
          </DialogClose>
          <Button
            variant="destructive"
            onClick={() => onConfirm(feedback)}
            disabled={!feedback.trim() || isPending}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ThumbsDown className="h-4 w-4" />
            )}
            {t('common.submit')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DeleteConfirmDialog({
  questionId,
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  questionId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  isPending: boolean
}) {
  const { t } = useTranslation()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('questions.actions.delete')}</DialogTitle>
          <DialogDescription>{t('questions.actions.confirm_delete')}</DialogDescription>
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

export default function QuestionsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [bloomFilter, setBloomFilter] = useState('')
  const [difficultyFilter, setDifficultyFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [bookFilter, setBookFilter] = useState('')
  const [offset, setOffset] = useState(0)

  const { data: booksData } = useBooks()
  const bookOptions = [
    { value: '', label: 'All Books' },
    ...(booksData?.items?.map(b => ({ value: String(b.id), label: b.title })) ?? []),
  ]
  const [viewQuestion, setViewQuestion] = useState<Question | null>(null)
  const [viewOpen, setViewOpen] = useState(false)
  const [rejectId, setRejectId] = useState<string | null>(null)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['questions', bloomFilter, difficultyFilter, statusFilter, bookFilter, offset],
    queryFn: () =>
      questionsApi.getQuestions({
        bloom_level: bloomFilter || undefined,
        difficulty: difficultyFilter || undefined,
        approval_status: statusFilter || undefined,
        book_id: bookFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  const approveMutation = useMutation({
    mutationFn: (id: string) => questionsApi.approveQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, feedback }: { id: string; feedback: string }) =>
      questionsApi.rejectQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      setRejectOpen(false)
      setRejectId(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => questionsApi.deleteQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      setDeleteOpen(false)
      setDeleteId(null)
    },
  })

  const handleView = useCallback((q: Question) => {
    setViewQuestion(q)
    setViewOpen(true)
  }, [])

  const handleApprove = useCallback((id: string) => {
    approveMutation.mutate(id)
  }, [approveMutation])

  const handleReject = useCallback((id: string) => {
    setRejectId(id)
    setRejectOpen(true)
  }, [])

  const handleRejectConfirm = useCallback((feedback: string) => {
    if (rejectId) {
      rejectMutation.mutate({ id: rejectId, feedback })
    }
  }, [rejectId, rejectMutation])

  const handleDeleteClick = useCallback((id: string) => {
    setDeleteId(id)
    setDeleteOpen(true)
  }, [])

  const handleDeleteConfirm = useCallback(() => {
    if (deleteId) {
      deleteMutation.mutate(deleteId)
    }
  }, [deleteId, deleteMutation])

  const [generateDialogOpen, setGenerateDialogOpen] = useState(false)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [genCount, setGenCount] = useState(10)
  const [genDifficulty, setGenDifficulty] = useState('medium')
  const [genLanguage, setGenLanguage] = useState('English')

  const startGenMutation = useMutation({
    mutationFn: () =>
      aiApi.startGeneration({
        concept_ids: [1], // Default fallback
        total_count: genCount,
        batch_size: 5,
        difficulty: genDifficulty,
        language: genLanguage,
      }),
    onSuccess: (data) => {
      setCurrentJobId(data.job_id)
    },
  })

  const handleOpenGenerate = useCallback(() => {
    setGenerateDialogOpen(true)
    setCurrentJobId(null)
    setGenCount(10)
    setGenDifficulty('medium')
    setGenLanguage('English')
  }, [])

  const handleStartGenerate = useCallback(() => {
    startGenMutation.mutate()
  }, [startGenMutation])

  const handleGenDone = useCallback(() => {
    setGenerateDialogOpen(false)
    setCurrentJobId(null)
    queryClient.invalidateQueries({ queryKey: ['questions'] })
  }, [queryClient])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('questions.title')}</h1>
          <p className="text-muted-foreground text-sm">
            {data ? `${data.total} questions` : ''}
          </p>
        </div>
        <Button variant="default" size="sm" onClick={handleOpenGenerate}>
          <Sparkles className="h-4 w-4 mr-1" />
          {t('questions.generate')}
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap gap-3">
            <Select
              options={bookOptions}
              placeholder="All Books"
              value={bookFilter}
              onChange={(e) => { setBookFilter(e.target.value); setOffset(0) }}
            />
            <Select
              options={bloomOptions}
              placeholder="All Bloom Levels"
              value={bloomFilter}
              onChange={(e) => { setBloomFilter(e.target.value); setOffset(0) }}
            />
            <Select
              options={difficultyOptions}
              placeholder="All Difficulties"
              value={difficultyFilter}
              onChange={(e) => { setDifficultyFilter(e.target.value); setOffset(0) }}
            />
            <Select
              options={statusOptions}
              placeholder="All Statuses"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setOffset(0) }}
            />
          </div>
        </CardHeader>
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
              <Brain className="h-12 w-12 text-muted-foreground/30 mb-4" />
              <p className="text-sm text-muted-foreground text-center max-w-md">
                {t('questions.empty')}
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">{t('questions.table.id')}</TableHead>
                    <TableHead>{t('questions.table.question')}</TableHead>
                    <TableHead className="w-24">{t('questions.table.bloom_level')}</TableHead>
                    <TableHead className="w-20">{t('questions.table.difficulty')}</TableHead>
                    <TableHead className="w-24">{t('questions.table.status')}</TableHead>
                    <TableHead className="w-28">{t('questions.table.type')}</TableHead>
                    <TableHead className="w-28">{t('questions.table.created_at')}</TableHead>
                    <TableHead className="w-32">{t('questions.table.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.items?.map((question, idx) => (
                    <TableRow key={question.id}>
                      <TableCell className="text-muted-foreground text-xs">
                        {offset + idx + 1}
                      </TableCell>
                      <TableCell className="max-w-md">
                        <span className="block truncate text-sm">
                          {question.question_text_en.length > 80
                            ? `${question.question_text_en.slice(0, 80)}...`
                            : question.question_text_en}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={bloomLevelColors[question.bloom_level] || 'default'}
                          className="capitalize"
                        >
                          {question.bloom_level}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={difficultyColors[question.difficulty] || 'default'}
                          className="capitalize"
                        >
                          {question.difficulty}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={statusColors[question.approval_status] || 'default'}
                        >
                          {statusDisplay[question.approval_status] || question.approval_status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground capitalize">
                        {question.question_type.replace(/_/g, ' ')}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(question.created_at).toLocaleDateString('en-GB', {
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
                            onClick={() => handleView(question)}
                            title={t('questions.actions.view')}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          {question.approval_status !== 'approved' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleApprove(question.id)}
                              disabled={approveMutation.isPending}
                              title={t('questions.actions.approve')}
                              className="text-green-500 hover:text-green-400"
                            >
                              <ThumbsUp className="h-4 w-4" />
                            </Button>
                          )}
                          {question.approval_status !== 'rejected' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleReject(question.id)}
                              disabled={rejectMutation.isPending}
                              title={t('questions.actions.reject')}
                              className="text-amber-500 hover:text-amber-400"
                            >
                              <ThumbsDown className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteClick(question.id)}
                            disabled={deleteMutation.isPending}
                            title={t('questions.actions.delete')}
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

      <ViewQuestionDialog
        question={viewQuestion}
        open={viewOpen}
        onOpenChange={(v) => { setViewOpen(v); if (!v) setViewQuestion(null) }}
      />

      <RejectDialog
        questionId={rejectId}
        open={rejectOpen}
        onOpenChange={(v) => { setRejectOpen(v); if (!v) setRejectId(null) }}
        onConfirm={handleRejectConfirm}
        isPending={rejectMutation.isPending}
      />

      <DeleteConfirmDialog
        questionId={deleteId}
        open={deleteOpen}
        onOpenChange={(v) => { setDeleteOpen(v); if (!v) setDeleteId(null) }}
        onConfirm={handleDeleteConfirm}
        isPending={deleteMutation.isPending}
      />

      <Dialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('ai.generate_title')}</DialogTitle>
            <DialogDescription>{t('ai.generate_description')}</DialogDescription>
          </DialogHeader>
          {!currentJobId ? (
            <div className="space-y-4 py-2">
              <div className="space-y-1">
                <label className="text-sm font-medium">{t('ai.question_count')}</label>
                <Select
                  options={[
                    { value: '5', label: '5' },
                    { value: '10', label: '10' },
                    { value: '25', label: '25' },
                    { value: '50', label: '50' },
                    { value: '100', label: '100' },
                  ]}
                  value={String(genCount)}
                  onChange={(e) => setGenCount(Number(e.target.value))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">{t('questions.table.difficulty')}</label>
                <Select
                  options={[
                    { value: 'easy', label: 'Easy' },
                    { value: 'medium', label: 'Medium' },
                    { value: 'hard', label: 'Hard' },
                  ]}
                  value={genDifficulty}
                  onChange={(e) => setGenDifficulty(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">Language</label>
                <Select
                  options={[
                    { value: 'English', label: 'English' },
                    { value: 'Hindi', label: 'Hindi' },
                    { value: 'Gujarati', label: 'Gujarati' },
                  ]}
                  value={genLanguage}
                  onChange={(e) => setGenLanguage(e.target.value)}
                />
              </div>
              <Button
                className="w-full"
                onClick={handleStartGenerate}
                disabled={startGenMutation.isPending}
              >
                {startGenMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <Sparkles className="h-4 w-4 mr-1" />
                )}
                {t('ai.start_generating')}
              </Button>
            </div>
          ) : (
            <GenerationProgress jobId={currentJobId} onDone={handleGenDone} />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
