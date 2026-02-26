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
          <!-- 文件信息展示 -->
          <h2 class="file-name-lg">{{ detail.filename || '未知文件' }}</h2>
          <p class="file-meta-lg">{{ formatSize(detail.file_size) }}</p>
          <!-- 状态标签 -->
          <span class="pill pill--success" v-if="detail.status === 2">就绪</span>
          <span class="pill pill--warning" v-if="detail.status === 1">向量化中...</span>
          <span class="pill pill--failed" v-if="detail.status === 3">失败</span>
          <!-- 上传时间 -->
          <p class="upload-time">上传时间: {{ formatTime(detail.upload_time) }}</p>
        </div>

        <div class="sidebar-section">
          <h3>摘要 SUMMARY</h3>
          <!-- API doesn't provide summary yet -->
          <p class="summary-text">{{ '暂无摘要 / NO_DATA' }}</p>
        </div>

        <div class="sidebar-actions">
          <button 
            class="btn btn-secondary full-width mb-3" 
            @click="generateSummary" 
            :disabled="generatingSummary"
            title="AI 自动生成总结笔记"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mr-2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            {{ generatingSummary ? '生成中...' : '生成智能笔记' }}
          </button>
          
          <button 
            class="btn btn-primary full-width mb-3" 
            @click="shareSession"
            title="发布到社区广场"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mr-2">
              <circle cx="18" cy="5" r="3"></circle>
              <circle cx="6" cy="12" r="3"></circle>
              <circle cx="18" cy="19" r="3"></circle>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
            </svg>
            发布到社区
          </button>

          <!-- Preview Button -->
          <button 
            class="btn btn-outline full-width" 
            @click="handlePreview"
            title="查看原文"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="mr-2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
            查看原文
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
        <!-- Status Indicator in Chat Header -->
        <div class="status-indicator" v-if="detail">
          <span v-if="detail.status === 2" class="status-ready">[READY]</span>
          <span v-else-if="detail.status === 1" class="status-busy">[VECTORIZING: {{ (vectorProgress || 0).toFixed(0) }}%]</span>
          <span v-else-if="detail.status === 3" class="status-error">[FAILED]</span>
        </div>
      </div>

      <div class="messages-container" ref="messagesRef">
        <!-- Vectorizing Blocking State -->
        <div v-if="detail?.status === 1" class="blocking-state">
           <div class="loading-spinner large"></div>
           <h2>SYSTEM INITIALIZING...</h2>
           <p>正在构建向量索引，请稍候...</p>
        </div>

        <div v-else-if="detail?.status === 3" class="blocking-state error">
           <div class="error-icon">!</div>
           <h2>SYSTEM ERROR</h2>
           <p>文件处理失败，无法进行对话。</p>
        </div>

        <div v-else-if="records.length === 0" class="empty-chat">
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
            <div class="message-header">
              <div class="user-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
              </div>
              <span class="message-time">{{ formatTime(msg.create_time) }}</span>
              <button class="copy-btn" @click="copyToClipboard(msg.content)" title="复制">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </div>
            <div class="message-content user-content">
              {{ msg.content }}
            </div>
          </div>

          <!-- AI Message -->
          <div v-else class="message message--ai">
            <div class="ai-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"></path>
                <path d="M12 6v6l4 2"></path>
              </svg>
            </div>
            <div class="message-content-wrapper">
              <div class="message-header ai-header">
                <span class="message-time">{{ formatTime(msg.create_time) }}</span>
                <button class="copy-btn" @click="copyToClipboard(msg.content)" title="复制">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                </button>
              </div>
              <div class="message-content ai-content" v-html="renderMarkdown(msg.content)"></div>
              
              <!-- Sources -->
              <div v-if="msg.sources?.length" class="sources-list">
                <div class="sources-title">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                  参考资料
                </div>
                <div v-for="(source, idx) in msg.sources" :key="idx" class="source-item">
                  <span class="source-score">{{ (source.score * 100).toFixed(0) }}% 匹配</span>
                  <p class="source-snippet">{{ source.snippet }}</p>
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

    <!-- Preview Modal -->
    <FilePreviewModal
      v-if="showPreview"
      :url="previewData.url"
      :file-name="previewData.fileName"
      :file-size="previewData.fileSize"
      :content-type="previewData.contentType"
      @close="closePreview"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useFilesStore } from '@/store/files';
import { useQaStore } from '@/store/qa';
import { formatSize, formatTime } from '@/utils/format';
import { communityService } from '@/services/community';
import { getFilePreview } from '@/services/files';
import { sendMessageStream } from '@/services/qa';
import MarkdownIt from 'markdown-it';
import { ElMessage } from 'element-plus';
import FilePreviewModal from '@/components/FilePreviewModal.vue';
import type { MessageItem } from '@/services/types';

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
});

const renderMarkdown = (content: string) => {
  return md.render(content || '');
};

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success('已复制到剪贴板');
  } catch {
    ElMessage.error('复制失败');
  }
};

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
const generatingSummary = ref(false); // Add generating summary state
const vectorProgress = ref(0); // Vectorization progress (simulated or real)
let pollingTimer: ReturnType<typeof setInterval> | null = null;

// Preview State
const showPreview = ref(false);
const previewData = ref({
  url: '',
  fileName: '',
  fileSize: '',
  contentType: ''
});

// --- Computed ---
const detail = computed(() => filesStore.detail); // 当前文件详情
const records = computed(() => qaStore.records); // 当前文件的问答历史 (MessageItems)
const loading = computed(() => qaStore.loading); // 加载/回答生成中状态

// --- Methods ---
const goBack = () => router.push('/files');
const toggleSidebar = () => isSidebarCollapsed.value = !isSidebarCollapsed.value;

const handlePreview = async () => {
  if (!detail.value) return;
  
  try {
    const url = await getFilePreview(detail.value.id);
    if (url) {
      previewData.value = {
        url,
        fileName: detail.value.filename,
        fileSize: formatSize(detail.value.file_size),
        contentType: detail.value.content_type
      };
      showPreview.value = true;
    } else {
      ElMessage.warning('无法获取预览链接');
    }
  } catch (e) {
    ElMessage.error('获取预览失败');
  }
};

const closePreview = () => {
  showPreview.value = false;
  previewData.value.url = ''; 
};

const generateSummary = async () => {
  if (!qaStore.sessionId || generatingSummary.value) return;
  generatingSummary.value = true;
  try {
    const res = await communityService.generateSummary(qaStore.sessionId);
    alert("笔记生成成功！\n" + res.summary_content);
  } catch (error) {
    console.error("Failed to generate summary", error);
    alert("生成失败，请稍后重试");
  } finally {
    generatingSummary.value = false;
  }
};

const shareSession = async () => {
  if (!detail.value || !qaStore.sessionId) return;
  
  const title = prompt("请输入分享标题", detail.value.filename + " 的问答分享");
  if (!title) return;
  
  const description = prompt("请输入分享描述", "这是关于 " + detail.value.filename + " 的精彩问答记录");
  
  try {
    await communityService.publishShare({
      source_file_id: detail.value.id,
      session_id: qaStore.sessionId,
      title: title,
      description: description || undefined,
      is_public_source: false
    });
    
    alert("发布成功！您的分享已发布到社区广场。");
    await router.push('/community');
  } catch (error) {
    console.error("Failed to share", error);
    alert("发布失败");
  }
};

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
 * 使用流式输出 (SSE)
 */
const submitQuestion = async () => {
  if (!question.value.trim() || loading.value) return;
  
  const q = question.value;
  question.value = '';
  
  // 重置输入框高度为单行
  if (inputRef.value) inputRef.value.style.height = 'auto';

  // 如果没有 session，先创建
  if (!qaStore.sessionId && detail.value?.id) {
    await qaStore.loadHistory(String(detail.value.id));
  }
  
  if (!qaStore.sessionId) {
    ElMessage.error('会话初始化失败');
    return;
  }

  // 添加用户消息到列表
  const userMsg: MessageItem = {
    id: Date.now(),
    session_id: qaStore.sessionId,
    user_id: 0,
    role: 'user',
    content: q,
    create_time: new Date().toISOString(),
  };
  qaStore.records.push(userMsg);
  
  // 创建空的 AI 消息占位
  const aiMsg: MessageItem = {
    id: Date.now() + 1,
    session_id: qaStore.sessionId,
    user_id: 0,
    role: 'assistant',
    content: '',
    create_time: new Date().toISOString(),
  };
  qaStore.records.push(aiMsg);
  
  // 设置加载状态
  qaStore.loading = true;
  
  // 流式接收 AI 响应
  try {
    await sendMessageStream(
      qaStore.sessionId,
      q,
      (chunk) => {
        // 追加内容到 AI 消息
        aiMsg.content += chunk;
        scrollToBottom();
      },
      () => {
        // 流式完成
        qaStore.loading = false;
        ElMessage.success('回答完成');
      },
      (error) => {
        // 错误处理
        qaStore.loading = false;
        aiMsg.content += '\n\n[Error: ' + error + ']';
        ElMessage.error('回答生成失败: ' + error);
      }
    );
  } catch (error) {
    qaStore.loading = false;
    console.error('Send message error:', error);
    ElMessage.error('发送消息失败');
  }
};

// --- Polling Logic ---
const startPolling = () => {
  if (pollingTimer) return;
  
  // Initial progress
  vectorProgress.value = 0;
  
  pollingTimer = setInterval(async () => {
    // Simulate progress while waiting for status update
    if (vectorProgress.value < 90) {
      vectorProgress.value += (100 - vectorProgress.value) * 0.1;
    }
    
    if (detail.value?.id) {
      // Use refreshDetail (silent update) instead of loadDetail
      // Check if refreshDetail exists on store (it was added in files.ts)
      if (typeof filesStore.refreshDetail === 'function') {
        await filesStore.refreshDetail(detail.value.id);
      } else {
        // Fallback if refreshDetail is not available (though we just added it)
        console.warn("refreshDetail not found on filesStore");
      }
      
      // Check status
      if (detail.value?.status === 2 || detail.value?.status === 3) {
        vectorProgress.value = 100;
        stopPolling();
      }
    }
  }, 2000); // Poll every 2 seconds
};

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
};

// --- Watchers ---

// Monitor file status to start/stop polling
watch(() => detail.value?.status, (newStatus) => {
  if (newStatus === 1) { // Vectorizing
    startPolling();
  } else if (newStatus === 2 || newStatus === 3) { // Ready or Failed
    stopPolling();
  }
}, { immediate: true });

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
    
    // Check initial status for polling
    if (detail.value?.status === 1) {
      startPolling();
    }
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
/* ===== RETRO PIXEL GAME THEME ===== */

/* Chat Layout */
.chat-layout {
  display: flex;
  height: calc(100vh - 72px);
  background: #000;
  overflow: hidden;
  position: relative;
  margin: -40px;
  font-family: 'Courier New', monospace;
}

/* Sidebar - Retro RPG Panel Style */
.chat-sidebar {
  width: 320px;
  border-right: 4px solid #ffd700;
  background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: relative;
}

.chat-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(rgba(255,215,0,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,215,0,0.03) 1px, transparent 1px);
  background-size: 8px 8px;
  pointer-events: none;
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
  border-bottom: 4px solid #ffd700;
  background: #2d1b4e;
}

.sidebar-title {
  font-size: 14px;
  color: #ffd700;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 2px 2px 0 #000;
}

.sidebar-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

/* Retro RPG Quest Card */
.notebook-card {
  text-align: center;
  margin-bottom: 24px;
  border: 4px solid #ffd700;
  background: #1a1a2e;
  padding: 20px;
  position: relative;
  box-shadow: 
    4px 4px 0 #000,
    inset 0 0 20px rgba(255, 215, 0, 0.1);
}

.notebook-card::before {
  content: '📜';
  position: absolute;
  top: -15px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 24px;
  background: #0f0f1a;
  padding: 0 8px;
}

.notebook-hole-punch {
  display: none;
}

.file-name-lg {
  font-size: 16px;
  margin-bottom: 12px;
  word-break: break-word;
  color: #fff;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.file-meta-lg {
  font-size: 14px;
  color: #888;
  margin-bottom: 12px;
  font-family: 'Courier New', monospace;
}

.upload-time {
  font-size: 12px;
  color: #666;
  margin-top: 8px;
  font-family: 'Courier New', monospace;
}

/* Status Pills - Retro RPG Style */
.pill {
  display: inline-block;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: bold;
  text-transform: uppercase;
  border: 2px solid;
  margin: 4px 2px;
  font-family: 'Courier New', monospace;
}

.pill--success {
  background: #00ff00;
  color: #000;
  border-color: #00aa00;
  box-shadow: 2px 2px 0 #004400;
}

.pill--warning {
  background: #ffff00;
  color: #000;
  border-color: #aaaa00;
  box-shadow: 2px 2px 0 #444400;
  animation: blink-yellow 1s step-end infinite;
}

.pill--failed {
  background: #ff0000;
  color: #fff;
  border-color: #aa0000;
  box-shadow: 2px 2px 0 #440000;
}

@keyframes blink-yellow {
  50% { opacity: 0.7; }
}

/* Sidebar Section */
.sidebar-section {
  margin-bottom: 24px;
  border: 2px dashed #ffd700;
  padding: 16px;
  background: rgba(255, 215, 0, 0.05);
}

.sidebar-section h3 {
  font-size: 12px;
  margin-bottom: 12px;
  background: #ffd700;
  color: #000;
  display: inline-block;
  padding: 4px 8px;
  font-weight: bold;
  text-transform: uppercase;
}

.summary-text {
  font-size: 14px;
  line-height: 1.6;
  color: #aaa;
  font-family: 'Courier New', monospace;
}

/* Action Buttons */
.btn {
  padding: 12px 16px;
  border: 3px solid;
  font-family: 'Courier New', monospace;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.1s;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  text-transform: uppercase;
  margin-bottom: 12px;
  box-shadow: 4px 4px 0 #000;
}

.btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.btn:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 0 0 0 #000;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-primary {
  background: #ff00ff;
  color: #fff;
  border-color: #aa00aa;
}

.btn-secondary {
  background: #00ffff;
  color: #000;
  border-color: #00aaaa;
}

.btn-outline {
  background: transparent;
  border: 2px dashed #888;
  color: #888;
  box-shadow: none;
}

.mr-2 { margin-right: 8px; }
.mb-3 { margin-bottom: 12px; }

.icon-btn {
  background: #ffd700;
  border: 2px solid #000;
  cursor: pointer;
  padding: 6px;
  color: #000;
  display: flex;
  box-shadow: 2px 2px 0 #000;
}

.icon-btn:hover {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
  background: #ff00ff;
  color: #fff;
}

/* ===== MAIN CHAT AREA - RETRO GAME CONSOLE ===== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #0a0a0a;
  position: relative;
  font-family: 'Courier New', monospace;
  overflow: hidden;
}

/* Scanline effect */
.chat-main::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.15),
    rgba(0, 0, 0, 0.15) 1px,
    transparent 1px,
    transparent 2px
  );
  pointer-events: none;
  z-index: 100;
}

.chat-header {
  height: 56px;
  border-bottom: 4px solid #00ff00;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #000;
  position: relative;
  z-index: 10;
}

.header-title {
  font-size: 14px;
  color: #00ff00;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 0 0 10px #00ff00;
}

.status-indicator {
  font-size: 12px;
  padding: 4px 8px;
  font-weight: bold;
  font-family: 'Courier New', monospace;
}

.status-ready {
  background: #00ff00;
  color: #000;
}

.status-busy {
  background: #ffff00;
  color: #000;
  animation: blink 0.5s step-end infinite;
}

.status-error {
  background: #ff0000;
  color: #fff;
}

@keyframes blink {
  50% { opacity: 0.5; }
}

/* Messages Container */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  z-index: 1;
}

/* Empty State */
.empty-chat {
  text-align: center;
  margin-top: 80px;
  color: #00ff00;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  filter: grayscale(100%);
  animation: float 2s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

/* Message Wrapper */
.message-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 85%;
}

.message {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 3px solid;
}

/* User Message - Player Style */
.message--user {
  align-self: flex-end;
  background: #0066cc;
  color: #fff;
  border-color: #004499;
  box-shadow: 4px 4px 0 #000;
}

.message--user .message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  border-bottom: 1px dashed rgba(255,255,255,0.3);
  padding-bottom: 8px;
}

.message--user .user-avatar {
  width: 24px;
  height: 24px;
  background: #ffd700;
  border: 2px solid #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.message--user .message-time {
  font-size: 10px;
  color: rgba(255,255,255,0.7);
}

.message--user .copy-btn {
  background: transparent;
  border: none;
  color: rgba(255,255,255,0.7);
  cursor: pointer;
  padding: 4px;
  margin-left: auto;
  opacity: 0;
  transition: opacity 0.2s;
}

.message--user:hover .copy-btn {
  opacity: 1;
}

.message-content {
  line-height: 1.5;
  font-size: 14px;
  word-wrap: break-word;
}

/* AI Message - NPC Style */
.message--ai {
  align-self: flex-start;
  background: #1a1a2e;
  color: #00ff00;
  border-color: #00ff00;
  box-shadow: 4px 4px 0 #004400;
  max-width: 95%;
}

.message--ai .ai-avatar {
  width: 40px;
  height: 40px;
  background: #00ff00;
  color: #000;
  border: 3px solid #000;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 10px;
  flex-shrink: 0;
  box-shadow: 2px 2px 0 #004400;
}

.message--ai .message-content-wrapper {
  flex: 1;
  min-width: 0;
}

.message--ai .message-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  border-bottom: 1px dashed #004400;
  padding-bottom: 8px;
}

.message--ai .message-time {
  font-size: 10px;
  color: #008800;
}

.message--ai .copy-btn {
  background: transparent;
  border: none;
  color: #008800;
  cursor: pointer;
  padding: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.message--ai:hover .copy-btn {
  opacity: 1;
}

.copy-btn:hover {
  color: #00ff00;
}

/* AI Content - Terminal Style */
.ai-content {
  color: #00ff00;
  font-family: 'Courier New', monospace;
  line-height: 1.6;
}

.ai-content :deep(h1),
.ai-content :deep(h2),
.ai-content :deep(h3),
.ai-content :deep(h4),
.ai-content :deep(h5),
.ai-content :deep(h6) {
  color: #ffd700;
  margin: 12px 0 8px;
  font-weight: bold;
  text-shadow: 2px 2px 0 #000;
}

.ai-content :deep(p) {
  margin-bottom: 8px;
}

.ai-content :deep(ul),
.ai-content :deep(ol) {
  padding-left: 20px;
  margin-bottom: 8px;
}

.ai-content :deep(li) {
  margin-bottom: 4px;
}

.ai-content :deep(code) {
  background: #003300;
  color: #ff00ff;
  padding: 2px 6px;
  font-family: 'Courier New', monospace;
}

.ai-content :deep(pre) {
  background: #001100;
  border: 2px solid #00ff00;
  padding: 12px;
  margin: 8px 0;
  overflow-x: auto;
}

.ai-content :deep(pre code) {
  background: transparent;
  color: #00ff00;
}

.ai-content :deep(blockquote) {
  border-left: 4px solid #ffd700;
  padding-left: 12px;
  margin: 8px 0;
  color: #888;
  font-style: italic;
}

.ai-content :deep(a) {
  color: #00ffff;
  text-decoration: underline;
}

.ai-content :deep(a:hover) {
  color: #ff00ff;
}

.ai-content :deep(hr) {
  border: none;
  border-top: 2px dashed #004400;
  margin: 12px 0;
}

/* Sources - Quest Items */
.sources-list {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 2px dashed #004400;
}

.sources-title {
  font-size: 11px;
  color: #ffd700;
  font-weight: bold;
  text-transform: uppercase;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.source-item {
  background: #001100;
  border: 2px solid #004400;
  padding: 8px;
  margin-bottom: 6px;
}

.source-score {
  display: inline-block;
  background: #00ff00;
  color: #000;
  font-size: 10px;
  padding: 2px 6px;
  font-weight: bold;
}

.source-snippet {
  font-size: 12px;
  color: #888;
  margin: 6px 0 0;
  line-height: 1.4;
}

/* Loading State */
.loading-message {
  background: #1a1a2e !important;
}

.typing-indicator {
  color: #00ff00;
  font-family: 'Courier New', monospace;
  animation: blink 0.5s step-end infinite;
}

/* Input Area */
.input-area {
  padding: 16px;
  background: #000;
  border-top: 4px solid #00ff00;
  position: relative;
  z-index: 10;
}

.input-wrapper {
  max-width: 100%;
  display: flex;
  align-items: flex-end;
  background: #0a0a0a;
  border: 3px solid #00ff00;
  padding: 8px;
}

.input-wrapper:focus-within {
  box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
}

.input-prompt {
  color: #ff00ff;
  font-size: 18px;
  padding: 8px;
  font-weight: bold;
}

textarea {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  color: #00ff00;
  resize: none;
  max-height: 150px;
  min-height: 24px;
  line-height: 1.4;
}

textarea:focus { 
  outline: none; 
}

textarea::placeholder { 
  color: #004400; 
}

.send-btn {
  background: #00ff00;
  color: #000;
  border: 3px solid #004400;
  padding: 10px 16px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.1s;
  box-shadow: 3px 3px 0 #004400;
  text-transform: uppercase;
}

.send-btn:hover:not(:disabled) {
  background: #00ffaa;
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #004400;
}

.send-btn:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 0 0 0 #004400;
}

.send-btn:disabled {
  background: #004400;
  color: #002200;
  cursor: not-allowed;
  box-shadow: none;
}

/* Blocking State */
.blocking-state {
  text-align: center;
  padding: 60px 20px;
  color: #00ff00;
}

.blocking-state.error {
  color: #ff0000;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #004400;
  border-top-color: #00ff00;
  border-radius: 0;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

.loading-spinner.large {
  width: 60px;
  height: 60px;
  border-width: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-10px); }
  75% { transform: translateX(10px); }
}
</style>
