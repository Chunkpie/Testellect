import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import AppShell from '@/components/layout/AppShell'
import { Loader2 } from 'lucide-react'

const LoginPage = lazy(() => import('@/modules/auth/LoginPage'))
const DashboardPage = lazy(() => import('@/modules/dashboard/DashboardPage'))
const BooksPage = lazy(() => import('@/modules/books/BooksPage'))
const KnowledgeBasePage = lazy(() => import('@/modules/knowledge-base/KnowledgeBasePage'))
const BlueprintsPage = lazy(() => import('@/modules/blueprints/BlueprintsPage'))
const PapersPage = lazy(() => import('@/modules/papers/PapersPage'))
const OMRPage = lazy(() => import('@/modules/omr/OMRPage'))
const ReportsPage = lazy(() => import('@/modules/reports/ReportsPage'))
const AnalyticsPage = lazy(() => import('@/modules/analytics/AnalyticsPage'))
const SettingsPage = lazy(() => import('@/modules/settings/SettingsPage'))
const StudentsPage = lazy(() => import('@/modules/students/StudentsPage'))
const QuestionsPage = lazy(() => import('@/modules/questions/QuestionsPage'))
const ImageBankPage = lazy(() => import('@/modules/image-bank/ImageBankPage'))
const AdminLoginPage = lazy(() => import('@/modules/auth/AdminLoginPage'))

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-[50vh]">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  )
}

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingFallback />}>{children}</Suspense>
}

function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

function PublicRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}

export default function App() {
  return (
    <SuspenseWrapper>
      <Routes>
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<SuspenseWrapper><DashboardPage /></SuspenseWrapper>} />
            <Route path="/books" element={<SuspenseWrapper><BooksPage /></SuspenseWrapper>} />
            <Route path="/books/:id" element={<SuspenseWrapper><BooksPage /></SuspenseWrapper>} />
            <Route path="/knowledge-base" element={<SuspenseWrapper><KnowledgeBasePage /></SuspenseWrapper>} />
            <Route path="/blueprints" element={<SuspenseWrapper><BlueprintsPage /></SuspenseWrapper>} />
            <Route path="/blueprints/:id" element={<SuspenseWrapper><BlueprintsPage /></SuspenseWrapper>} />
            <Route path="/papers" element={<SuspenseWrapper><PapersPage /></SuspenseWrapper>} />
            <Route path="/papers/:id" element={<SuspenseWrapper><PapersPage /></SuspenseWrapper>} />
            <Route path="/omr" element={<SuspenseWrapper><OMRPage /></SuspenseWrapper>} />
            <Route path="/reports" element={<SuspenseWrapper><ReportsPage /></SuspenseWrapper>} />
            <Route path="/analytics/:view" element={<SuspenseWrapper><AnalyticsPage /></SuspenseWrapper>} />
            <Route path="/settings/profile" element={<SuspenseWrapper><SettingsPage /></SuspenseWrapper>} />
            <Route path="/settings/users" element={<SuspenseWrapper><SettingsPage /></SuspenseWrapper>} />
            <Route path="/settings/backups" element={<SuspenseWrapper><SettingsPage /></SuspenseWrapper>} />
            <Route path="/students" element={<SuspenseWrapper><StudentsPage /></SuspenseWrapper>} />
            <Route path="/questions" element={<SuspenseWrapper><QuestionsPage /></SuspenseWrapper>} />
            <Route path="/image-bank" element={<SuspenseWrapper><ImageBankPage /></SuspenseWrapper>} />
          </Route>
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </SuspenseWrapper>
  )
}
