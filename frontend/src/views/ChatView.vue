<template>
  <div class="chat-layout">
    <!-- Sidebar: Notebook Panel -->
    <aside class="chat-sidebar" :class="{ 'collapsed': isSidebarCollapsed }">
      <div class="sidebar-header">
        <button class="icon-btn" @click="goBack" title="返回">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <span class="sidebar-title" v-if="!isSidebarCollapsed">文档笔记</span>
        <button class="icon-btn" @click="toggleSidebar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="3" x2="9" y2="21"></line>
          </svg>
        </button>
      </div>

      <div class="sidebar-content" v-if="!isSidebarCollapsed && detail">
        <div class="notebook-card">
          <div class="notebook-hole-punch"></div>
          <div class="notebook-hole-punch right"></div>
          <h2 class="file-name-lg">{{ detail.filename }}</h2>
          <p class="file-meta-lg">{{ formatSize(detail.file_size) }}</p>
          <span class="pill pill--success" v-if="detail.status === 1">就绪</span>
        </div>

        <div class="sidebar-section">
          <h3>摘要 SUMMARY</h3>
          <!-- API doesn't provide summary yet -->
          <p class="summary-text">{{ '暂无摘要 / NO_DATA' }}</p>
        </div>

        <div class="sidebar-actions">
          <!-- API doesn't provide previewUrl yet -->
          <button class="btn btn-primary full-width" disabled>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
            查看原文 (不可用)
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Chat Area: Terminal -->
    <main class="chat-main">
      <div class="chat-header">
        <div class="header-info">
          <h2 class="header-title">终端 TERMINAL://{{ detail?.filename || '加载中...' }}</h2>
          <span class="status-cursor">_</span>
        </div>
      </div>

      <div class="messages-container" ref="messagesRef">
        <div v-if="records.length === 0" class="empty-chat">
          <div class="empty-icon">👾</div>
          <h3>系统就绪 SYSTEM READY</h3>
          <p>等待指令 AWAITING INPUT...</p>
        </div>

        <div 
          v-for="msg in records" 
          :key="msg.id" 
          class="message-wrapper"
        >
          <!-- User Message -->
          <div v-if="msg.role === 'user'" class="message message--user">
            <div class="message-content">
              <span class="prompt-char">></span> {{ msg.content }}
            </div>
          </div>

          <!-- AI Message -->
          <div v-else class="message message--ai">
            <div class="ai-avatar">CPU</div>
            <div class="message-content">
              <div class="markdown-body">{{ msg.content }}</div>
              
              <!-- Sources -->
              <div v-if="msg.sources?.length" class="sources-list">
                <div class="sources-title">数据来源 SOURCE_DATA:</div>
                <div v-for="(source, idx) in msg.sources" :key="idx" class="source-item">
                  <span class="source-score">可信度:{{ (source.score * 100).toFixed(0) }}%</span>
                  <p>{{ source.snippet }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="loading" class="message message--ai loading-message">
          <div class="ai-avatar">CPU</div>
          <div class="typing-indicator">
            计算中 PROCESSING...
          </div>
        </div>
      </div>

      <div class="input-area">
        <div class="input-wrapper">
          <span class="input-prompt">></span>
          <textarea 
            v-model="question" 
            placeholder="输入指令..." 
            @keydown.enter.exact.prevent="submitQuestion"
            rows="1"
            ref="inputRef"
          ></textarea>
          <button class="send-btn" @click="submitQuestion" :disabled="!question.trim() || loading">
            发送 ENTER
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useFilesStore } from '@/store/files';
import { useQaStore } from '@/store/qa';
import { formatSize } from '@/utils/format';

/**
 * ChatView Component
 * -------------------
 * 智能问答核心页面
 * 包含左侧笔记本风格的侧边栏（显示文件详情）和右侧终端风格的对话区
 */

const route = useRoute();
const router = useRouter();
const filesStore = useFilesStore();
const qaStore = useQaStore();

// --- State ---
const question = ref(''); // 用户输入的问题
const messagesRef = ref<HTMLElement | null>(null); // 消息列表容器引用，用于滚动到底部
const inputRef = ref<HTMLTextAreaElement | null>(null); // 输入框引用，用于自动调整高度
const isSidebarCollapsed = ref(false); // 侧边栏折叠状态

// --- Computed ---
const detail = computed(() => filesStore.detail); // 当前文件详情
const records = computed(() => qaStore.records); // 当前文件的问答历史 (MessageItems)
const loading = computed(() => qaStore.loading); // 加载/回答生成中状态

// --- Methods ---
const goBack = () => router.push('/files');
const toggleSidebar = () => isSidebarCollapsed.value = !isSidebarCollapsed.value;

/**
 * 滚动消息列表到底部
 * 在新消息生成或加载历史记录后调用
 */
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight;
    }
  });
};

/**
 * 提交问题
 * 触发后端QA接口，并自动调整输入框高度
 */
const submitQuestion = async () => {
  if (!question.value.trim() || loading.value) return;
  
  const q = question.value;
  question.value = '';
  
  // 重置输入框高度为单行
  if (inputRef.value) inputRef.value.style.height = 'auto';

  // Use detail.id as context (fileId)
  await qaStore.sendQuestion(q, String(detail.value?.id));
};

// --- Watchers ---

// 监听输入内容，自动调整 Textarea 高度
watch(question, () => {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto';
    inputRef.value.style.height = inputRef.value.scrollHeight + 'px';
  }
});

// 监听消息记录变化，自动滚动到底部
watch(records, () => {
  scrollToBottom();
}, { deep: true });

// --- Lifecycle ---
onMounted(async () => {
  const id = route.params.id as string;
  if (id) {
    // 串行加载防止并发竞争（也可改为Promise.all优化）
    await filesStore.loadDetail(id);
    await qaStore.loadHistory(id);
    scrollToBottom();
  }
});
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: calc(100vh - 72px); /* Subtract navbar height only */
  background: white;
  overflow: hidden;
  position: relative;
  border-top: 4px solid black;
  margin: -40px; /* Offset parent padding */
}

/* Sidebar */
.chat-sidebar {
  width: 320px;
  border-right: 4px solid black;
  background: var(--nl-bg);
  display: flex;
  flex-direction: column;
  transition: width 0.1s steps(2);
  flex-shrink: 0;
}

.chat-sidebar.collapsed {
  width: 80px;
}

.chat-sidebar.collapsed .sidebar-content,
.chat-sidebar.collapsed .sidebar-title {
  display: none;
}

.chat-sidebar.collapsed .sidebar-header {
  height: auto;
  min-height: 60px;
  justify-content: center;
  flex-direction: column;
  gap: 16px;
  padding: 16px 0;
}

.chat-sidebar.collapsed .icon-btn {
  width: 48px;
  height: 48px;
  justify-content: center;
  align-items: center;
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 4px solid black;
  background: #f0f0f0;
}

.sidebar-title {
  font-family: var(--font-display);
  font-size: 16px;
  color: black;
  font-weight: bold;
}

.sidebar-content {
  padding: 24px;
  overflow-y: auto;
  background-image: linear-gradient(#e5e7eb 1px, transparent 1px);
  background-size: 100% 24px; /* Notebook lines */
}

.notebook-card {
  text-align: center;
  margin-bottom: 24px;
  border: 4px solid black;
  background: white;
  padding: 16px;
  position: relative;
  box-shadow: 6px 6px 0px black;
}

.notebook-hole-punch {
  width: 12px;
  height: 12px;
  background: #333;
  border-radius: 50%;
  position: absolute;
  top: 10px;
  left: 10px;
}
.notebook-hole-punch.right { left: auto; right: 10px; }

.file-name-lg {
  font-size: 16px;
  margin-bottom: 8px;
  word-break: break-word;
  font-family: var(--font-display);
}

.file-meta-lg {
  font-size: 14px;
  color: #555;
  margin-bottom: 12px;
  font-family: var(--font-body);
}

.sidebar-section {
  margin-bottom: 24px;
}

.sidebar-section h3 {
  font-size: 14px;
  margin-bottom: 12px;
  background: black;
  color: white;
  display: inline-block;
  padding: 2px 6px;
}

.summary-text {
  font-size: 16px;
  line-height: 1.5; /* Align with grid lines */
  color: black;
  font-family: var(--font-body);
}

.full-width { width: 100%; }

.icon-btn {
  background: white;
  border: 2px solid black;
  cursor: pointer;
  padding: 6px;
  color: black;
  display: flex;
  box-shadow: 2px 2px 0px black;
}

.icon-btn:hover {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0px black;
  background: #ec4899;
  color: white;
}

/* Chat Main */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #111; /* Terminal Dark Background */
  position: relative;
  color: #33ff00; /* Terminal Green */
  font-family: var(--font-body);
}

.chat-header {
  height: 60px;
  border-bottom: 4px solid #33ff00;
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: #000;
}

.header-title {
  font-size: 16px;
  color: #33ff00;
  font-family: var(--font-body);
}

.status-cursor {
  animation: blink 1s step-end infinite;
  margin-left: 4px;
  font-weight: bold;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.empty-chat {
  text-align: center;
  margin-top: 100px;
  color: #33ff00;
  opacity: 0.7;
}

.empty-icon { font-size: 48px; margin-bottom: 16px; filter: grayscale(100%) contrast(200%); }

.message-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 90%;
}

.message--user {
  align-self: flex-start; /* Terminal style: user is also left aligned usually, but let's keep it distinct */
  color: #fff;
  width: 100%;
  border-bottom: 1px dashed #555;
  padding-bottom: 12px;
}

.message--user .message-content {
  font-weight: bold;
}

.prompt-char { color: #ec4899; margin-right: 8px; }

.message--ai {
  align-self: flex-start;
  width: 100%;
}

.ai-avatar {
  width: 40px;
  height: 40px;
  background: #33ff00;
  color: black;
  border: 2px solid #33ff00;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
  flex-shrink: 0;
  font-family: var(--font-display);
}

.message--ai .message-content {
  color: #33ff00;
  padding: 0 16px;
  font-size: 18px;
  line-height: 1.4;
}

.sources-list {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 2px dashed #33ff00;
  font-size: 14px;
}

.sources-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #ec4899;
  font-family: var(--font-display);
}

.source-item {
  background: rgba(51, 255, 0, 0.1);
  padding: 8px;
  border: 1px solid #33ff00;
  margin-bottom: 8px;
}

.source-score {
  float: right;
  font-weight: 600;
  color: #ec4899;
}

/* Input Area */
.input-area {
  padding: 16px;
  background: #000;
  border-top: 4px solid #33ff00;
}

.input-wrapper {
  max-width: 100%;
  position: relative;
  display: flex;
  align-items: flex-end;
  background: #111;
  border: 2px solid #33ff00;
  padding: 8px;
}

.input-prompt {
  color: #ec4899;
  font-size: 20px;
  padding: 8px;
  font-weight: bold;
}

textarea {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px 12px;
  font-family: var(--font-body);
  font-size: 18px;
  color: #fff;
  resize: none;
  max-height: 200px;
  min-height: 24px;
}

textarea:focus { outline: none; }

.send-btn {
  background: #33ff00;
  color: black;
  border: none;
  padding: 0 16px;
  height: 36px;
  font-family: var(--font-display);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.1s;
  box-shadow: 4px 4px 0px #004400;
}

.send-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px #004400;
}

.send-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 0px 0px 0px transparent;
}

.send-btn:disabled {
  background: #555;
  cursor: not-allowed;
  box-shadow: none;
}
</style>
