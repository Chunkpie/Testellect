import { useAuthStore } from '@/stores/authStore'
import TeacherDashboard from './TeacherDashboard'
import PrincipalDashboard from './PrincipalDashboard'
import DEODashboard from './DEODashboard'

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const role = user?.role || 'teacher'

  switch (role) {
    case 'deo':
      return <DEODashboard />
    case 'principal':
      return <PrincipalDashboard />
    case 'teacher':
    case 'admin':
    default:
      return <TeacherDashboard />
  }
}
