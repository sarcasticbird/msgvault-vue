const TRANSPARENT_PIXEL =
  'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'

const IFRAME_CSS = `body {
  margin: 0;
  padding: 16px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: #333;
  background: #fff;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
img { max-width: 100%; height: auto; }
a { color: #268bd2; }
pre { white-space: pre-wrap; word-wrap: break-word; font-family: inherit; }
table { border-collapse: collapse; max-width: 100%; }
td, th { padding: 4px 8px; }
`

export interface SanitizedEmail {
  srcdoc: string
  hasExternalImages: boolean
}

export function buildEmailSrcdoc(bodyHtml: string, messageId: number): SanitizedEmail {
  const parser = new DOMParser()
  const doc = parser.parseFromString(bodyHtml, 'text/html')
  let hasExternalImages = false

  doc.querySelectorAll('script').forEach((el) => el.remove())

  doc.querySelectorAll('img').forEach((img) => {
    const src = img.getAttribute('src') || ''
    if (src.startsWith('cid:')) {
      const cid = src.slice(4)
      img.setAttribute('src', `/api/v1/messages/${messageId}/inline/${encodeURIComponent(cid)}`)
    } else if (src.startsWith('http://') || src.startsWith('https://')) {
      hasExternalImages = true
      img.setAttribute('data-original-src', src)
      img.setAttribute('src', TRANSPARENT_PIXEL)
    }
  })

  doc.querySelectorAll('image, source, video[poster], input[type="image"]').forEach((el) => {
    for (const attr of ['src', 'href', 'xlink:href', 'srcset', 'poster']) {
      const v = el.getAttribute(attr)
      if (v && /^https?:/i.test(v)) {
        hasExternalImages = true
        el.removeAttribute(attr)
      }
    }
  })

  doc.querySelectorAll('a').forEach((a) => {
    const href = (a.getAttribute('href') || '').trim().toLowerCase()
    if (href.startsWith('javascript:') || href.startsWith('vbscript:') || href.startsWith('data:')) {
      a.removeAttribute('href')
    }
    a.setAttribute('target', '_blank')
    a.setAttribute('rel', 'noopener noreferrer')
  })

  // Strip all inline event handlers (onerror, onload, onmouseover, etc.)
  doc.querySelectorAll('*').forEach((el) => {
    for (const attr of Array.from(el.attributes)) {
      if (attr.name.startsWith('on')) {
        el.removeAttribute(attr.name)
      }
    }
  })

  let srcdoc = '<!DOCTYPE html><html><head><meta charset="utf-8">'
  srcdoc += '<meta name="viewport" content="width=device-width, initial-scale=1">'
  srcdoc += `<style>${IFRAME_CSS}</style>`
  srcdoc += '</head><body>'
  srcdoc += doc.body.innerHTML
  srcdoc += '</body></html>'

  return { srcdoc, hasExternalImages }
}
