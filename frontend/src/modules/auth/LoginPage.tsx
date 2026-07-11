import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import { useLoginMutation } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { Loader2 } from 'lucide-react'

const loginSchema = z.object({
  email: z.string().email('auth.invalidEmail'),
  password: z.string().min(6, 'auth.passwordMin'),
})

type LoginForm = z.infer<typeof loginSchema>

const demoAccounts = [
  { label: 'Teacher', email: 'r.sharma@gseb.org', role: 'teacher' },
  { label: 'Principal', email: 'a.patel@gseb.org', role: 'principal' },
]

export default function LoginPage() {
  const { t } = useTranslation()
  const loginMutation = useLoginMutation()

  const form = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: 'r.sharma@gseb.org',
      password: 'Teacher@123',
    },
  })

  const { register, handleSubmit, setValue, formState: { errors } } = form

  const onSubmit = (data: LoginForm) => {
    loginMutation.mutate(data)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-primary">
            Testellect
          </h1>
          <p className="text-muted-foreground text-sm">
            {t('app.tagline')}
          </p>
        </div>

        <Card className="border-border/50 shadow-xl">
          <CardHeader>
            <CardTitle>{t('auth.signIn')}</CardTitle>
            <CardDescription>
              Enter your credentials to access the platform
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {loginMutation.isError && (
                <div className="bg-destructive/10 border border-destructive/20 text-destructive text-sm p-3 rounded-lg">
                  {t('auth.loginFailed')}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">{t('auth.email')}</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="admin@gseb.org"
                  {...register('email')}
                />
                {errors.email && (
                  <p className="text-[0.8rem] font-medium text-destructive">
                    {t(errors.email.message as string)}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">{t('auth.password')}</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  {...register('password')}
                />
                {errors.password && (
                  <p className="text-[0.8rem] font-medium text-destructive">
                    {t(errors.password.message as string)}
                  </p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={loginMutation.isPending}
              >
                {loginMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('auth.signingIn')}
                  </>
                ) : (
                  t('auth.signIn')
                )}
              </Button>
            </form>

            <div className="mt-6 pt-4 border-t border-border">
              <p className="text-xs text-muted-foreground mb-3 text-center">
                {t('auth.quickLogin')}
              </p>
              <div className="grid grid-cols-2 gap-2">
                {demoAccounts.map((acct) => (
                  <Button
                    key={acct.role}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setValue('email', acct.email)
                      setValue('password', acct.role === 'admin' ? 'Admin@123' : acct.role === 'teacher' ? 'Teacher@123' : acct.role === 'principal' ? 'Principal@123' : 'Deo@123')
                    }}
                  >
                    {acct.label}
                  </Button>
                ))}
              </div>
            </div>
            
            <div className="mt-4 text-center">
              <a href="/admin/login" className="text-xs text-primary hover:underline">
                Go to Admin & DEO Login
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
