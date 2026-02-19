<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useSessionsStore } from '@/store/sessions'
import { createSession, listSessions } from '@/services/sessions'
import { listMessages, sendMessage } from '@/services/messages'

const sessionsStore = useSessionsStore()
const sessionTitle = ref('快速检索会话')
const messageInput = ref('')
const messages = ref<string[]>([])
const selectedSessionId = ref<number | null>(null)

const refreshSessions = async () => {
  sessionsStore.setLoading(true)
  try {
    const payload = await listSessions(1, 10, 'rag')
    sessionsStore.setSessions(payload.items)
  } catch {
    ElMessage.error('会话列表加载失败')
  } finally {
    sessionsStore.setLoading(false)
  }
}

const createNewSession = async () => {
  try {
    const session = await createSession({
      title: sessionTitle.value,
      biz_type: 'rag',
      context_id: null,
    })
    selectedSessionId.value = session.id
    await refreshSessions()
    ElMessage.success('会话创建成功')
  } catch {
    ElMessage.error('会话创建失败')
  }
}

const loadMessages = async (sessionId: number) => {
  try {
    const payload = await listMessages(sessionId)
    messages.value = payload.items.map((item) => `${item.role}: ${item.content}`)
  } catch {
    ElMessage.error('消息加载失败')
  }
}

const handleSend = async () => {
  if (!selectedSessionId.value || !messageInput.value.trim()) return
  try {
    await sendMessage(selectedSessionId.value, { content: messageInput.value })
    messageInput.value = ''
    await loadMessages(selectedSessionId.value)
  } catch {
    ElMessage.error('发送失败')
  }
}

onMounted(() => {
  refreshSessions()
})
</script>

<template>
  <div class="content-grid">
    <div class="card">
      <div class="section-title">
        <h2>检索会话</h2>
        <span class="tag">会话 + 消息</span>
      </div>
      <div style="display: grid; gap: 16px">
        <div class="table-header">
          <el-input v-model="sessionTitle" placeholder="会话标题" style="max-width: 260px" />
          <el-button type="primary" @click="createNewSession">创建会话</el-button>
          <el-select
            v-model="selectedSessionId"
            placeholder="选择会话"
            style="width: 220px"
            @change="(value) => value && loadMessages(value)"
          >
            <el-option
              v-for="session in sessionsStore.sessions"
              :key="session.id"
              :label="session.title"
              :value="session.id"
            />
          </el-select>
        </div>
        <div class="card" style="background: var(--accent-100)">
          <div class="muted">消息历史</div>
          <div style="display: grid; gap: 8px; margin-top: 8px">
            <div v-for="(item, index) in messages" :key="index">{{ item }}</div>
          </div>
        </div>
        <div class="table-header">
          <el-input v-model="messageInput" placeholder="输入检索内容" />
          <el-button type="primary" @click="handleSend">发送</el-button>
        </div>
      </div>
    </div>
  </div>
</template>
