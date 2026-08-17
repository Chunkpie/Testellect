import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import * as analyticsApi from '@/api/analytics'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Loader2, Users, School, TrendingUp, BookOpen } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'
import { QRSyncModal } from './QRSyncModal'
import { QrCode, Download } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'

export default function AnalyticsPage() {
  const { t } = useTranslation()
  const { view } = useParams()
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const [qrOpen, setQrOpen] = useState(false)

  const tabViews = [
    { value: 'teacher', label: 'Teacher', roles: ['admin', 'teacher'] },
    { value: 'school', label: 'School', roles: ['admin', 'principal'] },
    { value: 'district', label: 'District', roles: ['admin', 'deo'] },
  ]

  const allowedViews = tabViews.filter(v => user?.role && v.roles.includes(user.role))
  const activeView = view && allowedViews.some(v => v.value === view) ? view : allowedViews[0]?.value

  const { data: studentData, isLoading: studentLoading } = useQuery({
    queryKey: ['analytics', 'student', activeView],
    queryFn: () => analyticsApi.getStudentAnalytics(user?.id?.toString() || '1'),
    enabled: activeView === 'student',
  })

  const { data: schoolData, isLoading: schoolLoading } = useQuery({
    queryKey: ['analytics', 'school', activeView],
    queryFn: () => analyticsApi.getSchoolAnalytics(user?.school_id?.toString() || '1'),
    enabled: activeView === 'school',
  })

  const { data: districtData, isLoading: districtLoading } = useQuery({
    queryKey: ['analytics', 'district', activeView],
    queryFn: () => analyticsApi.getDistrictAnalytics('district_name_here'), // Normally from user profile
    enabled: activeView === 'district',
  })
  
  const { data: trends } = useQuery({
    queryKey: ['analytics-trends', activeView],
    queryFn: () => analyticsApi.getScoreTrends(30),
  })

  const { data: subjects } = useQuery({
    queryKey: ['analytics-subjects', activeView],
    queryFn: () => analyticsApi.getSubjectPerformance(),
  })

  const { data: competencies } = useQuery({
    queryKey: ['analytics-competencies', activeView],
    queryFn: () => analyticsApi.getCompetencies(),
  })

  const isLoading = studentLoading || schoolLoading || districtLoading

  if (!user) return null

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">{activeView ? activeView.charAt(0).toUpperCase() + activeView.slice(1) : ''} Analytics</h1>
        <p className="text-muted-foreground text-sm mt-1">Detailed performance insights and analytics</p>
      </div>

      <div className="flex items-center justify-between">
        <Tabs value={activeView} onValueChange={(v) => navigate(`/analytics/${v}`)}>
          <TabsList className="bg-muted/50 p-1">
            {allowedViews.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value} className="capitalize">
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <Button variant="outline" className="gap-2" onClick={() => setQrOpen(true)}>
          <QrCode className="w-4 h-4" />
          Offline Sync
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-none shadow-md bg-gradient-to-br from-blue-500/10 to-transparent">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
              <Users className="h-5 w-5" />
              <CardTitle className="text-sm font-semibold uppercase tracking-wider">Students Tracked</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold">{isLoading ? '-' : (studentData?.total_students ?? schoolData?.total_students ?? districtData?.total_students ?? 0)}</p>
          </CardContent>
        </Card>

        <Card className="border-none shadow-md bg-gradient-to-br from-green-500/10 to-transparent">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <School className="h-5 w-5" />
              <CardTitle className="text-sm font-semibold uppercase tracking-wider">Total Assessments</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold">{isLoading ? '-' : (studentData?.total_assessments ?? schoolData?.total_assessments ?? districtData?.total_assessments ?? 0)}</p>
          </CardContent>
        </Card>

        <Card className="border-none shadow-md bg-gradient-to-br from-amber-500/10 to-transparent">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
              <TrendingUp className="h-5 w-5" />
              <CardTitle className="text-sm font-semibold uppercase tracking-wider">Avg Score</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold">{isLoading ? '-' : `${(studentData?.average_score ?? schoolData?.average_score ?? districtData?.average_score ?? 0)}%`}</p>
          </CardContent>
        </Card>
      </div>

      {isLoading && (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      )}

      {!isLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <Card className="shadow-sm border-muted/50 overflow-hidden">
            <CardHeader className="bg-muted/10 border-b border-muted/20">
              <CardTitle>Score Progression</CardTitle>
              <CardDescription>Average scores over time</CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="h-[300px] w-full">
                {trends && trends.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorScore2" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted))" />
                      <XAxis dataKey="date" tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})} axisLine={false} tickLine={false} tick={{fill: 'hsl(var(--muted-foreground))', fontSize: 12}} dy={10} />
                      <YAxis axisLine={false} tickLine={false} tick={{fill: 'hsl(var(--muted-foreground))', fontSize: 12}} />
                      <RechartsTooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} labelFormatter={(val) => new Date(val).toLocaleDateString()} />
                      <Area type="monotone" dataKey="score" stroke="hsl(var(--primary))" strokeWidth={3} fillOpacity={1} fill="url(#colorScore2)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">No trend data</div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-muted/50 overflow-hidden">
            <CardHeader className="bg-muted/10 border-b border-muted/20">
              <CardTitle>Subject Performance Breakdown</CardTitle>
              <CardDescription>Comparison across different subjects</CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="h-[300px] w-full">
                {subjects && subjects.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={subjects} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--muted))" />
                      <XAxis type="number" domain={[0, 100]} hide />
                      <YAxis dataKey="subject_name" type="category" axisLine={false} tickLine={false} tick={{fill: 'hsl(var(--foreground))', fontSize: 13, fontWeight: 500}} width={100} />
                      <RechartsTooltip cursor={{fill: 'hsl(var(--muted)/0.5)'}} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                      <Bar dataKey="average_score" radius={[0, 4, 4, 0]} barSize={24}>
                        {subjects.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={`hsl(var(--primary) / ${0.6 + (entry.average_score / 200)})`} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">No subject data</div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Competency Radar Chart */}
      {!isLoading && competencies && (
        <div className="grid grid-cols-1 gap-6 mt-6">
          <Card className="shadow-sm border-muted/50 overflow-hidden">
            <CardHeader className="bg-muted/10 border-b border-muted/20">
              <CardTitle>Competency Analytics</CardTitle>
              <CardDescription>Mastery across cognitive levels (Bloom's Taxonomy)</CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="h-[400px] w-full flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="70%" data={competencies}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: 'hsl(var(--foreground))', fontSize: 13, fontWeight: 500 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} />
                    <Radar name="Score %" dataKey="A" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.4} />
                    <RechartsTooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <QRSyncModal 
        open={qrOpen} 
        onOpenChange={setQrOpen} 
        data={studentData || schoolData || districtData} 
      />
    </div>
  )
}
