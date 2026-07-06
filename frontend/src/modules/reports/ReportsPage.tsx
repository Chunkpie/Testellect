import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import * as analyticsApi from '@/api/analytics'
import type { DashboardStats, SubjectPerformance, BloomDistribution, TrendData, Report } from '@/api/analytics'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Users, GraduationCap, FileText, Brain, BarChart3, TrendingUp, Download, Trash2, Loader2, AlertCircle, Plus, ChevronUp, ChevronDown, Minus } from 'lucide-react'

const reportTypeOptions = [
  { value: 'school_summary', label: 'School Summary' },
  { value: 'class_performance', label: 'Class Performance' },
  { value: 'student_detail', label: 'Student Detail' },
]

const bloomColors: Record<string, string> = {
  remember: 'bg-blue-500',
  understand: 'bg-green-500',
  apply: 'bg-amber-500',
  analyze: 'bg-purple-500',
  evaluate: 'bg-red-500',
  create: 'bg-pink-500',
}

const statCards: { key: keyof DashboardStats, icon: any, label: string, color: string, gradient: string, format?: (v: number) => string }[] = [
  { key: 'total_students', icon: Users, label: 'reports.stats.total_students', color: 'text-cyan-600 dark:text-cyan-400', gradient: 'from-cyan-500/20 to-blue-500/5' },
  { key: 'total_teachers', icon: GraduationCap, label: 'reports.stats.total_teachers', color: 'text-rose-600 dark:text-rose-400', gradient: 'from-rose-500/20 to-orange-500/5' },
  { key: 'total_assessments', icon: FileText, label: 'reports.stats.total_assessments', color: 'text-amber-600 dark:text-amber-400', gradient: 'from-amber-500/20 to-yellow-500/5' },
  { key: 'total_questions', icon: Brain, label: 'reports.stats.total_questions', color: 'text-purple-600 dark:text-purple-400', gradient: 'from-purple-500/20 to-pink-500/5' },
  { key: 'average_score', icon: BarChart3, label: 'reports.stats.average_score', color: 'text-green-600 dark:text-green-400', gradient: 'from-green-500/20 to-emerald-500/5', format: (v) => `${v}%` },
  { key: 'completion_rate', icon: TrendingUp, label: 'reports.stats.completion_rate', color: 'text-blue-600 dark:text-blue-400', gradient: 'from-blue-500/20 to-indigo-500/5', format: (v) => `${v}%` },
]

function StatCardsGrid({ data, isLoading }: { data?: DashboardStats; isLoading: boolean }) {
  const { t } = useTranslation()
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {statCards.map((card) => {
        const Icon = card.icon
        const value = data ? data[card.key] : undefined
        return (
          <Card key={card.key} className={`border-none shadow-sm bg-gradient-to-br ${card.gradient} hover:shadow-md transition-all duration-300 hover:-translate-y-1`}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{t(card.label)}</p>
                  {isLoading ? (
                    <Skeleton className="h-8 w-16 mt-1" />
                  ) : (
                    <p className="text-2xl font-bold mt-1 text-foreground">
                      {value !== undefined ? (card.format ? card.format(value as number) : value) : 0}
                    </p>
                  )}
                </div>
                <div className={`p-3 rounded-xl bg-background/40 backdrop-blur-sm ${card.color} shadow-inner`}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function SubjectPerformanceChart({ data, isLoading }: { data?: SubjectPerformance[]; isLoading: boolean }) {
  const { t } = useTranslation()
  const maxScore = useMemo(() => {
    if (!data || data.length === 0) return 100
    return Math.max(...data.map((s) => s.average_score), 100)
  }, [data])

  return (
    <Card className="shadow-sm border-muted/50 overflow-hidden">
      <CardHeader className="bg-muted/10 border-b border-muted/20 pb-4">
        <CardTitle className="text-lg">{t('reports.subject_performance')}</CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-8 w-full" />)}
          </div>
        ) : !data || data.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">No subject data available.</p>
        ) : (
          <div className="space-y-5">
            {data.map((subject) => (
              <div key={subject.subject_id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{subject.subject_name}</span>
                  <span className="text-sm font-bold text-primary">
                    {subject.average_score}% <span className="font-normal text-muted-foreground text-xs ml-1">({subject.student_count} students)</span>
                  </span>
                </div>
                <div className="h-2 bg-muted/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary/60 to-primary rounded-full transition-all duration-1000 ease-out"
                    style={{ width: `${(subject.average_score / maxScore) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function BloomDistributionChart({ data, isLoading }: { data?: BloomDistribution[]; isLoading: boolean }) {
  const { t } = useTranslation()
  const maxCount = useMemo(() => {
    if (!data || data.length === 0) return 1
    return Math.max(...data.map((d) => d.count), 1)
  }, [data])

  return (
    <Card className="shadow-sm border-muted/50 overflow-hidden">
      <CardHeader className="bg-muted/10 border-b border-muted/20 pb-4">
        <CardTitle className="text-lg">{t('reports.bloom_distribution')}</CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-8 w-full" />)}
          </div>
        ) : !data || data.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">No data available.</p>
        ) : (
          <div className="space-y-5">
            {data.map((item) => (
              <div key={item.level}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium capitalize">{item.level}</span>
                  <span className="text-sm text-muted-foreground">{item.count} ({item.percentage}%)</span>
                </div>
                <div className="h-2.5 bg-muted/50 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ease-out ${bloomColors[item.level] || 'bg-primary'}`}
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ScoreTrendChart({ data, isLoading }: { data?: TrendData[]; isLoading: boolean }) {
  const { t } = useTranslation()

  const { points, svgHeight, svgWidth, maxScore, minScore } = useMemo(() => {
    if (!data || data.length === 0) return { points: [], svgHeight: 200, svgWidth: 600, maxScore: 100, minScore: 0 }
    const scores = data.map((d) => d.score)
    const mx = Math.max(...scores, 100)
    const mn = Math.min(...scores, 0)
    const padding = (mx - mn) * 0.1 || 10
    const h = 200
    const w = Math.max(600, data.length * 60)

    const pts = data.map((d, i) => {
      const x = (i / (data.length - 1 || 1)) * (w - 40) + 20
      const y = h - 20 - ((d.score - mn + padding) / (mx - mn + padding * 2)) * (h - 40)
      return { x, y, score: d.score, date: d.date, count: d.assessment_count }
    })
    return { points: pts, svgHeight: h, svgWidth: w, maxScore: mx, minScore: mn }
  }, [data])

  const pathD = useMemo(() => points.length < 2 ? '' : points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' '), [points])
  const areaD = useMemo(() => points.length < 2 ? '' : `${pathD} L ${points[points.length - 1].x} ${svgHeight - 20} L ${points[0].x} ${svgHeight - 20} Z`, [pathD, points, svgHeight])
  const bestPoint = useMemo(() => points.length === 0 ? null : points.reduce((a, b) => (a.score > b.score ? a : b)), [points])
  const worstPoint = useMemo(() => points.length === 0 ? null : points.reduce((a, b) => (a.score < b.score ? a : b)), [points])

  return (
    <Card className="shadow-sm border-muted/50 overflow-hidden">
      <CardHeader className="bg-muted/10 border-b border-muted/20">
        <CardTitle className="text-lg">{t('reports.score_trends')}</CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        {isLoading ? (
          <Skeleton className="h-[200px] w-full" />
        ) : !data || data.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">No trend data available.</p>
        ) : (
          <div className="space-y-6">
            <div className="relative overflow-x-auto rounded-lg border border-border bg-card">
              <svg width={svgWidth} height={svgHeight} className="min-w-full" viewBox={`0 0 ${svgWidth} ${svgHeight}`}>
                {[0, 25, 50, 75, 100].map((pct) => {
                  const y = svgHeight - 20 - (pct / 100) * (svgHeight - 40)
                  return (
                    <g key={pct}>
                      <line x1={20} y1={y} x2={svgWidth - 20} y2={y} stroke="currentColor" strokeOpacity={0.05} strokeDasharray="4 4" />
                      <text x={15} y={y + 4} textAnchor="end" className="text-[10px] fill-muted-foreground font-medium">{pct}%</text>
                    </g>
                  )
                })}
                {areaD && <path d={areaD} fill="url(#gradient)" opacity={0.3} />}
                {pathD && <path d={pathD} fill="none" stroke="hsl(var(--primary))" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />}
                {points.map((p, i) => (
                  <circle key={i} cx={p.x} cy={p.y} r={5} fill="hsl(var(--background))" stroke="hsl(var(--primary))" strokeWidth={2} className="cursor-pointer transition-all hover:r-[7px]">
                    <title>{`Date: ${p.date ? new Date(p.date).toLocaleDateString() : 'N/A'}\nScore: ${p.score}%\nAssessments: ${p.count}`}</title>
                  </circle>
                ))}
                <defs>
                  <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.6} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-muted/30">
              <div className="text-center">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Best Score</p>
                <p className="text-2xl font-bold text-emerald-500 mt-1">{bestPoint ? `${bestPoint.score}%` : '-'}</p>
              </div>
              <div className="text-center border-l border-border/50">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Worst Score</p>
                <p className="text-2xl font-bold text-rose-500 mt-1">{worstPoint ? `${worstPoint.score}%` : '-'}</p>
              </div>
              <div className="text-center border-l border-border/50">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Average</p>
                <p className="text-2xl font-bold text-foreground mt-1">
                  {data.length > 0 ? `${(data.reduce((s, d) => s + d.score, 0) / data.length).toFixed(1)}%` : '-'}
                </p>
              </div>
              <div className="text-center border-l border-border/50">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Trend</p>
                <p className="text-xl font-bold flex items-center justify-center gap-1 mt-1.5">
                  {data.length >= 2 ? (
                    data[data.length - 1].score > data[0].score ? (
                      <><ChevronUp className="h-6 w-6 text-emerald-500" /> <span className="text-emerald-500 text-sm">Up</span></>
                    ) : data[data.length - 1].score < data[0].score ? (
                      <><ChevronDown className="h-6 w-6 text-rose-500" /> <span className="text-rose-500 text-sm">Down</span></>
                    ) : (
                      <><Minus className="h-6 w-6 text-muted-foreground" /> <span className="text-muted-foreground text-sm">Stable</span></>
                    )
                  ) : '-'}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function GenerateReportDialog({ open, onOpenChange }: { open: boolean, onOpenChange: (v: boolean) => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [reportType, setReportType] = useState('')
  const generateMutation = useMutation({
    mutationFn: () => analyticsApi.generateReport(reportType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      onOpenChange(false)
      setReportType('')
    },
  })
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('reports.generate')}</DialogTitle>
          <DialogDescription>Select the type of report to generate.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="report-type">{t('reports.form.report_type')}</Label>
            <Select id="report-type" options={reportTypeOptions} placeholder="Select report type" value={reportType} onChange={(e) => setReportType(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <DialogClose><Button type="button" variant="outline">{t('common.cancel')}</Button></DialogClose>
          <Button onClick={() => generateMutation.mutate()} disabled={!reportType || generateMutation.isPending}>
            {generateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
            {t('reports.form.generate')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function OverviewTab() {
  const { t } = useTranslation()
  const { data: stats, isLoading: statsLoading, isError: statsError, refetch: refetchStats } = useQuery({ queryKey: ['reports-stats'], queryFn: () => analyticsApi.getDashboardStats() })
  const { data: subjectPerf, isLoading: subjectLoading } = useQuery({ queryKey: ['reports-subject-performance'], queryFn: () => analyticsApi.getSubjectPerformance() })
  const { data: bloomDist, isLoading: bloomLoading } = useQuery({ queryKey: ['reports-bloom-distribution'], queryFn: () => analyticsApi.getBloomDistribution() })
  const { data: scoreTrends, isLoading: trendsLoading } = useQuery({ queryKey: ['reports-score-trends'], queryFn: () => analyticsApi.getScoreTrends(30) })

  if (statsError) {
    return (
      <Card className="border-destructive/50 bg-destructive/5">
        <CardContent className="flex items-center gap-3 p-6">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <p className="text-sm text-destructive flex-1">{t('common.error')}</p>
          <Button variant="outline" size="sm" onClick={() => refetchStats()}>{t('common.retry')}</Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <StatCardsGrid data={stats} isLoading={statsLoading} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SubjectPerformanceChart data={subjectPerf} isLoading={subjectLoading} />
        <BloomDistributionChart data={bloomDist} isLoading={bloomLoading} />
      </div>
      <ScoreTrendChart data={scoreTrends} isLoading={trendsLoading} />
    </div>
  )
}

function ReportsTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [generateOpen, setGenerateOpen] = useState(false)
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['reports'], queryFn: () => analyticsApi.getReports() })
  const deleteMutation = useMutation({ mutationFn: (id: number) => analyticsApi.deleteReport(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reports'] }) })

  const handleDownload = async (report: Report) => {
    try {
      const blob = await analyticsApi.downloadReport(report.id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${report.id}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => window.URL.revokeObjectURL(url), 1000)
    } catch { console.error('Download failed') }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{data ? `${data.total} reports available` : ''}</p>
        <Button onClick={() => setGenerateOpen(true)} className="shadow-md shadow-primary/20"><Plus className="h-4 w-4 mr-2" />{t('reports.generate')}</Button>
      </div>

      <Card className="border-none shadow-md overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>
          ) : isError ? (
            <div className="flex items-center justify-between p-6 bg-destructive/5"><div className="flex items-center gap-2 text-sm text-destructive"><AlertCircle className="h-5 w-5" />{t('common.error')}</div><Button variant="outline" size="sm" onClick={() => refetch()}>{t('common.retry')}</Button></div>
          ) : !data || data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 px-4 bg-muted/10">
              <div className="p-6 bg-background rounded-full shadow-sm mb-4"><FileText className="h-10 w-10 text-muted-foreground/40" /></div>
              <p className="text-base text-muted-foreground text-center font-medium">{t('reports.empty')}</p>
            </div>
          ) : (
            <Table>
              <TableHeader className="bg-muted/30">
                <TableRow>
                  <TableHead className="w-16">ID</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>School</TableHead>
                  <TableHead>Generated</TableHead>
                  <TableHead className="w-32">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((report) => (
                  <TableRow key={report.id} className="hover:bg-muted/10 transition-colors">
                    <TableCell className="text-xs text-muted-foreground font-mono">#{report.id}</TableCell>
                    <TableCell><span className="text-sm font-medium text-foreground">{report.title}</span></TableCell>
                    <TableCell><Badge variant="outline" className="capitalize bg-background text-primary border-primary/20">{report.report_type.replace(/_/g, ' ')}</Badge></TableCell>
                    <TableCell className="text-sm text-muted-foreground">School #{report.school_id}</TableCell>
                    <TableCell className="text-xs font-medium text-muted-foreground">
                      {report.generated_at ? new Date(report.generated_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" onClick={() => handleDownload(report)} title={t('reports.download')} className="text-blue-500 hover:text-blue-600 hover:bg-blue-500/10"><Download className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" onClick={() => deleteMutation.mutate(report.id)} disabled={deleteMutation.isPending} title={t('reports.delete')} className="text-rose-500 hover:text-rose-600 hover:bg-rose-500/10"><Trash2 className="h-4 w-4" /></Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <GenerateReportDialog open={generateOpen} onOpenChange={setGenerateOpen} />
    </div>
  )
}

function TrendsTab() {
  const { t } = useTranslation()
  const [days, setDays] = useState(30)
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['reports-score-trends', days], queryFn: () => analyticsApi.getScoreTrends(days) })

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center gap-2 p-1 bg-muted/30 rounded-lg w-fit">
        {[7, 30, 90].map((d) => (
          <Button key={d} variant={days === d ? 'default' : 'ghost'} size="sm" onClick={() => setDays(d)} className={`px-4 ${days === d ? 'shadow-sm' : 'text-muted-foreground'}`}>
            {d} days
          </Button>
        ))}
      </div>

      {isError ? (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive flex-1">{t('common.error')}</p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>{t('common.retry')}</Button>
          </CardContent>
        </Card>
      ) : (
        <ScoreTrendChart data={data} isLoading={isLoading} />
      )}
    </div>
  )
}

export default function ReportsPage() {
  const { t } = useTranslation()
  const [tab, setTab] = useState('overview')

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">{t('reports.title')}</h1>
        <p className="text-muted-foreground text-sm">{t('nav.reports')} and detailed analytics</p>
      </div>

      <Tabs value={tab} onValueChange={setTab} className="w-full">
        <TabsList className="bg-muted/50 p-1 w-full sm:w-auto grid grid-cols-3 sm:inline-flex mb-2">
          <TabsTrigger value="overview">{t('reports.tabs.overview')}</TabsTrigger>
          <TabsTrigger value="reports">{t('reports.tabs.reports')}</TabsTrigger>
          <TabsTrigger value="trends">{t('reports.tabs.trends')}</TabsTrigger>
        </TabsList>
        <div className="mt-4">
          <TabsContent value="overview" className="m-0 focus-visible:outline-none"><OverviewTab /></TabsContent>
          <TabsContent value="reports" className="m-0 focus-visible:outline-none"><ReportsTab /></TabsContent>
          <TabsContent value="trends" className="m-0 focus-visible:outline-none"><TrendsTab /></TabsContent>
        </div>
      </Tabs>
    </div>
  )
}
