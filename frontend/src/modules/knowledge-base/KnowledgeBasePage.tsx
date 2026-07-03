import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import * as booksApi from '@/api/books'
import { TreePine, BookOpen, ChevronRight, Loader2, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export default function KnowledgeBasePage() {
  const { t } = useTranslation()
  const [selectedBookId, setSelectedBookId] = useState<string | null>(null)

  const { data: booksData, isLoading: booksLoading } = useQuery({
    queryKey: ['books'],
    queryFn: () => booksApi.getBooks(),
  })

  const { data: bookDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['book', selectedBookId],
    queryFn: () => booksApi.getBook(selectedBookId!),
    enabled: !!selectedBookId,
    select: (data: any) => data,
  })

  const books = booksData?.items ?? []
  const chapters = (bookDetail as any)?.chapters ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{t('nav.knowledgeBase')}</h1>
        <p className="text-muted-foreground text-sm mt-1">Curriculum knowledge graph from uploaded textbooks</p>
      </div>

      {booksLoading && (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      )}

      {!booksLoading && books.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 gap-3">
            <TreePine className="h-12 w-12 text-muted-foreground/40" />
            <p className="text-muted-foreground text-sm">No textbooks uploaded yet</p>
          </CardContent>
        </Card>
      )}

      {!booksLoading && books.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Textbooks</CardTitle>
            </CardHeader>
            <CardContent className="p-2">
              {books.map((book: any) => (
                <button
                  key={book.id}
                  onClick={() => setSelectedBookId(book.id)}
                  className={cn(
                    'w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors text-left',
                    selectedBookId === book.id
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'hover:bg-muted text-foreground'
                  )}
                >
                  <BookOpen className="h-4 w-4 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="truncate">{book.title}</p>
                    <p className="text-xs text-muted-foreground">Grade {book.grade}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                </button>
              ))}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {bookDetail ? bookDetail.title : 'Select a textbook'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {detailLoading && (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              )}
              {!detailLoading && !selectedBookId && (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <TreePine className="h-10 w-10 mb-2 opacity-40" />
                  <p className="text-sm">Select a textbook to view its curriculum structure</p>
                </div>
              )}
              {!detailLoading && selectedBookId && chapters.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <AlertCircle className="h-6 w-6 mb-2 opacity-40" />
                  <p className="text-sm">No chapters extracted yet. Run extraction on this book.</p>
                </div>
              )}
              {!detailLoading && chapters.length > 0 && (
                <div className="space-y-4">
                  {chapters.map((ch: any, idx: number) => (
                    <div key={ch.id} className="border rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="shrink-0">Ch {idx + 1}</Badge>
                        <h3 className="font-medium text-sm">{ch.title_en || ch.unit_name || `Chapter ${ch.sequence}`}</h3>
                      </div>
                      {ch.topics && ch.topics.length > 0 && (
                        <div className="ml-8 space-y-1">
                          {ch.topics.map((t: any) => (
                            <p key={t.id} className="text-sm text-muted-foreground flex items-center gap-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 shrink-0" />
                              {t.title_en || `Topic ${t.sequence}`}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
