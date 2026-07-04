import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as booksApi from '@/api/books'

export function useBooks(params?: {
  grade?: string
  subject_id?: string
  processing_status?: string
}) {
  return useQuery({
    queryKey: ['books', params],
    queryFn: () => booksApi.getBooks(params),
    refetchInterval: (query) => {
      const data = query.state.data as { items: any[] } | undefined
      if (data?.items && data.items.some((b: any) => !['ready', 'failed', 'uploaded', 'failed_extraction', 'failed_upload'].includes(b.processing_status))) {
        return 3000
      }
      return false
    },
  })
}

export function useBook(id: string | undefined) {
  return useQuery({
    queryKey: ['book', id],
    queryFn: () => booksApi.getBook(id!),
    enabled: !!id,
  })
}

export function useBookStatus(id: string | undefined) {
  return useQuery({
    queryKey: ['book-status', id],
    queryFn: () => booksApi.getBookStatus(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data
      if (data && data.processing_status !== 'ready' && data.processing_status !== 'failed' && data.processing_status !== 'uploaded') {
        return 5000
      }
      return false
    },
  })
}

export function useUploadBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ formData, onProgress }: { formData: FormData; onProgress?: (progress: number) => void }) =>
      booksApi.uploadBook(formData, onProgress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] })
    },
  })
}

export function useExtractBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => booksApi.extractBook(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['book', id] })
      queryClient.invalidateQueries({ queryKey: ['books'] })
    },
  })
}

export function useAnalyzeBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => booksApi.analyzeBook(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['book', id] })
      queryClient.invalidateQueries({ queryKey: ['books'] })
    },
  })
}

export function useGenerateQuestions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, params }: { id: string; params?: any }) => booksApi.generateQuestions(id, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
    },
  })
}

export function useDeleteBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => booksApi.deleteBook(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] })
    },
  })
}
