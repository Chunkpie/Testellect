import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Download } from 'lucide-react'

interface QRSyncModalProps {
  open: boolean
  onOpenChange: (v: boolean) => void
  data: any
}

export function QRSyncModal({ open, onOpenChange, data }: QRSyncModalProps) {
  // We compress the data into a minimal JSON string to ensure it fits in a QR code
  // In a real app, you might use lz-string or msgpack, but JSON.stringify is fine for a summary.
  const summaryPayload = JSON.stringify({
    d: data?.district || data?.school_id || 'Unknown',
    tS: data?.total_students || 0,
    tA: data?.total_assessments || 0,
    avg: data?.average_score || 0,
    ts: Date.now()
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Offline Data Sync</DialogTitle>
          <DialogDescription>
            Scan this QR code with the Parakh District App to sync the latest analytics offline.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center p-6 bg-white rounded-md mt-4">
          <QRCodeSVG 
            value={summaryPayload}
            size={256}
            level="M"
            includeMargin={true}
          />
          <p className="mt-4 text-xs text-muted-foreground break-all text-center">
            {summaryPayload.length} bytes encoded
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
