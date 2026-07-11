import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  BookOpen,
  TreePine,
  Brain,
  FileEdit,
  FileText,
  Scan,
  BarChart3,
  Settings,
  ChevronLeft,
  Users,
  Image,
} from 'lucide-react'

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'nav.dashboard', roles: ['admin', 'teacher', 'principal', 'deo'] },
  { path: '/books', icon: BookOpen, label: 'nav.books', roles: ['admin', 'teacher'] },
  { path: '/knowledge-base', icon: TreePine, label: 'nav.knowledgeBase', roles: ['admin', 'teacher'] },
  { path: '/questions', icon: Brain, label: 'Question Bank', roles: ['admin', 'teacher'] },
  { path: '/image-bank', icon: Image, label: 'Image Bank', roles: ['admin', 'teacher'] },
  { path: '/blueprints', icon: FileEdit, label: 'nav.blueprints', roles: ['admin', 'teacher'] },
  { path: '/papers', icon: FileText, label: 'nav.papers', roles: ['admin', 'teacher'] },
  { path: '/omr', icon: Scan, label: 'nav.omr', roles: ['admin', 'teacher'] },
  { path: '/reports', icon: BarChart3, label: 'nav.reports', roles: ['admin', 'teacher', 'principal', 'deo'] },
  { path: '/analytics/teacher', icon: BarChart3, label: 'nav.analytics', roles: ['admin', 'teacher', 'principal', 'deo'] },
  { path: '/students', icon: Users, label: 'nav.students', roles: ['admin', 'teacher', 'principal', 'deo'] },
  { path: '/settings/profile', icon: Settings, label: 'nav.settings', roles: ['admin'] },
]

export default function Sidebar() {
  const { pathname } = useLocation()
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const collapsed = useUIStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)

  const filteredItems = navItems.filter(
    (item) => user?.role && item.roles.includes(user.role)
  )

  return (
    <aside className="flex h-full flex-col">
      <div className={cn('flex h-14 items-center border-b border-sidebar-border px-4', collapsed && 'justify-center')}>
        {!collapsed && (
          <div className="flex-1">
            <h1 className="text-sm font-bold text-sidebar-foreground">Testellect</h1>
            <p className="text-[10px] text-sidebar-foreground/60">Assessment Platform</p>
          </div>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); toggleSidebar() }}
          className="text-sidebar-foreground hover:text-sidebar-accent-foreground"
        >
          <ChevronLeft className={cn('h-4 w-4 transition-transform', collapsed && 'rotate-180')} />
        </button>
      </div>

      <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
        {filteredItems.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-4">No navigation available</p>
        )}
        {filteredItems.map((item) => {
          const Icon = item.icon
          const active =
            pathname === item.path || pathname.startsWith(item.path + '/')

          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                collapsed && 'justify-center px-2',
                active
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                  : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span>{t(item.label)}</span>}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
