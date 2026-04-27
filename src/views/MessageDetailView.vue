<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type MessageDetail } from '../api/client'
import { formatBytes } from '../utils/format'
import { useMessageNav } from '../composables/useMessageNav'

const route = useRoute()
const router = useRouter()
const { getNavigation } = useMessageNav()

const msg = ref<MessageDetail | null>(null)
const error = ref('')
const htmlAvailable = ref(false)

const messageId = computed(() => Number(route.params.id))
const nav = computed(() => getNavigation(messageId.value))

watch(() => route.params.id, async (id) => {
  msg.value = null
  error.value = ''
  htmlAvailable.value = false
  try {
    const numId = Number(id)
    const [detail, htmlRes] = await Promise.allSettled([
      api.getMessage(numId),
      fetch(`/messages/${numId}/html`, { method: 'HEAD' }),
    ])
    if (detail.status === 'fulfilled') {
      msg.value = detail.value
    } else {
      throw detail.reason
    }
    if (htmlRes.status === 'fulfilled' && htmlRes.value.ok) {
      htmlAvailable.value = true
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}, { immediate: true })

function onIframeMessage(e: MessageEvent) {
  const frame = document.querySelector('.msg-body-frame') as HTMLIFrameElement
  if (!frame || e.source !== frame.contentWindow) return
  const h = Number(e.data?.height)
  if (e.data?.type === 'resize' && Number.isFinite(h) && h >= 0) {
    frame.style.height = h + 'px'
  }
}

function goBack() {
  if (window.history.state?.back) {
    router.back()
  } else {
    router.push('/messages')
  }
}

onMounted(() => window.addEventListener('message', onIframeMessage))
onUnmounted(() => window.removeEventListener('message', onIframeMessage))
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
        <router-link v-if="nav.prev" id="msg-prev" :to="`/messages/${nav.prev}`" class="msg-nav-link">
          &larr; Prev
        </router-link>
        <router-link v-if="nav.next" id="msg-next" :to="`/messages/${nav.next}`" class="msg-nav-link">
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
      <iframe
        v-if="htmlAvailable"
        sandbox="allow-scripts"
        :src="`/messages/${msg.id}/html`"
        class="msg-body-frame"
        frameborder="0"
        scrolling="no"
      ></iframe>
      <pre v-else class="msg-body-text">{{ msg.body }}</pre>
    </div>
  </template>
</template>
