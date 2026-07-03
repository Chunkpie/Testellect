import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, CheckCircle2, XCircle, AlertCircle, Brain } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import * as aiApi from '@/api/ai'
import type { JobStatus } from '@/api/ai'

export function GenerationProgress({
  jobId,
  onDone,
}: {
  jobId: string | null
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [status, setStatus] = useState<JobStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!jobId) return

    const poll = async () => {
      try {
        const s = await aiApi.getJobStatus(jobId)
        setStatus(s)
        if (s.status === 'completed' || s.status === 'failed') {
          if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
        }
      } catch (e: any) {
        setError(e?.message || 'Polling failed')
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 2000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [jobId])

  if (!jobId) return null

  const progress = status ? status.progress : 0
  const total = status ? status.total : 100
  const pct = total > 0 ? Math.round((progress / total) * 100) : 0
  const isDone = status?.status === 'completed'
  const isFailed = status?.status === 'failed'
  const isProcessing = status?.status === 'processing'

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          {isDone ? (
            <CheckCircle2 className="h-5 w-5 text-green-500" />
          ) : isFailed || error ? (
            <XCircle className="h-5 w-5 text-destructive" />
          ) : (
            <Brain className="h-5 w-5 text-primary animate-pulse" />
          )}
          <div>
            <CardTitle className="text-base">
              {isDone
                ? t('ai.generation_complete')
                : isFailed || error
                  ? t('ai.generation_failed')
                  : t('ai.generating_questions')}
            </CardTitle>
            <CardDescription>
              {isProcessing && `${progress} / ${total} questions`}
              {isDone && `${progress} questions saved`}
              {isFailed && (status?.error || error || 'Unknown error')}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-2 w-full rounded-full bg-secondary">
          <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${pct}%` }} />
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{pct}%</span>
          {isProcessing && (
            <span className="flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              Processing...
            </span>
          )}
        </div>
        {(isDone || isFailed || error) && (
          <Button size="sm" variant="outline" className="w-full" onClick={onDone}>
            {t('common.close')}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
