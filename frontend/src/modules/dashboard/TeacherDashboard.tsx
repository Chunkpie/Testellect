import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import * as analyticsApi from '@/api/analytics'
import type { DashboardStats } from '@/api/analytics'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { BookOpen, Brain, FileText, School, Users, BarChart3, AlertCircle, ArrowUpRight } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts'
import { Link } from 'react-router-dom'

type StatKeys = 'total_students' | 'total_teachers' | 'total_assessments' | 'total_questions' | 'average_score' | 'completion_rate'

const statCards: { key: StatKeys; icon: any; label: string; color: string; gradient: string }[] = [
  { key: 'total_students', icon: Users, label: 'Students', color: 'text-cyan-600 dark:text-cyan-400', gradient: 'from-cyan-500/20 to-blue-500/5' },
  { key: 'total_teachers', icon: School, label: 'Teachers', color: 'text-rose-600 dark:text-rose-400', gradient: 'from-rose-500/20 to-orange-500/5' },
  { key: 'total_assessments', icon: BarChart3, label: 'Assessments', color: 'text-amber-600 dark:text-amber-400', gradient: 'from-amber-500/20 to-yellow-500/5' },
  { key: 'total_questions', icon: Brain, label: 'Questions Bank', color: 'text-purple-600 dark:text-purple-400', gradient: 'from-purple-500/20 to-pink-500/5' },
  { key: 'average_score', icon: FileText, label: 'Avg Score', color: 'text-green-600 dark:text-green-400', gradient: 'from-green-500/20 to-emerald-500/5' },
  { key: 'completion_rate', icon: BookOpen, label: 'Completion %', color: 'text-blue-600 dark:text-blue-400', gradient: 'from-blue-500/20 to-indigo-500/5' },
]

export default function TeacherDashboard() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)

  const { data: stats, isLoading: statsLoading, isError: statsError, refetch: refetchStats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => analyticsApi.getDashboardStats(),
  })

  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: ['dashboard-trends'],
    queryFn: () => analyticsApi.getScoreTrends(30),
  })

  const { data: subjects, isLoading: subjectsLoading } = useQuery({
    queryKey: ['dashboard-subjects'],
    queryFn: () => analyticsApi.getSubjectPerformance(),
  })

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
            {t('dashboard.welcome')}, {user?.name}
          </h1>
          <p className="text-muted-foreground mt-2 text-lg">
            Here's an overview of your institution's performance.
          </p>
        </div>
        <div className="flex gap-3">
          <Button asChild className="shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all">
            <Link to="/papers/create">
              Create Assessment <ArrowUpRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>

      {statsError && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive flex-1">{t('common.error')}</p>
            <Button variant="outline" size="sm" onClick={() => refetchStats()}>
              {t('common.retry')}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {statCards.map((card) => {
          const Icon = card.icon
          const value = stats?.[card.key as keyof DashboardStats]

          return (
            <Card key={card.key} className={`overflow-hidden border-none shadow-md bg-gradient-to-br ${card.gradient} hover:shadow-lg transition-all duration-300 hover:-translate-y-1`}>
              <CardContent className="p-6">
                <div className="flex justify-between items-start">
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-muted-foreground/80 uppercase tracking-wider">{card.label}</p>
                    {statsLoading ? (
                      <Skeleton className="h-10 w-24" />
                    ) : (
                      <div className="flex items-baseline gap-2">
                        <p className="text-4xl font-bold text-foreground tracking-tight">
                          {value ?? 0}{(card.key === 'average_score' || card.key === 'completion_rate') && '%'}
                        </p>
                      </div>
                    )}
                  </div>
                  <div className={`p-4 rounded-2xl bg-background/50 backdrop-blur-sm ${card.color} shadow-inner`}>
                    <Icon className="h-6 w-6" />
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trend Chart */}
        <Card className="shadow-sm border-muted/50 overflow-hidden">
          <CardHeader className="bg-muted/10 border-b border-muted/20">
            <CardTitle>Performance Trends (Last 30 Days)</CardTitle>
            <CardDescription>Average student scores over recent assessments</CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <div className="h-[300px] w-full">
              {trendsLoading ? (
                <div className="h-full w-full flex items-center justify-center">
                  <Skeleton className="h-[250px] w-full" />
                </div>
              ) : trends && trends.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted))" />
                    <XAxis 
                      dataKey="date" 
                      tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})}
                      axisLine={false}
                      tickLine={false}
                      tick={{fill: 'hsl(var(--muted-foreground))', fontSize: 12}}
                      dy={10}
                    />
                    <YAxis 
                      axisLine={false}
                      tickLine={false}
                      tick={{fill: 'hsl(var(--muted-foreground))', fontSize: 12}}
                    />
                    <Tooltip 
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      labelFormatter={(val) => new Date(val).toLocaleDateString()}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="score" 
                      stroke="hsl(var(--primary))" 
                      strokeWidth={3}
                      fillOpacity={1} 
                      fill="url(#colorScore)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground flex-col gap-2">
                  <BarChart3 className="h-10 w-10 opacity-20" />
                  <p>No assessment data available for the selected period.</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Subject Performance */}
        <Card className="shadow-sm border-muted/50 overflow-hidden">
          <CardHeader className="bg-muted/10 border-b border-muted/20">
            <CardTitle>Subject Performance</CardTitle>
            <CardDescription>Average scores across different subjects</CardDescription>
          </CardHeader>
          <CardContent className="p-6">
            <div className="h-[300px] w-full">
              {subjectsLoading ? (
                <div className="h-full w-full flex items-center justify-center">
                  <Skeleton className="h-[250px] w-full" />
                </div>
              ) : subjects && subjects.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={subjects} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--muted))" />
                    <XAxis type="number" domain={[0, 100]} hide />
                    <YAxis 
                      dataKey="subject_name" 
                      type="category" 
                      axisLine={false}
                      tickLine={false}
                      tick={{fill: 'hsl(var(--foreground))', fontSize: 13, fontWeight: 500}}
                      width={100}
                    />
                    <Tooltip 
                      cursor={{fill: 'hsl(var(--muted)/0.5)'}}
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Bar dataKey="average_score" radius={[0, 4, 4, 0]} barSize={24}>
                      {subjects.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={`hsl(var(--primary) / ${0.6 + (entry.average_score / 200)})`} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground flex-col gap-2">
                  <BookOpen className="h-10 w-10 opacity-20" />
                  <p>No subject performance data available.</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

    </div>
  )
}
