const KB = 1024
const MB = 1024 * KB
const GB = 1024 * MB

export function formatBytes(b: number): string {
  if (b >= GB) return `${(b / GB).toFixed(1)} GB`
  if (b >= MB) return `${(b / MB).toFixed(1)} MB`
  if (b >= KB) return `${(b / KB).toFixed(1)} KB`
  return `${b} B`
}

export function formatCount(n: number): string {
  if (n < 0) return '-' + formatCount(-n)
  if (n < 1000) return String(n)
  const s = String(n)
  const parts: string[] = []
  let rem = s.length % 3
  if (rem === 0) rem = 3
  parts.push(s.slice(0, rem))
  for (let i = rem; i < s.length; i += 3) {
    parts.push(s.slice(i, i + 3))
  }
  return parts.join(',')
}

export function formatMessageDate(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const mon = months[d.getMonth()]
  const day = String(d.getDate()).padStart(2, '0')
  if (d.getFullYear() === now.getFullYear()) {
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    return `${mon} ${day} ${hh}:${mm}`
  }
  return `${mon} ${day}, ${d.getFullYear()}`
}

export function formatSyncTime(iso: string | null): string {
  if (!iso) return 'never'
  const d = new Date(iso)
  const ms = Date.now() - d.getTime()
  const minutes = Math.floor(ms / 60000)
  const hours = Math.floor(ms / 3600000)
  const days = Math.floor(ms / 86400000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 30) return `${days}d ago`
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${months[d.getMonth()]} ${String(d.getDate()).padStart(2, '0')}, ${d.getFullYear()}`
}
