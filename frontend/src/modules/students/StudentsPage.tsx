import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import * as studentsApi from '@/api/students'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
import { Badge } from '@/components/ui/badge'
import {
  Users,
  Plus,
  Search,
  Upload,
  Loader2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  FileUp,
  UserPlus,
  Edit2,
} from 'lucide-react'

const createStudentSchema = z.object({
  name: z.string().min(1, 'Student name is required'),
  roll_number: z.string().optional(),
  gender: z.enum(['male', 'female', 'other']).optional(),
  class_id: z.string().optional(),
})

type CreateStudentForm = z.infer<typeof createStudentSchema>

const genderOptions = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
]

const PAGE_SIZE = 20

function CreateStudentDialog({
  open,
  onOpenChange,
  schoolId,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  schoolId: string
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const form = useForm<CreateStudentForm>({
    resolver: zodResolver(createStudentSchema),
    defaultValues: { name: '', roll_number: '', gender: undefined, class_id: '' },
  })

  const { data: classesData } = useQuery({
    queryKey: ['classes', schoolId],
    queryFn: () => studentsApi.getClasses({ school_id: schoolId, limit: 100 }),
    enabled: !!schoolId,
  })

  const createMutation = useMutation({
    mutationFn: (data: CreateStudentForm) =>
      studentsApi.createStudent({ ...data, school_id: schoolId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] })
      onOpenChange(false)
      form.reset()
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('students.addStudent')}</DialogTitle>
          <DialogDescription>{t('students.addStudentDesc')}</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit((data) => createMutation.mutate(data))} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('students.name')}</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="Enter student name" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="roll_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('students.rollNumber')}</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="Roll number" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="gender"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('students.gender')}</FormLabel>
                    <FormControl>
                      <select
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        {...field}
                      >
                        <option value="">Select gender</option>
                        {genderOptions.map((o) => (
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
              name="class_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('students.class')}</FormLabel>
                  <FormControl>
                    <select
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      {...field}
                    >
                      <option value="">Select class</option>
                      {classesData?.items?.map((cls) => (
                        <option key={cls.id} value={cls.id}>{cls.name} (Grade {cls.grade})</option>
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
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <UserPlus className="h-4 w-4" />
                )}
                {t('common.create')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function BulkImportDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<{ imported: number; errors?: string[] } | null>(null)

  const importMutation = useMutation({
    mutationFn: (formData: FormData) => studentsApi.bulkImportStudents(formData),
    onSuccess: (data) => {
      setResult(data)
      queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0])
      setResult(null)
    }
  }

  const handleUpload = () => {
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    importMutation.mutate(formData)
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) { setFile(null); setResult(null) } }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('students.bulkImport')}</DialogTitle>
          <DialogDescription>{t('students.bulkImportDesc')}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {result ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-green-500">
                <AlertCircle className="h-4 w-4" />
                Successfully imported {result.imported} students
              </div>
              {result.errors && result.errors.length > 0 && (
                <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3">
                  <p className="text-xs font-medium text-destructive mb-1">Errors:</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {result.errors.map((err, i) => (
                      <li key={i} className="text-xs text-destructive/80">{err}</li>
                    ))}
                  </ul>
                </div>
              )}
              <DialogClose>
                <Button className="w-full">{t('common.done')}</Button>
              </DialogClose>
            </div>
          ) : (
            <>
              <div className="rounded-lg border-2 border-dashed p-8 text-center">
                {file ? (
                  <div className="space-y-2">
                    <FileUp className="h-8 w-8 mx-auto text-primary" />
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <label className="cursor-pointer space-y-2">
                    <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">{t('students.clickToUpload')}</p>
                    <input type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
                  </label>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{t('students.csvFormat')}</p>
              <DialogFooter>
                <DialogClose>
                  <Button type="button" variant="outline">{t('common.cancel')}</Button>
                </DialogClose>
                <Button onClick={handleUpload} disabled={!file || importMutation.isPending}>
                  {importMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  {t('common.upload')}
                </Button>
              </DialogFooter>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function EditStudentDialog({
  open,
  onOpenChange,
  student,
  schoolId,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  student: studentsApi.Student | null
  schoolId: string
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const form = useForm<CreateStudentForm>({
    resolver: zodResolver(createStudentSchema),
    defaultValues: { 
      name: student?.name || '', 
      roll_number: student?.roll_number || '', 
      gender: (student?.gender as any) || undefined, 
      class_id: student?.class_id ? String(student.class_id) : '' 
    },
  })

  // Reset form when student changes
  useEffect(() => {
    if (student) {
      form.reset({
        name: student.name,
        roll_number: student.roll_number || '',
        gender: (student.gender as any) || undefined,
        class_id: student.class_id ? String(student.class_id) : '',
      })
    }
  }, [student, form])

  const { data: classesData } = useQuery({
    queryKey: ['classes', schoolId],
    queryFn: () => studentsApi.getClasses({ school_id: schoolId, limit: 100 }),
    enabled: !!schoolId,
  })

  const updateMutation = useMutation({
    mutationFn: (data: CreateStudentForm) =>
      studentsApi.updateStudent(student!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] })
      onOpenChange(false)
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('students.editStudent')}</DialogTitle>
          <DialogDescription>{t('students.editStudentDesc')}</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit((data) => updateMutation.mutate(data))} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('students.name')}</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="Enter student name" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="roll_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('students.rollNumber')}</FormLabel>
                    <FormControl>
                      <Input {...field} placeholder="Roll number" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="gender"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('students.gender')}</FormLabel>
                    <FormControl>
                      <select
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        {...field}
                      >
                        <option value="">Select gender</option>
                        {genderOptions.map((o) => (
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
              name="class_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('students.class')}</FormLabel>
                  <FormControl>
                    <select
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      {...field}
                    >
                      <option value="">Select class</option>
                      {classesData?.items?.map((cls) => (
                        <option key={cls.id} value={cls.id}>{cls.name} (Grade {cls.grade})</option>
                      ))}
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t('common.cancel')}
              </Button>
              <Button type="submit" disabled={updateMutation.isPending || !student}>
                {updateMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Edit2 className="h-4 w-4 mr-2" />
                )}
                {t('common.save')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

export default function StudentsPage() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const schoolId = user?.school_id ?? ''

  const [search, setSearch] = useState('')
  const [classFilter, setClassFilter] = useState('')
  const [offset, setOffset] = useState(0)
  const [createOpen, setCreateOpen] = useState(false)
  const [bulkOpen, setBulkOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editingStudent, setEditingStudent] = useState<studentsApi.Student | null>(null)

  const { data: classesData } = useQuery({
    queryKey: ['classes', schoolId],
    queryFn: () => studentsApi.getClasses({ school_id: schoolId, limit: 100 }),
    enabled: !!schoolId,
  })

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['students', schoolId, classFilter, search, offset],
    queryFn: () =>
      studentsApi.getStudents({
        school_id: schoolId,
        class_id: classFilter || undefined,
        search: search || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
    enabled: !!schoolId,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">{t('nav.students')}</h1>
          <p className="text-muted-foreground text-sm mt-1">{t('students.description')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="shadow-sm">
                <Upload className="h-4 w-4 mr-2" />
                {t('students.bulkImport')}
              </Button>
            </DialogTrigger>
            <BulkImportDialog open={bulkOpen} onOpenChange={setBulkOpen} />
          </Dialog>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="shadow-lg shadow-primary/20">
                <Plus className="h-4 w-4 mr-2" />
                {t('students.addStudent')}
              </Button>
            </DialogTrigger>
            <CreateStudentDialog open={createOpen} onOpenChange={setCreateOpen} schoolId={schoolId} />
          </Dialog>
        </div>
      </div>

      <Card className="border-none shadow-md overflow-hidden">
        <CardHeader className="pb-4 bg-muted/10 border-b border-muted/20">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t('students.searchPlaceholder')}
                className="pl-9 bg-background/50 border-muted-foreground/20 focus-visible:ring-primary/30"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setOffset(0) }}
              />
            </div>
            <select
              className="h-10 rounded-md border border-muted-foreground/20 bg-background/50 px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary/30"
              value={classFilter}
              onChange={(e) => { setClassFilter(e.target.value); setOffset(0) }}
            >
              <option value="">All classes</option>
              {classesData?.items?.map((cls) => (
                <option key={cls.id} value={cls.id}>{cls.name}</option>
              ))}
            </select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : isError ? (
            <div className="flex items-center justify-between p-6 bg-destructive/5">
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-5 w-5" />
                {t('common.error')}
              </div>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                {t('common.retry')}
              </Button>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader className="bg-muted/5">
                  <TableRow>
                    <TableHead>{t('students.name')}</TableHead>
                    <TableHead>{t('students.rollNumber')}</TableHead>
                    <TableHead>{t('students.class')}</TableHead>
                    <TableHead>{t('students.gender')}</TableHead>
                    <TableHead>{t('students.school')}</TableHead>
                    <TableHead>{t('students.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.items?.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-16">
                         <div className="flex flex-col items-center justify-center">
                            <Users className="h-10 w-10 text-muted-foreground/30 mb-3" />
                            <p className="text-sm text-muted-foreground font-medium">{t('common.noData')}</p>
                         </div>
                      </TableCell>
                    </TableRow>
                  ) : (
                    data?.items?.map((student) => (
                      <TableRow key={student.id} className="hover:bg-muted/5">
                        <TableCell className="font-medium">{student.name}</TableCell>
                        <TableCell className="text-muted-foreground font-mono text-sm">{student.roll_number || '-'}</TableCell>
                        <TableCell><Badge variant="outline" className="bg-background">{student.class_name || '-'}</Badge></TableCell>
                        <TableCell>
                          <Badge variant={
                            student.gender === 'male' ? 'default' :
                            student.gender === 'female' ? 'secondary' : 'outline'
                          } className="capitalize">
                            {student.gender || '-'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {student.school_name || '-'}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm" onClick={() => { setEditingStudent(student); setEditOpen(true); }}>
                            <Edit2 className="h-4 w-4 mr-1" /> {t('students.edit')}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
              {data && data.total > PAGE_SIZE && (
                <div className="flex items-center justify-between border-t border-muted/20 px-6 py-4 bg-muted/5">
                  <p className="text-sm text-muted-foreground font-medium">
                    Showing {offset + 1}-{Math.min(offset + PAGE_SIZE, data.total)} of <span className="text-foreground">{data.total}</span>
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="shadow-sm"
                      onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                      disabled={offset === 0}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm font-medium px-3">
                      {currentPage} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="shadow-sm"
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
      <EditStudentDialog open={editOpen} onOpenChange={setEditOpen} student={editingStudent} schoolId={schoolId} />
    </div>
  )
}
