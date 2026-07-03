import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as questionsApi from '@/api/questions'
import type { Question } from '@/types'

export function useQuestions(params?: {
  concept_id?: string
  competency_id?: string
  bloom_level?: string
  difficulty?: string
  approval_status?: string
  question_type?: string
}) {
  return useQuery({
    queryKey: ['questions', params],
    queryFn: () => questionsApi.getQuestions(params),
  })
}

export function useQuestion(id: string | undefined) {
  return useQuery({
    queryKey: ['questions', id],
    queryFn: () => questionsApi.getQuestion(id!),
    enabled: !!id,
  })
}

export function useCreateQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (question: Partial<Question>) =>
      questionsApi.createQuestion(question),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
    },
  })
}

export function useUpdateQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Question> }) =>
      questionsApi.updateQuestion(id, data),
    onSuccess: (_result, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['questions', id] })
      queryClient.invalidateQueries({ queryKey: ['questions'] })
    },
  })
}

export function useApproveQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => questionsApi.approveQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
    },
  })
}

export function useRejectQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => questionsApi.rejectQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
    },
  })
}

export function useDeleteQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => questionsApi.deleteQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] })
    },
  })
}
