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
  { label: 'Admin', email: 'admin@gseb.org', role: 'admin' },
  { label: 'DEO', email: 'v.singh@gseb.org', role: 'deo' },
]

export default function AdminLoginPage() {
  const { t } = useTranslation()
  const loginMutation = useLoginMutation()

  const form = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: 'admin@gseb.org',
      password: 'Admin@123',
    },
  })

  const { register, handleSubmit, setValue, formState: { errors } } = form

  const onSubmit = (data: LoginForm) => {
    loginMutation.mutate(data)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-50">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-slate-800">
            GSEB PARAKH <span className="text-primary">Admin</span>
          </h1>
          <p className="text-muted-foreground text-sm">
            Administrator & DEO Portal
          </p>
        </div>

        <Card className="border-border/50 shadow-xl">
          <CardHeader>
            <CardTitle>{t('auth.signIn')}</CardTitle>
            <CardDescription>
              Enter your credentials to access the admin portal
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
                className="w-full bg-slate-800 hover:bg-slate-700"
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
                      setValue('password', acct.role === 'admin' ? 'Admin@123' : 'Deo@123')
                    }}
                  >
                    {acct.label}
                  </Button>
                ))}
              </div>
            </div>
            
            <div className="mt-4 text-center">
              <a href="/login" className="text-xs text-slate-500 hover:underline">
                Back to School Login
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
