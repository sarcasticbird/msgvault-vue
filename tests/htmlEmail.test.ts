import { describe, expect, it } from 'vitest'
import { buildEmailSrcdoc } from '../src/utils/htmlEmail'

describe('inline email images', () => {
  it('requests the v0.21 inline endpoint with an encoded Content-ID', () => {
    const email = buildEmailSrcdoc('<img src="cid:part+1@example.com">', 42)
    const doc = new DOMParser().parseFromString(email.srcdoc, 'text/html')
    expect(doc.querySelector('img')?.getAttribute('src')).toBe(
      '/api/v1/messages/42/inline?cid=part%2B1%40example.com',
    )
    expect(email.hasExternalImages).toBe(false)
  })
})
