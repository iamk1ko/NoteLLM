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

      <div class="messages-container" ref="messagesRef" @click="handleMessagesClick">
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
          :key="`${msg.id}-${streamTick}`" 
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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useFilesStore } from '@/store/files';
import { useQaStore } from '@/store/qa';
import { formatSize, formatTime } from '@/utils/format';
import { createAutoScroll } from '@/utils/autoScroll';
import { communityService } from '@/services/community';
import { getFilePreview } from '@/services/files';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/atom-one-dark.css';
import { ElMessage } from 'element-plus';
import FilePreviewModal from '@/components/FilePreviewModal.vue';

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
});

// Override fence renderer to add code highlighting and copy button
md.renderer.rules.fence = function (tokens, idx, options, env, self) {
  const token = tokens[idx];
  const lang = token.info.trim();
  const code = token.content;
  
  let highlightedCode = '';
  if (lang && hljs.getLanguage(lang)) {
    try {
      highlightedCode = hljs.highlight(code, { language: lang, ignoreIllegals: true }).value;
    } catch (__) {
      highlightedCode = md.utils.escapeHtml(code);
    }
  } else {
    highlightedCode = md.utils.escapeHtml(code);
  }
  
  const encodedCode = encodeURIComponent(code);
  
  return `
    <div class="code-block-wrapper">
      <div class="code-block-header">
        <span class="code-lang">${lang || 'text'}</span>
        <button class="code-copy-btn" data-code="${encodedCode}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          COPY
        </button>
      </div>
      <pre class="hljs"><code class="language-${lang}">${highlightedCode}</code></pre>
    </div>
  `;
};

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

const handleMessagesClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  const btn = target.closest('.code-copy-btn');
  if (btn) {
    const code = decodeURIComponent(btn.getAttribute('data-code') || '');
    if (code) {
      copyToClipboard(code);
      const originalText = btn.innerHTML;
      btn.innerHTML = 'COPIED!';
      setTimeout(() => {
        btn.innerHTML = originalText;
      }, 2000);
    }
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
const { scrollToBottom, updateAutoScroll } = createAutoScroll({
  threshold: 120
});
const handleScroll = () => updateAutoScroll(messagesRef.value);
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
const scrollToBottomIfNeeded = () => scrollToBottom(messagesRef.value);

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

   // 统一由 store 处理流式输出
   try {
     await qaStore.sendQuestion(q, String(detail.value?.id));
   } catch (error) {
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
      vectorProgress.value += (100 - vectorProgress.value) * 0.2; // 加快进度条模拟
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
  }, 1000); // 从 2 秒缩短为 1 秒，适应更快的远程向量化API
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
  scrollToBottomIfNeeded();
}, { deep: true });

// --- Lifecycle ---
onMounted(async () => {
  const id = route.params.id as string;
  if (id) {
    // 串行加载防止并发竞争（也可改为Promise.all优化）
    await filesStore.loadDetail(id);
    await qaStore.loadHistory(id);
    scrollToBottomIfNeeded();
    
    // Check initial status for polling
    if (detail.value?.status === 1) {
      startPolling();
    }
  }
  if (messagesRef.value) {
    messagesRef.value.addEventListener('scroll', handleScroll, { passive: true });
  }
});

onUnmounted(() => {
  stopPolling();
  if (messagesRef.value) {
    messagesRef.value.removeEventListener('scroll', handleScroll);
  }
});
</script>

<style scoped>
/* ===== RETRO PIXAR THEME - Unified with NoteLLM Project ===== */

/* Chat Layout */
.chat-layout {
  display: flex;
  height: calc(100vh - 72px);
  background: var(--nl-bg);
  overflow: hidden;
  position: relative;
  margin: -40px;
  font-family: var(--font-body);
}

/* Sidebar - Notebook Panel */
.chat-sidebar {
  width: 320px;
  border-right: var(--nl-border-width) solid var(--nl-border);
  background: var(--nl-bg);
  display: flex;
  flex-direction: column;
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
  border-bottom: var(--nl-border-width) solid var(--nl-border);
  background: var(--nl-surface);
}

.sidebar-title {
  font-family: var(--font-display);
  font-size: 14px;
  color: var(--nl-text-main);
  font-weight: bold;
  text-transform: uppercase;
}

.sidebar-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
  background-image: linear-gradient(var(--nl-bg-grid) 1px, transparent 1px);
  background-size: 100% 24px;
}

/* Quest Card */
.notebook-card {
  text-align: center;
  margin-bottom: 24px;
  border: var(--nl-border-width) solid var(--nl-border);
  background: var(--nl-surface);
  padding: 20px;
  position: relative;
  box-shadow: var(--nl-shadow-solid);
}

.notebook-card::before {
  content: '>';
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  font-family: var(--font-display);
  font-size: 14px;
  background: var(--nl-bg);
  padding: 0 8px;
  color: var(--nl-primary);
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
  color: var(--nl-text-main);
}

.file-meta-lg {
  font-size: 14px;
  color: var(--nl-text-secondary);
  margin-bottom: 12px;
  font-family: var(--font-body);
}

.upload-time {
  font-size: 12px;
  color: var(--nl-text-secondary);
  margin-top: 8px;
  font-family: var(--font-body);
}

/* Status Pills - Unified Style */
.pill {
  display: inline-block;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: bold;
  text-transform: uppercase;
  border: var(--nl-border-width) solid var(--nl-border);
  margin: 4px 2px;
  font-family: var(--font-ui);
}

.pill--success {
  background: var(--nl-accent);
  color: white;
}

.pill--warning {
  background: var(--nl-warning);
  color: black;
}

.pill--failed {
  background: var(--nl-danger);
  color: white;
}

/* Sidebar Section */
.sidebar-section {
  margin-bottom: 24px;
  border: var(--nl-border-width) solid var(--nl-border);
  padding: 16px;
  background: var(--nl-surface);
  box-shadow: var(--nl-shadow-solid);
}

.sidebar-section h3 {
  font-size: 12px;
  margin-bottom: 12px;
  background: var(--nl-border);
  color: white;
  display: inline-block;
  padding: 2px 8px;
  font-family: var(--font-display);
}

.summary-text {
  font-size: 16px;
  line-height: 1.5;
  color: var(--nl-text-main);
  font-family: var(--font-body);
}

/* Action Buttons - Unified Style */
.btn {
  padding: 12px 16px;
  border: var(--nl-border-width) solid var(--nl-border);
  font-family: var(--font-ui);
  font-weight: bold;
  cursor: pointer;
  transition: all 0.1s;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  text-transform: uppercase;
  background: var(--nl-surface);
  color: var(--nl-text-main);
  box-shadow: var(--nl-shadow-solid);
  margin-bottom: 12px;
}

.btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: var(--nl-shadow-solid-hover);
  background: #fff9c4;
}

.btn:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
  background: #e5e5e5;
}

.btn-primary {
  background: var(--nl-primary);
  color: white;
}

.btn-secondary {
  background: var(--nl-accent);
  color: white;
}

.btn-outline {
  background: transparent;
  border-style: dashed;
  box-shadow: none;
}

.mr-2 { margin-right: 8px; }
.mb-3 { margin-bottom: 12px; }

.icon-btn {
  background: var(--nl-surface);
  border: var(--nl-border-width) solid var(--nl-border);
  cursor: pointer;
  padding: 6px;
  color: var(--nl-text-main);
  display: flex;
  box-shadow: 2px 2px 0 #000;
}

.icon-btn:hover {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
  background: var(--nl-secondary);
  color: white;
}

/* ===== MAIN CHAT AREA - RETRO TERMINAL ===== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--nl-bg);
  position: relative;
  font-family: var(--font-body);
}

.chat-header {
  height: 60px;
  border-bottom: var(--nl-border-width) solid var(--nl-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--nl-surface);
}

.header-title {
  font-size: 16px;
  color: var(--nl-text-main);
  font-family: var(--font-display);
}

.status-indicator {
  font-family: var(--font-ui);
  font-size: 14px;
  padding: 4px 12px;
  font-weight: bold;
  border: var(--nl-border-width) solid var(--nl-border);
}

.status-ready {
  background: var(--nl-accent);
  color: white;
}

.status-busy {
  background: var(--nl-warning);
  color: black;
}

.status-error {
  background: var(--nl-danger);
  color: white;
}

/* Messages Container */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Empty State */
.empty-chat {
  text-align: center;
  margin-top: 100px;
  color: var(--nl-text-secondary);
}

.empty-icon { font-size: 48px; margin-bottom: 16px; }

/* Message Wrapper */
.message-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 90%;
  padding: 16px;
  border: var(--nl-border-width) solid var(--nl-border);
}

/* User Message */
.message--user {
  align-self: flex-end;
  background: var(--nl-primary);
  color: white;
  box-shadow: var(--nl-shadow-solid);
}

.message--user .message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.message--user .user-avatar {
  width: 28px;
  height: 28px;
  background: white;
  border: 2px solid black;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
}

.message--user .message-time {
  font-size: 12px;
  color: rgba(255,255,255,0.8);
}

.message--user .copy-btn {
  background: transparent;
  border: none;
  color: rgba(255,255,255,0.8);
  cursor: pointer;
  padding: 4px 8px;
  margin-left: auto;
  opacity: 0;
  transition: opacity 0.2s;
}

.message--user:hover .copy-btn {
  opacity: 1;
}

.message-content {
  line-height: 1.5;
  font-size: 16px;
  word-wrap: break-word;
}

/* AI Message */
.message--ai {
  align-self: flex-start;
  background: var(--nl-surface);
  color: var(--nl-text-main);
  box-shadow: var(--nl-shadow-solid);
}

.message--ai .ai-avatar {
  width: 40px;
  height: 40px;
  background: var(--nl-secondary);
  color: white;
  border: var(--nl-border-width) solid var(--nl-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 12px;
  flex-shrink: 0;
  font-family: var(--font-display);
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
}

.message--ai .message-time {
  font-size: 12px;
  color: var(--nl-text-secondary);
}

.message--ai .copy-btn {
  background: transparent;
  border: none;
  color: var(--nl-text-secondary);
  cursor: pointer;
  padding: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.message--ai:hover .copy-btn {
  opacity: 1;
}

.copy-btn:hover {
  color: var(--nl-primary);
}

/* AI Content - Markdown Styles */
.ai-content {
  color: var(--nl-text-main);
  font-family: var(--font-body);
  line-height: 1.6;
  font-size: 16px;
}

.ai-content :deep(h1),
.ai-content :deep(h2),
.ai-content :deep(h3),
.ai-content :deep(h4),
.ai-content :deep(h5),
.ai-content :deep(h6) {
  color: var(--nl-text-main);
  margin: 16px 0 8px;
  font-weight: bold;
  font-family: var(--font-display);
}

.ai-content :deep(h1) { font-size: 20px; border-bottom: 2px solid black; padding-bottom: 4px; }
.ai-content :deep(h2) { font-size: 18px; }
.ai-content :deep(h3) { font-size: 16px; }

.ai-content :deep(p) {
  margin-bottom: 12px;
}

.ai-content :deep(ul),
.ai-content :deep(ol) {
  padding-left: 24px;
  margin-bottom: 12px;
}

.ai-content :deep(li) {
  margin-bottom: 4px;
}

.ai-content :deep(code) {
  background: var(--nl-bg-grid);
  padding: 2px 6px;
  font-family: 'Courier New', monospace;
  border: 1px solid black;
  color: var(--nl-danger); /* Give inline code a distinct color */
}

/* Custom Code Block Wrapper */
.ai-content :deep(.code-block-wrapper) {
  margin: 16px 0;
  border: var(--nl-border-width) solid var(--nl-border);
  box-shadow: 4px 4px 0px rgba(0,0,0,0.2);
  background: #282c34; /* Atom One Dark background */
  overflow: hidden;
}

.ai-content :deep(.code-block-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1e2227; /* Darker header */
  padding: 4px 12px;
  border-bottom: var(--nl-border-width) solid var(--nl-border);
}

.ai-content :deep(.code-lang) {
  color: #abb2bf;
  font-family: var(--font-display);
  font-size: 12px;
  text-transform: uppercase;
}

.ai-content :deep(.code-copy-btn) {
  background: transparent;
  border: none;
  color: #abb2bf;
  font-family: var(--font-ui);
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  transition: all 0.2s;
}

.ai-content :deep(.code-copy-btn:hover) {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.1);
}

.ai-content :deep(pre.hljs) {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
  background: transparent; /* Rely on wrapper background */
  color: #abb2bf; /* Default One Dark color */
  border: none; /* Remove old border */
}

.ai-content :deep(pre code) {
  background: transparent;
  border: none;
  padding: 0;
  color: inherit;
  font-family: 'Courier New', monospace;
  font-size: 15px;
  line-height: 1.5;
}

.ai-content :deep(blockquote) {
  border-left: 4px solid var(--nl-secondary);
  padding-left: 16px;
  margin: 12px 0;
  color: var(--nl-text-secondary);
  font-style: italic;
}

.ai-content :deep(a) {
  color: var(--nl-primary);
  text-decoration: underline;
}

.ai-content :deep(a:hover) {
  color: var(--nl-secondary);
}

.ai-content :deep(hr) {
  border: none;
  border-top: 2px dashed black;
  margin: 16px 0;
}

/* Sources */
.sources-list {
  margin-top: 16px;
  padding-top: 16px;
  border-top: var(--nl-border-width) dashed var(--nl-border);
}

.sources-title {
  font-size: 12px;
  color: var(--nl-text-main);
  font-weight: bold;
  margin-bottom: 8px;
  font-family: var(--font-display);
  text-transform: uppercase;
}

.source-item {
  background: var(--nl-bg);
  border: var(--nl-border-width) solid var(--nl-border);
  padding: 12px;
  margin-bottom: 8px;
}

.source-score {
  display: inline-block;
  background: var(--nl-primary);
  color: white;
  font-size: 12px;
  padding: 2px 8px;
  font-weight: bold;
  margin-bottom: 8px;
}

.source-snippet {
  font-size: 14px;
  color: var(--nl-text-secondary);
  line-height: 1.4;
  margin: 0;
}

/* Loading State */
.loading-message {
  background: var(--nl-surface) !important;
}

.typing-indicator {
  color: var(--nl-text-secondary);
  font-family: var(--font-body);
}

/* Input Area */
.input-area {
  padding: 16px;
  background: var(--nl-surface);
  border-top: var(--nl-border-width) solid var(--nl-border);
}

.input-wrapper {
  max-width: 100%;
  display: flex;
  align-items: flex-end;
  background: var(--nl-bg);
  border: var(--nl-border-width) solid var(--nl-border);
  padding: 8px;
}

.input-wrapper:focus-within {
  box-shadow: var(--nl-shadow-solid);
}

.input-prompt {
  color: var(--nl-secondary);
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
  color: var(--nl-text-main);
  resize: none;
  max-height: 200px;
  min-height: 24px;
}

textarea:focus { outline: none; }
textarea::placeholder { color: var(--nl-text-secondary); }

.send-btn {
  background: var(--nl-primary);
  color: white;
  border: var(--nl-border-width) solid var(--nl-border);
  padding: 10px 20px;
  font-family: var(--font-ui);
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.1s;
  box-shadow: var(--nl-shadow-solid);
  text-transform: uppercase;
}

.send-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: var(--nl-shadow-solid-hover);
  background: #4338ca;
}

.send-btn:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 0 0 0 #000;
}

.send-btn:disabled {
  background: #e5e5e5;
  color: #999;
  cursor: not-allowed;
  box-shadow: none;
}

/* Blocking State */
.blocking-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--nl-text-main);
}

.blocking-state.error {
  color: var(--nl-danger);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--nl-bg-grid);
  border-top-color: var(--nl-primary);
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
}
</style>
