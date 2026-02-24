<template>
  <div class="community-container">
    <!-- 顶部导航栏 / Header -->
    <header class="community-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="icon">🌐</span> 社区广场_COMMUNITY
        </h1>
        <p class="page-subtitle">探索·分享·Fork知识库 // EXPLORE_SHARED_KNOWLEDGE</p>
      </div>

      <!-- 搜索栏 / Search Bar -->
      <div class="search-box">
        <span class="search-prompt">> find</span>
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="输入关键词..." 
          @keyup.enter="fetchShares"
        />
        <button class="btn-retro" @click="fetchShares">EXEC</button>
      </div>
    </header>

    <!-- 过滤器与工具栏 / Filter Toolbar -->
    <div class="toolbar">
      <div class="filter-group">
        <button 
          class="tab-btn" 
          :class="{ active: currentFilter === 'Latest' }"
          @click="currentFilter = 'Latest'"
        >
          [ 最新发布 ]
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: currentFilter === 'Popular' }"
          @click="currentFilter = 'Popular'"
        >
          [ 热门榜单 ]
        </button>
      </div>
      
      <div class="stats-display">
        STATUS: <span class="blink">ONLINE</span> | ITEMS: {{ shares.length }}
      </div>
    </div>

    <!-- 内容区域 / Content Grid -->
    <main class="content-area">
      <!-- 加载状态 / Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="loading-text">正在从网络获取数据...</div>
        <div class="loading-bar">
          <div class="loading-progress"></div>
        </div>
      </div>

      <!-- 空状态 / Empty State -->
      <div v-else-if="shares.length === 0" class="empty-state">
        <div class="pixel-art">¯\_(ツ)_/¯</div>
        <p>没有找到相关数据 / NO_DATA_FOUND</p>
      </div>

      <!-- 分享列表 / Grid -->
      <div v-else class="card-grid">
        <div 
          v-for="share in shares" 
          :key="share.id" 
          class="retro-card"
        >
          <!-- 卡片头部：用户信息 -->
          <div class="card-header">
            <div class="user-badge">
              <div class="avatar-block">{{ (share.user_name || 'U')[0].toUpperCase() }}</div>
              <span class="username">@{{ share.user_name }}</span>
            </div>
            <span class="date-tag">{{ formatDate(share.create_time) }}</span>
          </div>

          <!-- 卡片主体：内容信息 -->
          <div class="card-body">
            <h3 class="card-title" :title="share.title">{{ share.title }}</h3>
            <p class="card-desc">{{ share.description || '暂无描述信息...' }}</p>
            
            <!-- 标签组 -->
            <div class="tags-row">
              <span v-for="tag in share.tags" :key="tag" class="retro-tag">#{{ tag }}</span>
            </div>
          </div>

          <!-- 卡片底部：操作栏 -->
          <div class="card-footer">
            <div class="metrics">
              <span class="metric-item" title="浏览量">
                👁 {{ share.view_count }}
              </span>
              <button 
                class="metric-btn" 
                :class="{ 'is-liked': share.is_liked }"
                @click="toggleLike(share)"
                title="点赞"
              >
                {{ share.is_liked ? '♥' : '♡' }} {{ share.like_count }}
              </button>
            </div>

            <button class="action-btn" @click="forkShare(share)">
              <span>⑂ FORK</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { communityService, type CommunityShare } from '@/services/community';

/**
 * CommunityView 组件逻辑
 * ---------------------
 * 负责展示社区分享列表，提供搜索、筛选、点赞和 Fork 功能。
 * 数据目前使用 Mock 模拟，后续对接真实后端接口。
 */

// --- 响应式状态 / State ---
const loading = ref(false);         // 加载状态
const searchQuery = ref('');        // 搜索关键词
const currentFilter = ref('Latest'); // 当前过滤器：Latest | Popular
const shares = ref<CommunityShare[]>([]); // 分享列表数据

// --- Mock 数据生成器 / Mock Data Generator ---
// 模拟后端返回的数据结构
const generateMockData = () => {
  const mockShares: CommunityShare[] = [
    {
      id: 101,
      title: "Python Web 开发面试题集锦 (2024版)",
      description: "整理了包含 FastAPI, Django, Flask 在内的常见面试题，并附带了 RAG 相关的回答示例。非常适合准备面试的同学。",
      tags: ["Python", "面试", "后端"],
      user_id: 1,
      user_name: "TechGuru",
      view_count: 1240,
      like_count: 45,
      fork_count: 12,
      create_time: "2024-02-20T10:00:00",
      is_liked: false
    },
    {
      id: 102,
      title: "公司新员工入职手册问答助手",
      description: "基于公司最新的 Employee Handbook PDF 生成的问答助手，可以直接询问关于休假、报销流程等问题。",
      tags: ["HR", "入职", "行政"],
      user_id: 2,
      user_name: "HR_Admin",
      view_count: 56,
      like_count: 8,
      fork_count: 3,
      create_time: "2024-02-22T14:30:00",
      is_liked: true
    },
    {
      id: 103,
      title: "DeepSeek 论文精读笔记",
      description: "对 DeepSeek-V3 论文的深度解析，包含关键架构图和公式推导的个人理解。",
      tags: ["AI", "LLM", "论文"],
      user_id: 3,
      user_name: "AI_Researcher",
      view_count: 3400,
      like_count: 128,
      fork_count: 56,
      create_time: "2024-02-23T09:15:00",
      is_liked: false
    },
    {
      id: 104,
      title: "Rust 语言圣经学习笔记",
      description: "记录了从入门到放弃再到精通的过程，重点记录了所有权机制的理解。",
      tags: ["Rust", "编程", "笔记"],
      user_id: 4,
      user_name: "Rustacean",
      view_count: 890,
      like_count: 67,
      fork_count: 5,
      create_time: "2024-02-24T11:20:00",
      is_liked: false
    }
  ];
  
  // 简单的本地过滤模拟
  if (searchQuery.value) {
    return mockShares.filter(s => s.title.includes(searchQuery.value) || s.tags.includes(searchQuery.value));
  }
  
  // 简单的排序模拟
  if (currentFilter.value === 'Popular') {
    return mockShares.sort((a, b) => b.like_count - a.like_count);
  }
  
  return mockShares;
};

// --- 方法 / Methods ---

// 获取分享列表
const fetchShares = async () => {
  loading.value = true;
  shares.value = [];
  try {
    const res = await communityService.getShares({ 
      page: 1, 
      size: 20, 
      sort: currentFilter.value === 'Popular' ? 'popular' : 'latest',
      tag: searchQuery.value || undefined
    });
    // Adjust based on actual client response structure
    // If client.get returns the data payload directly:
    shares.value = res.items || [];
  } catch (error) {
    console.error("Failed to load shares", error);
    shares.value = [];
  } finally {
    loading.value = false;
  }
};

// 格式化日期
const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${(d.getMonth()+1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
};

// 点赞/取消点赞
const toggleLike = async (share: CommunityShare) => {
  const action = share.is_liked ? 'unlike' : 'like';
  // Optimistic update
  share.is_liked = !share.is_liked;
  share.like_count += action === 'like' ? 1 : -1;
  
  try {
    const res = await communityService.likeShare(share.id, action);
    // Sync with server count if needed
    if (res && typeof res.like_count === 'number') {
      share.like_count = res.like_count;
    }
  } catch (e) {
    // Revert on failure
    share.is_liked = !share.is_liked;
    share.like_count += action === 'like' ? -1 : 1;
    console.error("Like failed", e);
  }
};

// Fork (转存) 分享
const forkShare = async (share: CommunityShare) => {
  const confirmed = confirm(`[系统提示]\n确定要将 "${share.title}" 转存到你的个人空间吗？\n这将复制文档和对话历史。`);
  if (confirmed) {
    try {
      await communityService.forkShare(share.id);
      share.fork_count++;
      alert("✅ 转存成功！\n你可以前往【文档库】查看已转存的内容。");
    } catch (e) {
      console.error("Fork failed", e);
      alert("❌ 转存失败，请稍后重试。");
    }
  }
};

// --- 生命周期与监听 / Lifecycle & Watchers ---

onMounted(() => {
  fetchShares();
});

// 监听筛选条件变化，自动重新加载
watch([currentFilter], () => {
  fetchShares();
});

</script>

<style scoped>
/* 
  主题变量定义 
  注意：这里直接使用硬编码颜色以确保与 ChatView 风格一致，
  也可以提取到全局 CSS 变量中。
*/
.community-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f3f4f6; /* 浅灰底色 */
  font-family: 'Courier New', Courier, monospace; /* 强制等宽字体 */
  padding: 20px;
  overflow: hidden;
}

/* --- Header 样式 --- */
.community-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 4px solid black;
}

.page-title {
  font-size: 28px;
  font-weight: 900;
  color: black;
  text-transform: uppercase;
  letter-spacing: -1px;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon {
  font-size: 32px;
}

.page-subtitle {
  color: #555;
  font-size: 14px;
  margin-top: 4px;
  font-weight: bold;
}

/* --- 搜索框样式 --- */
.search-box {
  display: flex;
  align-items: center;
  background: white;
  border: 4px solid black;
  box-shadow: 6px 6px 0px rgba(0,0,0,0.2);
  padding: 4px 8px;
  height: 48px;
}

.search-prompt {
  color: #ec4899; /* Pink */
  font-weight: bold;
  margin-right: 8px;
}

.search-box input {
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 16px;
  width: 240px;
  background: transparent;
}

.btn-retro {
  background: black;
  color: #33ff00; /* Terminal Green */
  border: none;
  padding: 6px 12px;
  font-family: inherit;
  font-weight: bold;
  cursor: pointer;
  transition: transform 0.1s;
}

.btn-retro:hover {
  transform: scale(1.05);
  color: white;
}

/* --- 工具栏样式 --- */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.filter-group {
  display: flex;
  gap: 16px;
}

.tab-btn {
  background: transparent;
  border: none;
  font-family: inherit;
  font-size: 16px;
  font-weight: bold;
  color: #888;
  cursor: pointer;
  padding: 4px 8px;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: black;
}

.tab-btn.active {
  color: black;
  background: #33ff00; /* 高亮绿 */
  box-shadow: 4px 4px 0px black;
  border: 2px solid black;
  transform: translate(-2px, -2px);
}

.stats-display {
  font-size: 12px;
  font-weight: bold;
  background: black;
  color: #33ff00;
  padding: 4px 8px;
}

.blink {
  animation: blink 1s step-end infinite;
}

@keyframes blink { 50% { opacity: 0; } }

/* --- 内容区域样式 --- */
.content-area {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px; /* 给滚动条留空 */
}

/* Grid 布局 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
  padding-bottom: 40px;
}

/* --- 卡片样式 (核心复古风格) --- */
.retro-card {
  background: white;
  border: 4px solid black;
  padding: 0;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
}

.retro-card:hover {
  transform: translate(-4px, -4px);
  box-shadow: 8px 8px 0px black;
  z-index: 10;
}

.card-header {
  background: #f0f0f0;
  border-bottom: 2px solid black;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar-block {
  width: 24px;
  height: 24px;
  background: black;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 12px;
}

.username {
  font-weight: bold;
  font-size: 14px;
}

.date-tag {
  font-size: 12px;
  color: #666;
  background: #e5e7eb;
  padding: 2px 4px;
  border: 1px solid #999;
}

.card-body {
  padding: 16px;
  flex: 1; /* 撑开高度 */
  border-bottom: 2px solid black;
}

.card-title {
  font-size: 18px;
  font-weight: 800;
  margin: 0 0 12px 0;
  line-height: 1.4;
  /* 限制标题行数 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-desc {
  font-size: 14px;
  color: #444;
  margin-bottom: 16px;
  line-height: 1.5;
  /* 限制描述行数 */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 4.5em; /* Fallback height */
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.retro-tag {
  font-size: 12px;
  background: white;
  border: 1px solid black;
  padding: 2px 6px;
  color: black;
  box-shadow: 2px 2px 0px #ccc;
}

/* 卡片底部 */
.card-footer {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
}

.metrics {
  display: flex;
  gap: 12px;
  font-size: 14px;
  font-weight: bold;
}

.metric-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-weight: bold;
  padding: 0;
  transition: transform 0.1s;
}

.metric-btn:hover {
  transform: scale(1.2);
}

.metric-btn.is-liked {
  color: #ec4899; /* Pink liked state */
}

.action-btn {
  background: #ec4899; /* Pink */
  color: white;
  border: 2px solid black;
  padding: 6px 12px;
  font-family: inherit;
  font-weight: bold;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 2px 2px 0px black;
  transition: all 0.1s;
}

.action-btn:hover {
  background: #33ff00; /* Green hover */
  color: black;
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0px black;
}

.action-btn:active {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0px black;
}

/* --- 加载与空状态 --- */
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  text-align: center;
}

.loading-bar {
  width: 200px;
  height: 20px;
  border: 2px solid black;
  margin-top: 16px;
  padding: 2px;
}

.loading-progress {
  height: 100%;
  background: #33ff00;
  width: 50%;
  animation: progress 2s infinite linear;
}

@keyframes progress {
  0% { width: 0%; margin-left: 0; }
  50% { width: 100%; margin-left: 0; }
  51% { width: 0%; margin-left: 100%; }
  100% { width: 0%; margin-left: 0; }
}

.pixel-art {
  font-size: 48px;
  font-family: monospace;
  margin-bottom: 16px;
}

/* 滚动条美化 */
.content-area::-webkit-scrollbar {
  width: 12px;
}
.content-area::-webkit-scrollbar-track {
  background: #e5e5e5;
  border-left: 2px solid black;
}
.content-area::-webkit-scrollbar-thumb {
  background: black;
  border: 2px solid #e5e5e5;
}
</style>