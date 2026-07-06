import { useState, useRef, useCallback, useEffect } from 'react'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import Webcam from 'react-webcam'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Loader2, Upload, Camera, RefreshCw } from 'lucide-react'
import api from '@/api/client'
import { getStudents } from '@/api/students'

interface ScannerDialogProps {
  open: boolean
  onOpenChange: (v: boolean) => void
  batchId: string
}

export function ScannerDialog({ open, onOpenChange, batchId }: ScannerDialogProps) {
  const queryClient = useQueryClient()
  const webcamRef = useRef<Webcam>(null)
  
  const [file, setFile] = useState<File | null>(null)
  const [studentId, setStudentId] = useState<string>('')
  const [mode, setMode] = useState<'webcam' | 'upload'>('webcam')

  const { data: studentsData, isLoading: studentsLoading } = useQuery({
    queryKey: ['students'],
    queryFn: () => getStudents({ limit: 500 }),
    enabled: open,
  })

  const uploadMutation = useMutation({
    mutationFn: async (f: File) => {
      const formData = new FormData()
      formData.append('file', f)
      if (studentId) {
        formData.append('student_id', studentId)
      }
      const { data } = await api.post(`/omr/${batchId}/scan-upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['omr-sessions'] })
      onOpenChange(false)
      setFile(null)
      setStudentId('')
    }
  })

  const handleCapture = useCallback(() => {
    if (!webcamRef.current) return
    const imageSrc = webcamRef.current.getScreenshot()
    if (!imageSrc) return

    // Convert base64 to file
    fetch(imageSrc)
      .then(res => res.blob())
      .then(blob => {
        const capturedFile = new File([blob], `scan_${Date.now()}.jpg`, { type: 'image/jpeg' })
        uploadMutation.mutate(capturedFile)
      })
  }, [webcamRef, uploadMutation])

  const studentOptions = [
    { value: '', label: 'Unassigned (Scan without Student)' },
    ...(studentsData?.items || []).map(s => ({ value: String(s.id), label: `${s.name} (${s.roll_number || 'N/A'})` }))
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Scan & Evaluate OMR</DialogTitle>
          <DialogDescription>
            Map the scan to a student, then capture using your webcam or upload a file.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="space-y-2">
            <Label>Student (Option A: Pre-assign)</Label>
            {studentsLoading ? (
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading students...
              </div>
            ) : (
              <Select 
                options={studentOptions} 
                value={studentId} 
                onChange={(e) => setStudentId(e.target.value)} 
                placeholder="Select a student..."
              />
            )}
          </div>

          <Tabs value={mode} onValueChange={(v) => setMode(v as 'webcam'|'upload')} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="webcam"><Camera className="w-4 h-4 mr-2" /> Live Camera</TabsTrigger>
              <TabsTrigger value="upload"><Upload className="w-4 h-4 mr-2" /> File Upload</TabsTrigger>
            </TabsList>
            
            <TabsContent value="webcam" className="mt-4 space-y-4">
              <div className="relative rounded-md overflow-hidden bg-black aspect-video flex items-center justify-center">
                {open && mode === 'webcam' ? (
                  <Webcam
                    audio={false}
                    ref={webcamRef}
                    screenshotFormat="image/jpeg"
                    videoConstraints={{ facingMode: 'environment' }}
                    className="w-full h-full object-cover"
                  />
                ) : null}
              </div>
            </TabsContent>
            
            <TabsContent value="upload" className="mt-4 space-y-4">
              <Input type="file" accept="image/*,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </TabsContent>
          </Tabs>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          {mode === 'webcam' ? (
            <Button onClick={handleCapture} disabled={uploadMutation.isPending}>
              {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Camera className="h-4 w-4 mr-2" />}
              Capture & Evaluate
            </Button>
          ) : (
            <Button onClick={() => file && uploadMutation.mutate(file)} disabled={!file || uploadMutation.isPending}>
              {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Upload className="h-4 w-4 mr-2" />}
              Upload & Evaluate
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
