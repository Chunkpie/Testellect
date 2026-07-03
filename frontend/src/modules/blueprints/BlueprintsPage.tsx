import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import * as blueprintsApi from '@/api/blueprints'
import type { Blueprint } from '@/api/blueprints'
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
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
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
  FileEdit,
  Eye,
  Loader2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Trash2,
  Plus,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'

const PAGE_SIZE = 20

const subjectOptions = [
  { value: '1', label: 'Science' },
  { value: '2', label: 'Mathematics' },
  { value: '3', label: 'English' },
  { value: '4', label: 'Hindi' },
  { value: '5', label: 'Gujarati' },
  { value: '6', label: 'Social Science' },
]

const bloomLevelNames = [
  'remember',
  'understand',
  'apply',
  'analyze',
  'evaluate',
  'create',
]

const difficultyLevels = ['easy', 'medium', 'hard']

function SliderGroup({
  label,
  items,
  values,
  onChange,
  total,
}: {
  label: string
  items: string[]
  values: Record<string, number>
  onChange: (key: string, value: number) => void
  total: number
}) {
  const isValid = Math.abs(total - 100) < 1
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">{label}</Label>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-mono ${isValid ? 'text-green-400' : 'text-destructive'}`}>
            Total: {total}%
          </span>
          {!isValid && (
            <AlertTriangle className="h-4 w-4 text-destructive" />
          )}
        </div>
      </div>
      {items.map((key) => (
        <div key={key} className="space-y-1">
          <div className="flex items-center justify-between">
            <Label className="text-xs capitalize text-muted-foreground">{key}</Label>
            <span className="text-xs font-mono tabular-nums text-foreground">{values[key] || 0}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={values[key] || 0}
            onChange={(e) => onChange(key, Number(e.target.value))}
            className="w-full h-2 rounded-full appearance-none cursor-pointer
              bg-muted
              accent-primary
              [&::-webkit-slider-thumb]:appearance-none
              [&::-webkit-slider-thumb]:h-4
              [&::-webkit-slider-thumb]:w-4
              [&::-webkit-slider-thumb]:rounded-full
              [&::-webkit-slider-thumb]:bg-primary
              [&::-webkit-slider-thumb]:shadow"
          />
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>0%</span>
            <span>100%</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function DeleteConfirmDialog({
  blueprint,
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  blueprint: Blueprint | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  isPending: boolean
}) {
  const { t } = useTranslation()
  if (!blueprint) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('blueprints.delete')}</DialogTitle>
          <DialogDescription>
            {t('blueprints.confirm_delete')} &quot;{blueprint.name}&quot;
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

export default function BlueprintsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [view, setView] = useState<'list' | 'editor'>('list')
  const [editingBlueprint, setEditingBlueprint] = useState<Blueprint | null>(null)
  const [offset, setOffset] = useState(0)
  const [deleteTarget, setDeleteTarget] = useState<Blueprint | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [generatingId, setGeneratingId] = useState<number | null>(null)

  const [formName, setFormName] = useState('')
  const [formGrade, setFormGrade] = useState('')
  const [formSubject, setFormSubject] = useState('')
  const [formMarks, setFormMarks] = useState('40')
  const [formDuration, setFormDuration] = useState('60')
  const [formQuestions, setFormQuestions] = useState('10')
  const [formBloom, setFormBloom] = useState<Record<string, number>>(
    Object.fromEntries(bloomLevelNames.map((k) => [k, 0]))
  )
  const [formDifficulty, setFormDifficulty] = useState<Record<string, number>>(
    Object.fromEntries(difficultyLevels.map((k) => [k, 0]))
  )

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['blueprints', offset],
    queryFn: () => blueprintsApi.getBlueprints({ limit: PAGE_SIZE, offset }),
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  const createMutation = useMutation({
    mutationFn: () =>
      blueprintsApi.createBlueprint({
        name: formName,
        grade: Number(formGrade),
        subject_id: Number(formSubject),
        total_marks: Number(formMarks),
        total_questions: Number(formQuestions),
        duration_minutes: Number(formDuration),
        bloom_distribution: formBloom,
        difficulty_distribution: formDifficulty,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] })
      resetForm()
      setView('list')
    },
  })

  const updateMutation = useMutation({
    mutationFn: () =>
      blueprintsApi.updateBlueprint(editingBlueprint!.id, {
        name: formName,
        grade: Number(formGrade),
        subject_id: Number(formSubject),
        total_marks: Number(formMarks),
        total_questions: Number(formQuestions),
        duration_minutes: Number(formDuration),
        bloom_distribution: formBloom,
        difficulty_distribution: formDifficulty,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] })
      resetForm()
      setView('list')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => blueprintsApi.deleteBlueprint(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['blueprints'] })
      setDeleteOpen(false)
      setDeleteTarget(null)
    },
  })

  const generateMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name?: string }) =>
      blueprintsApi.generatePaperFromBlueprint(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      setGeneratingId(null)
    },
    onError: () => {
      setGeneratingId(null)
    },
  })

  const bloomTotal = Object.values(formBloom).reduce((a, b) => a + b, 0)
  const difficultyTotal = Object.values(formDifficulty).reduce((a, b) => a + b, 0)
  const isFormValid =
    formName.trim() &&
    formGrade &&
    formSubject &&
    Number(formMarks) > 0 &&
    Number(formDuration) > 0 &&
    Number(formQuestions) > 0 &&
    Math.abs(bloomTotal - 100) < 1 &&
    Math.abs(difficultyTotal - 100) < 1

  function resetForm() {
    setFormName('')
    setFormGrade('')
    setFormSubject('')
    setFormMarks('40')
    setFormDuration('60')
    setFormQuestions('10')
    setFormBloom(Object.fromEntries(bloomLevelNames.map((k) => [k, 0])))
    setFormDifficulty(Object.fromEntries(difficultyLevels.map((k) => [k, 0])))
    setEditingBlueprint(null)
  }

  function startCreate() {
    resetForm()
    setEditingBlueprint(null)
    setView('editor')
  }

  function startEdit(bp: Blueprint) {
    setEditingBlueprint(bp)
    setFormName(bp.name)
    setFormGrade(String(bp.grade))
    setFormSubject(String(bp.subject_id))
    setFormMarks(String(bp.total_marks))
    setFormDuration(String(bp.duration_minutes))
    setFormQuestions(String(bp.total_questions || 10))
    const bloom = typeof bp.bloom_distribution === 'string'
      ? JSON.parse(bp.bloom_distribution as string)
      : bp.bloom_distribution
    const difficulty = typeof bp.difficulty_distribution === 'string'
      ? JSON.parse(bp.difficulty_distribution as string)
      : bp.difficulty_distribution
    setFormBloom({
      remember: bloom.remember || 0,
      understand: bloom.understand || 0,
      apply: bloom.apply || 0,
      analyze: bloom.analyze || 0,
      evaluate: bloom.evaluate || 0,
      create: bloom.create || 0,
    })
    setFormDifficulty({
      easy: difficulty.easy || 0,
      medium: difficulty.medium || 0,
      hard: difficulty.hard || 0,
    })
    setView('editor')
  }

  const handleDeleteClick = useCallback((bp: Blueprint) => {
    setDeleteTarget(bp)
    setDeleteOpen(true)
  }, [])

  const handleDeleteConfirm = useCallback(() => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget.id)
    }
  }, [deleteTarget, deleteMutation])

  const handleGenerate = useCallback((bp: Blueprint) => {
    setGeneratingId(bp.id)
    generateMutation.mutate({ id: bp.id, name: `Paper from ${bp.name}` })
  }, [generateMutation])

  const handleBloomChange = useCallback((key: string, value: number) => {
    setFormBloom((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleDifficultyChange = useCallback((key: string, value: number) => {
    setFormDifficulty((prev) => ({ ...prev, [key]: value }))
  }, [])

  function handleSave() {
    if (!isFormValid) return
    if (editingBlueprint) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  function handleCancel() {
    resetForm()
    setView('list')
  }

  const subjectMap: Record<string, string> = Object.fromEntries(
    subjectOptions.map((s) => [s.value, s.label])
  )

  if (view === 'editor') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={handleCancel}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              {editingBlueprint ? t('blueprints.edit') : t('blueprints.create')}
            </h1>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>{t('blueprints.form.details') || 'Details'}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">{t('blueprints.form.name')}</Label>
                <Input
                  id="name"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g. Mid-Term Science Assessment"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="grade">{t('blueprints.form.grade')}</Label>
                <Input
                  id="grade"
                  type="number"
                  min={1}
                  max={12}
                  value={formGrade}
                  onChange={(e) => setFormGrade(e.target.value)}
                  placeholder="e.g. 10"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="subject">{t('blueprints.form.subject')}</Label>
                <Select
                  id="subject"
                  value={formSubject}
                  onChange={(e) => setFormSubject(e.target.value)}
                  placeholder="Select subject"
                  options={subjectOptions}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="marks">{t('blueprints.form.total_marks')}</Label>
                <Input
                  id="marks"
                  type="number"
                  min={1}
                  value={formMarks}
                  onChange={(e) => setFormMarks(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration">{t('blueprints.form.duration')}</Label>
                <Input
                  id="duration"
                  type="number"
                  min={1}
                  value={formDuration}
                  onChange={(e) => setFormDuration(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="questions">{t('blueprints.form.total_questions')}</Label>
                <Input
                  id="questions"
                  type="number"
                  min={1}
                  value={formQuestions}
                  onChange={(e) => setFormQuestions(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>{t('blueprints.form.bloom_distribution')}</CardTitle>
              </CardHeader>
              <CardContent>
                <SliderGroup
                  label=""
                  items={bloomLevelNames}
                  values={formBloom}
                  onChange={handleBloomChange}
                  total={bloomTotal}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>{t('blueprints.form.difficulty_distribution')}</CardTitle>
              </CardHeader>
              <CardContent>
                <SliderGroup
                  label=""
                  items={difficultyLevels}
                  values={formDifficulty}
                  onChange={handleDifficultyChange}
                  total={difficultyTotal}
                />
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={handleSave}
            disabled={!isFormValid || createMutation.isPending || updateMutation.isPending}
          >
            {(createMutation.isPending || updateMutation.isPending) ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
            {t('blueprints.form.save')}
          </Button>
          <Button variant="outline" onClick={handleCancel}>
            {t('blueprints.form.cancel')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('blueprints.title')}</h1>
          <p className="text-muted-foreground text-sm">
            {data ? `${data.total} blueprints` : ''}
          </p>
        </div>
        <Button variant="default" size="sm" onClick={startCreate}>
          <Plus className="h-4 w-4" />
          {t('blueprints.create')}
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
              <FileEdit className="h-12 w-12 text-muted-foreground/30 mb-4" />
              <p className="text-sm text-muted-foreground text-center max-w-md">
                {t('blueprints.empty')}
              </p>
              <Button variant="outline" size="sm" className="mt-4" onClick={startCreate}>
                <Plus className="h-4 w-4" />
                {t('blueprints.create')}
              </Button>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="w-16">Grade</TableHead>
                    <TableHead className="w-28">Subject</TableHead>
                    <TableHead className="w-24">Total Marks</TableHead>
                    <TableHead className="w-24">Duration</TableHead>
                    <TableHead className="w-28">Created</TableHead>
                    <TableHead className="w-36">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.items?.map((bp) => (
                    <TableRow key={bp.id}>
                      <TableCell>
                        <span className="text-sm font-medium">{bp.name}</span>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        Grade {bp.grade}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{subjectMap[String(bp.subject_id)] || `Subject ${bp.subject_id}`}</Badge>
                      </TableCell>
                      <TableCell className="text-sm">{bp.total_marks}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {bp.duration_minutes}m
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(bp.created_at).toLocaleDateString('en-GB', {
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
                            onClick={() => startEdit(bp)}
                            title={t('blueprints.edit')}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleGenerate(bp)}
                            disabled={generatingId === bp.id || generateMutation.isPending}
                            title={t('blueprints.generate_paper')}
                            className="text-blue-500 hover:text-blue-400"
                          >
                            {generatingId === bp.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Plus className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteClick(bp)}
                            disabled={deleteMutation.isPending}
                            title={t('blueprints.delete')}
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

      <DeleteConfirmDialog
        blueprint={deleteTarget}
        open={deleteOpen}
        onOpenChange={(v) => { setDeleteOpen(v); if (!v) setDeleteTarget(null) }}
        onConfirm={handleDeleteConfirm}
        isPending={deleteMutation.isPending}
      />
    </div>
  )
}
