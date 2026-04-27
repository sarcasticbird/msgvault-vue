<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type MessageDetail } from '../api/client'
import { formatBytes } from '../utils/format'
import { buildEmailSrcdoc } from '../utils/htmlEmail'
import { useMessageNav } from '../composables/useMessageNav'

const route = useRoute()
const router = useRouter()
const { getNavigation } = useMessageNav()

const msg = ref<MessageDetail | null>(null)
const error = ref('')
const hasExternalImages = ref(false)
const externalImagesLoaded = ref(false)
const iframeRef = ref<HTMLIFrameElement | null>(null)
let resizeObserver: ResizeObserver | null = null

const messageId = computed(() => Number(route.params.id))
const nav = computed(() => getNavigation(messageId.value))

const emailHtml = computed(() => {
  if (!msg.value?.body_html) return null
  return buildEmailSrcdoc(msg.value.body_html, msg.value.id)
})

const srcdoc = computed(() => emailHtml.value?.srcdoc ?? '')

watch(() => route.params.id, async (id) => {
  msg.value = null
  error.value = ''
  hasExternalImages.value = false
  externalImagesLoaded.value = false
  cleanupResizeObserver()
  try {
    msg.value = await api.getMessage(Number(id))
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}, { immediate: true })

watch(emailHtml, (result) => {
  hasExternalImages.value = result?.hasExternalImages ?? false
})

function cleanupResizeObserver() {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
}

function syncIframeHeight() {
  const frame = iframeRef.value
  if (!frame) return
  try {
    const body = frame.contentDocument?.body
    if (body) {
      const h = body.scrollHeight
      if (h > 0) frame.style.height = h + 'px'
    }
  } catch {
    // cross-origin access denied — ignore
  }
}

function onIframeLoad() {
  const frame = iframeRef.value
  if (!frame) return
  syncIframeHeight()
  try {
    const body = frame.contentDocument?.body
    if (body) {
      cleanupResizeObserver()
      resizeObserver = new ResizeObserver(syncIframeHeight)
      resizeObserver.observe(body)
    }
  } catch {
    // cross-origin access denied — ignore
  }
}

function loadExternalImages() {
  const frame = iframeRef.value
  if (!frame) return
  try {
    const doc = frame.contentDocument
    if (!doc) return
    doc.querySelectorAll('img[data-original-src]').forEach((img) => {
      const original = img.getAttribute('data-original-src')
      if (original) img.setAttribute('src', original)
    })
    externalImagesLoaded.value = true
    nextTick(syncIframeHeight)
  } catch {
    // cross-origin access denied — ignore
  }
}

function goBack() {
  if (window.history.state?.back) {
    router.back()
  } else {
    router.push('/messages')
  }
}

onUnmounted(cleanupResizeObserver)
</script>

<template>
  <div v-if="error" class="empty-state">
    <div class="empty-state-title">Error</div>
    <p>{{ error }}</p>
  </div>

  <div v-else-if="!msg" class="empty-state">
    <div class="empty-state-title">Loading...</div>
  </div>

  <template v-else>
    <nav class="breadcrumb">
      <a href="#" @click.prevent="goBack()">&larr; Back to messages</a>
      <span v-if="nav.total > 0" class="msg-nav">
        <router-link v-if="nav.prev" id="msg-prev" :to="`/messages/${nav.prev}`" replace class="msg-nav-link">
          &larr; Prev
        </router-link>
        <router-link v-if="nav.next" id="msg-next" :to="`/messages/${nav.next}`" replace class="msg-nav-link">
          Next &rarr;
        </router-link>
        <span class="msg-nav-pos">{{ nav.position }}</span>
      </span>
    </nav>

    <div class="card">
      <h2 class="msg-subject">
        <template v-if="msg.subject">{{ msg.subject }}</template>
        <em v-else class="text-muted">(no subject)</em>
      </h2>
      <table class="msg-headers">
        <tbody>
          <tr>
            <td class="msg-header-label">Date</td>
            <td class="msg-header-value">{{ new Date(msg.sent_at).toLocaleString() }}</td>
          </tr>
          <tr v-if="msg.from">
            <td class="msg-header-label">From</td>
            <td class="msg-header-value">{{ msg.from }}</td>
          </tr>
          <tr v-if="msg.to.length > 0">
            <td class="msg-header-label">To</td>
            <td class="msg-header-value">{{ msg.to.join(', ') }}</td>
          </tr>
          <tr v-if="msg.cc && msg.cc.length > 0">
            <td class="msg-header-label">Cc</td>
            <td class="msg-header-value">{{ msg.cc.join(', ') }}</td>
          </tr>
          <tr v-if="msg.labels.length > 0">
            <td class="msg-header-label">Labels</td>
            <td class="msg-header-value">
              <span v-for="label in msg.labels" :key="label" class="msg-label">{{ label }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="msg.attachments.length > 0" class="msg-section">
        <div class="msg-section-title">Attachments ({{ msg.attachments.length }})</div>
        <div v-for="(att, i) in msg.attachments" :key="i" class="msg-attachment">
          {{ att.filename }}
          <span class="msg-attachment-size">({{ formatBytes(att.size_bytes) }})</span>
        </div>
      </div>
      <div v-if="msg.conversation_id" class="msg-section text-sm">
        <router-link :to="{ path: '/messages', query: { conversation_id: String(msg.conversation_id) } }">
          View thread
        </router-link>
      </div>
    </div>

    <div class="card">
      <div v-if="hasExternalImages && !externalImagesLoaded" class="ext-img-banner">
        External images are blocked.
        <button class="ext-img-btn" @click="loadExternalImages">Load external images</button>
      </div>
      <iframe
        v-if="srcdoc"
        ref="iframeRef"
        sandbox="allow-same-origin"
        :srcdoc="srcdoc"
        class="msg-body-frame"
        frameborder="0"
        scrolling="no"
        @load="onIframeLoad"
      ></iframe>
      <pre v-else class="msg-body-text">{{ msg.body }}</pre>
    </div>
  </template>
</template>
