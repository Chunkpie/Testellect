import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useUIStore } from '@/stores/uiStore'
import { cn } from '@/lib/utils'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function AppShell() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed)
  const [mobileOpen, setMobileOpen] = useState(false)

  const sidebarWidth = collapsed ? 'w-16' : 'w-60'

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar */}
      <div className={cn('hidden lg:flex flex-col border-r border-sidebar-border bg-sidebar-background transition-all duration-300 shrink-0', sidebarWidth)}>
        <Sidebar />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/50" onClick={() => setMobileOpen(false)} />
      )}

      {/* Mobile sidebar drawer */}
      <div className={cn(
        'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-sidebar-border bg-sidebar-background transition-transform duration-300 lg:hidden',
        sidebarWidth,
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <Sidebar />
      </div>

      <div className="flex flex-1 flex-col min-w-0">
        <Topbar onMenuClick={() => setMobileOpen(true)} />
        <main className="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
