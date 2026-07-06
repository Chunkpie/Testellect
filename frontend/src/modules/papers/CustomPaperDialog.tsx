import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Loader2 } from 'lucide-react'
import { CustomLoader } from '@/components/ui/CustomLoader'
import * as papersApi from '@/api/papers'
import * as booksApi from '@/api/books'
import * as subjectsApi from '@/api/subjects'

export function CustomPaperDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [grade, setGrade] = useState<string>('10')
  const [subjectId, setSubjectId] = useState<string>('2') // Default to Math (id 2)
  const [selectedChapters, setSelectedChapters] = useState<number[]>([])
  const [totalQuestions, setTotalQuestions] = useState<number>(10)
  const [difficulty, setDifficulty] = useState<string>('medium')

  // Fetch subjects
  const { data: subjects } = useQuery({
    queryKey: ['subjects'],
    queryFn: () => subjectsApi.getSubjects(),
  })

  // Fetch book to get chapters
  const { data: booksData } = useQuery({
    queryKey: ['books', grade, subjectId],
    queryFn: () => booksApi.getBooks({ grade, subject_id: subjectId }),
    enabled: !!grade && !!subjectId,
  })

  const bookId = booksData?.items?.[0]?.id

  const { data: bookDetails, isLoading: loadingChapters } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => booksApi.getBook(String(bookId)),
    enabled: !!bookId,
  })

  const chapters = (bookDetails as any)?.chapters || []

  const generateMutation = useMutation({
    mutationFn: () =>
      papersApi.customGeneratePaper({
        grade: parseInt(grade),
        subject_id: parseInt(subjectId),
        chapter_ids: selectedChapters,
        total_questions: totalQuestions,
        difficulty: difficulty,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['papers'] })
      onOpenChange(false)
      setSelectedChapters([])
      setTotalQuestions(10)
    },
    onError: (err: any) => {
      alert(err?.response?.data?.detail || 'Failed to generate custom paper')
    },
  })

  const handleChapterToggle = (id: number) => {
    setSelectedChapters((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Generate Custom Paper</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 my-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Grade</label>
              <Select
                options={Array.from({ length: 12 }, (_, i) => ({
                  value: String(i + 1),
                  label: `Class ${i + 1}`,
                }))}
                value={grade}
                onChange={(e) => { setGrade(e.target.value); setSelectedChapters([]) }}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Subject</label>
              <Select
                options={
                  subjects?.items?.map((s: any) => ({
                    value: String(s.id),
                    label: s.name_en,
                  })) || []
                }
                value={subjectId}
                onChange={(e) => { setSubjectId(e.target.value); setSelectedChapters([]) }}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Select Chapters</label>
            <div className="border rounded-md max-h-48 overflow-y-auto p-2 space-y-1">
              {loadingChapters ? (
                <div className="text-sm text-muted-foreground p-2 text-center">Loading chapters...</div>
              ) : chapters.length === 0 ? (
                <div className="text-sm text-muted-foreground p-2 text-center">No chapters found for this subject.</div>
              ) : (
                chapters.map((ch: any) => (
                  <label key={ch.id} className="flex items-center gap-2 p-1.5 hover:bg-muted rounded cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedChapters.includes(ch.id)}
                      onChange={() => handleChapterToggle(ch.id)}
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm font-medium truncate flex-1">{ch.sequence}. {ch.title_en}</span>
                  </label>
                ))
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Total Questions</label>
              <Input
                type="number"
                min={1}
                max={100}
                value={totalQuestions}
                onChange={(e) => setTotalQuestions(parseInt(e.target.value) || 0)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Difficulty</label>
              <Select
                options={[
                  { value: 'easy', label: 'Easy' },
                  { value: 'medium', label: 'Medium' },
                  { value: 'hard', label: 'Hard' },
                ]}
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending || selectedChapters.length === 0 || totalQuestions < 1}
          >
            {generateMutation.isPending ? 'Generating...' : 'Generate Paper'}
          </Button>
        </DialogFooter>
      </DialogContent>
      {generateMutation.isPending && (
        <CustomLoader message="Generating Custom Paper..." />
      )}
    </Dialog>
  )
}
