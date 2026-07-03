import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import * as schoolsApi from '@/api/schools'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from '@/components/ui/form'
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import {
  Building2,
  Users,
  Database,
  Loader2,
  AlertCircle,
  Plus,
  Save,
  UserPlus,
  CheckCircle2,
} from 'lucide-react'

const schoolProfileSchema = z.object({
  name: z.string().min(1, 'School name is required'),
  address: z.string().optional(),
  medium: z.string().optional(),
  board: z.string().optional(),
  udise_code: z.string().optional(),
})

type SchoolProfileForm = z.infer<typeof schoolProfileSchema>

const createUserSchema = z.object({
  email: z.string().email('Invalid email address'),
  name: z.string().min(1, 'Name is required'),
  role: z.enum(['admin', 'teacher', 'principal', 'deo']),
})

type CreateUserForm = z.infer<typeof createUserSchema>

const roleOptions = [
  { value: 'admin', label: 'Admin' },
  { value: 'teacher', label: 'Teacher' },
  { value: 'principal', label: 'Principal' },
  { value: 'deo', label: 'DEO' },
]

const mediumOptions = [
  { value: 'gujarati', label: 'Gujarati' },
  { value: 'hindi', label: 'Hindi' },
  { value: 'english', label: 'English' },
]

const boardOptions = [
  { value: 'gseb', label: 'GSEB' },
  { value: 'cbse', label: 'CBSE' },
  { value: 'icse', label: 'ICSE' },
]

function ProfileTab({ schoolId }: { schoolId: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)

  const { data: school, isLoading, isError } = useQuery({
    queryKey: ['school', schoolId],
    queryFn: () => schoolsApi.getSchool(schoolId),
    enabled: !!schoolId,
  })

  const form = useForm<SchoolProfileForm>({
    resolver: zodResolver(schoolProfileSchema),
    values: {
      name: school?.name ?? '',
      address: school?.address ?? '',
      medium: school?.medium ?? '',
      board: school?.board ?? '',
      udise_code: school?.udise_code ?? '',
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: SchoolProfileForm) => schoolsApi.updateSchool(schoolId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['school', schoolId] })
      setEditing(false)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (isError) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="flex items-center gap-3 p-6">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <p className="text-sm text-destructive">{t('common.error')}</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              {t('settings.schoolProfile')}
            </CardTitle>
            <CardDescription>{t('settings.schoolProfileDesc')}</CardDescription>
          </div>
          {!editing && (
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
              {t('common.edit')}
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit((data) => updateMutation.mutate(data))} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('school.name')}</FormLabel>
                      <FormControl>
                        <Input {...field} disabled={!editing} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="udise_code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('school.udiseCode')}</FormLabel>
                      <FormControl>
                        <Input {...field} disabled={!editing} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="medium"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('school.medium')}</FormLabel>
                      <FormControl>
                        <select
                          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                          {...field}
                          disabled={!editing}
                        >
                          <option value="">Select medium</option>
                          {mediumOptions.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="board"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('school.board')}</FormLabel>
                      <FormControl>
                        <select
                          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                          {...field}
                          disabled={!editing}
                        >
                          <option value="">Select board</option>
                          {boardOptions.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={form.control}
                name="address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('school.address')}</FormLabel>
                    <FormControl>
                      <Input {...field} disabled={!editing} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {editing && (
                <div className="flex gap-2">
                  <Button type="submit" disabled={updateMutation.isPending}>
                    {updateMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                    {t('common.save')}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => {
                    form.reset()
                    setEditing(false)
                  }}>
                    {t('common.cancel')}
                  </Button>
                </div>
              )}
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}

function UsersTab({ schoolId }: { schoolId: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['school-users', schoolId],
    queryFn: () => schoolsApi.getSchoolUsers({ school_id: schoolId, limit: 50 }),
    enabled: !!schoolId,
  })

  const userForm = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { email: '', name: '', role: 'teacher' },
  })

  const createUserMutation = useMutation({
    mutationFn: (data: CreateUserForm) =>
      schoolsApi.createUser({ ...data, school_id: schoolId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['school-users', schoolId] })
      setCreateOpen(false)
      userForm.reset()
    },
  })

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Users className="h-5 w-5" />
              {t('settings.userManagement')}
            </CardTitle>
            <CardDescription>{t('settings.userManagementDesc')}</CardDescription>
          </div>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger>
              <Button size="sm">
                <UserPlus className="h-4 w-4" />
                {t('settings.addUser')}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t('settings.createUser')}</DialogTitle>
                <DialogDescription>{t('settings.createUserDesc')}</DialogDescription>
              </DialogHeader>
              <Form {...userForm}>
                <form
                  onSubmit={userForm.handleSubmit((data) => createUserMutation.mutate(data))}
                  className="space-y-4"
                >
                  <FormField
                    control={userForm.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('user.name')}</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="John Doe" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={userForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('user.email')}</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="john@school.edu" type="email" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={userForm.control}
                    name="role"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('user.role')}</FormLabel>
                        <FormControl>
                          <select
                            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                            {...field}
                          >
                            {roleOptions.map((o) => (
                              <option key={o.value} value={o.value}>{o.label}</option>
                            ))}
                          </select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <DialogFooter>
                    <DialogClose>
                      <Button type="button" variant="outline">{t('common.cancel')}</Button>
                    </DialogClose>
                    <Button type="submit" disabled={createUserMutation.isPending}>
                      {createUserMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Plus className="h-4 w-4" />
                      )}
                      {t('common.create')}
                    </Button>
                  </DialogFooter>
                </form>
              </Form>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="divide-y">
              {usersData?.items?.length === 0 ? (
                <p className="text-sm text-muted-foreground p-6 text-center">{t('common.noData')}</p>
              ) : (
                usersData?.items?.map((user) => (
                  <div key={user.id} className="flex items-center justify-between px-6 py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted text-xs font-medium">
                        {user.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium">{user.name}</p>
                        <p className="text-xs text-muted-foreground">{user.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={user.is_active ? 'success' : 'secondary'}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                      <Badge variant="outline">{user.role}</Badge>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function BackupsTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: backups, isLoading, isError } = useQuery({
    queryKey: ['backups'],
    queryFn: () => schoolsApi.listBackups(),
  })

  const backupMutation = useMutation({
    mutationFn: () => schoolsApi.triggerBackup(),
    onSuccess: () => {
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['backups'] })
      }, 2000)
    },
  })

  return (
    <div className="space-y-6">
      <Card className="border-destructive/20">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2 text-destructive">
            <Database className="h-5 w-5" />
            {t('settings.dangerZone')}
          </CardTitle>
          <CardDescription>{t('settings.backupDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-destructive">{t('settings.backupAction')}</p>
                <p className="text-xs text-muted-foreground mt-1">{t('settings.backupWarning')}</p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => backupMutation.mutate()}
                disabled={backupMutation.isPending}
              >
                {backupMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Database className="h-4 w-4" />
                )}
                {t('settings.triggerBackup')}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{t('settings.backupHistory')}</CardTitle>
          <CardDescription>{t('settings.backupHistoryDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : isError ? (
            <div className="flex items-center gap-2 p-6 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              {t('common.error')}
            </div>
          ) : backups && backups.length > 0 ? (
            <div className="divide-y">
              {backups.map((backup) => (
                <div key={backup.id} className="flex items-center justify-between px-6 py-3">
                  <div className="flex items-center gap-3">
                    <Database className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">{backup.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(backup.created_at).toLocaleString()} &middot; {(backup.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <Badge variant="success">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Completed
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground p-6 text-center">{t('common.noData')}</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default function SettingsPage() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const [activeTab, setActiveTab] = useState('profile')

  const isAdmin = user?.role === 'admin'
  const schoolId = user?.school_id ?? ''

  const tabs = [
    { value: 'profile', label: t('settings.schoolProfile'), icon: Building2, show: true },
    { value: 'users', label: t('settings.userManagement'), icon: Users, show: isAdmin },
    { value: 'backups', label: t('settings.backups'), icon: Database, show: isAdmin },
  ].filter((t) => t.show)

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">{t('nav.settings')}</h1>
        <p className="text-muted-foreground text-sm mt-1">{t('settings.description')}</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="bg-muted/50 p-1 w-full sm:w-auto grid grid-cols-1 sm:inline-flex mb-2">
          {tabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value} className="flex items-center gap-2">
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
        <div className="mt-4">
          <TabsContent value="profile" className="m-0 focus-visible:outline-none">
            <ProfileTab schoolId={schoolId} />
          </TabsContent>
          <TabsContent value="users" className="m-0 focus-visible:outline-none">
            <UsersTab schoolId={schoolId} />
          </TabsContent>
          <TabsContent value="backups" className="m-0 focus-visible:outline-none">
            <BackupsTab />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}
