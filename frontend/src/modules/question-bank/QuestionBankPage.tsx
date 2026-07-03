import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Brain, ListChecks, BarChart3 } from 'lucide-react'

export default function QuestionBankPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{t('nav.questionBank')}</h1>
        <p className="text-muted-foreground text-sm mt-1">Manage and review AI-generated questions</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="hover:border-primary/50 cursor-pointer transition-colors" onClick={() => navigate('/questions')}>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/10">
                <ListChecks className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <CardTitle className="text-base">Question Bank</CardTitle>
                <CardDescription>View, filter, approve or reject questions</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full" onClick={(e) => { e.stopPropagation(); navigate('/questions') }}>
              Open Question Bank
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:border-primary/50 cursor-pointer transition-colors" onClick={() => navigate('/questions?status=pending_review')}>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-500/10">
                <Brain className="h-5 w-5 text-amber-400" />
              </div>
              <div>
                <CardTitle className="text-base">Review Queue</CardTitle>
                <CardDescription>Pending questions awaiting approval</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full" onClick={(e) => { e.stopPropagation(); navigate('/questions?status=pending_review') }}>
              Review Questions
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:border-primary/50 cursor-pointer transition-colors" onClick={() => navigate('/questions')}>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/10">
                <BarChart3 className="h-5 w-5 text-green-400" />
              </div>
              <div>
                <CardTitle className="text-base">Generate Questions</CardTitle>
                <CardDescription>Use AI to create new questions</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full" onClick={(e) => { e.stopPropagation(); navigate('/books') }}>
              Upload Textbook
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
