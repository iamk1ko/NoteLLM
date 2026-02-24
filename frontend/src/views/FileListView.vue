<template>
  <div class="dashboard-container">
    <div class="header">
      <h1 class="page-title">> 文档归档_</h1>
      <div class="header-actions">
        <div class="search-box">
          <span class="prompt">$</span>
          <input 
            v-model="keyword" 
            type="text" 
            placeholder="搜索文档..." 
            class="search-input"
          />
        </div>
        <button class="pixel-btn" @click="goUpload">
          <span class="icon">+</span>
          上传新文件
        </button>
      </div>
    </div>

    <div class="grid-cards fade-in">
      <!-- Upload Card -->
      <div class="upload-card card" @click="goUpload">
        <div class="upload-content">
          <div class="upload-icon-box">
            <span class="pixel-icon">+</span>
          </div>
          <h3>新文件</h3>
          <p>[PDF/MD/TXT]</p>
        </div>
      </div>

      <!-- File Cards -->
      <FileCard 
        v-for="file in filteredFiles" 
        :key="file.id" 
        :file="file"
        @click="goChat(file.id)"
        @preview="handlePreview"
        @delete="confirmDelete"
      />
    </div>

    <div v-if="loading" class="loading-state">
      <div class="flow-loader">
        <div class="flow-dot" v-for="n in 7" :key="n"></div>
      </div>
      <p>数据加载中...</p>
    </div>

    <div v-if="!loading && filteredFiles.length === 0" class="empty-state">
      <p>[ 空空如也 ]</p>
      <p>上传文件以开始</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useFilesStore } from '@/store/files';
import { deleteFile, getFilePreview } from '@/services/files';
import FileCard from '@/components/FileCard.vue';
import { ElMessage, ElMessageBox } from 'element-plus';

/**
 * FileListView Component
 * ----------------------
 * 文档库列表页
 * 展示所有已上传的文档，提供搜索、删除和跳转到上传页的入口
 */

const router = useRouter();
const filesStore = useFilesStore();
const keyword = ref(''); // 搜索关键词

const loading = computed(() => filesStore.loading);
const files = computed(() => filesStore.list); // 从Store获取文件列表

// 计算属性：根据关键词过滤文件列表 (前端过滤)
const filteredFiles = computed(() => {
  if (!keyword.value) return files.value;
  return files.value.filter(f => f.filename.toLowerCase().includes(keyword.value.toLowerCase()));
});

// 跳转
const goUpload = () => router.push('/upload');
const goChat = (id: string) => router.push(`/chat/${id}`);

/**
 * 预览文件 (Preview File)
 * 获取MinIO预签名链接并打开新标签页
 */
const handlePreview = async (id: string) => {
  try {
    const url = await getFilePreview(id);
    if (url) {
      window.open(url, '_blank');
    } else {
      ElMessage.warning('无法获取预览链接');
    }
  } catch (e) {
    ElMessage.error('获取预览失败');
  }
};

/**
 * 确认删除操作 (Confirm Delete)
 * 弹出确认框，用户确认后调用后端删除接口
 */
const confirmDelete = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定要永久删除此文件吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
      customClass: 'pixel-msg-box' // 使用自定义复古样式
    });
    
    // 执行删除
    await deleteFile(id);
    // 重新加载列表
    await filesStore.loadFiles();
    ElMessage.success('文件已删除');
  } catch (e) {
    // 用户取消删除
  }
};

// 页面挂载时自动加载文件列表
onMounted(() => {
  filesStore.loadFiles();
});
</script>

<style scoped>
.dashboard-container {
  max-width: 100%;
  margin: 0;
  padding: 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
  border-bottom: 4px solid var(--nl-border);
  padding-bottom: 20px;
  flex-wrap: wrap;
  gap: 20px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 24px;
  color: var(--nl-text-main);
  text-shadow: 2px 2px 0px rgba(0,0,0,0.1);
}

.header-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}

.search-box {
  display: flex;
  align-items: center;
  background: var(--nl-surface);
  border: 2px solid var(--nl-border);
  padding: 4px 12px;
  box-shadow: 4px 4px 0px var(--nl-border);
}

.prompt {
  font-family: var(--font-display);
  color: var(--nl-primary);
  margin-right: 8px;
  font-weight: bold;
}

.search-input {
  border: none;
  background: transparent;
  font-family: var(--font-body);
  font-size: 18px;
  width: 240px;
  color: var(--nl-text-main);
  text-transform: uppercase;
}

.search-input:focus {
  outline: none;
}

.search-input::placeholder {
  color: var(--nl-text-secondary);
}

.pixel-btn {
  font-family: var(--font-display);
  font-size: 14px;
  background: var(--nl-primary);
  color: white;
  border: 2px solid var(--nl-border);
  padding: 10px 20px;
  cursor: pointer;
  box-shadow: 4px 4px 0px var(--nl-border);
  transition: all 0.1s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.pixel-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px var(--nl-border);
  background: #4338ca;
}

.pixel-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 0px 0px 0px var(--nl-border);
}

.icon {
  font-size: 16px;
  line-height: 1;
}

/* Upload Card Special Style */
.upload-card {
  border: 4px dashed var(--nl-border);
  background: var(--nl-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 220px;
  cursor: pointer;
  transition: all 0.1s;
  box-shadow: none; /* Override default card shadow for dashed style */
}

.upload-card:hover {
  border-color: var(--nl-primary);
  background: #f0fdf4;
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0px var(--nl-border);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon-box {
  width: 48px;
  height: 48px;
  background: var(--nl-primary);
  border: 2px solid var(--nl-border);
  display: flex;
  align-items: center;
  justify-content: center;
}

.pixel-icon {
  font-family: var(--font-display);
  font-size: 24px;
  color: white;
}

.upload-card h3 {
  font-family: var(--font-display);
  font-size: 16px;
  margin: 0;
  color: var(--nl-text-main);
}

.upload-card p {
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--nl-text-secondary);
  margin: 0;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 60px;
  font-family: var(--font-display);
  color: var(--nl-text-secondary);
}

.flow-loader {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin: 0 auto 20px;
  height: 20px;
  align-items: center;
}

.flow-dot {
  width: 12px;
  height: 12px;
  background: var(--nl-primary);
  border: 2px solid var(--nl-border);
  box-shadow: 2px 2px 0px var(--nl-border);
  animation: flow 1.4s ease-in-out infinite;
}

/* Creating the wave effect with staggered delays */
.flow-dot:nth-child(1) { animation-delay: 0.0s; }
.flow-dot:nth-child(2) { animation-delay: 0.1s; }
.flow-dot:nth-child(3) { animation-delay: 0.2s; }
.flow-dot:nth-child(4) { animation-delay: 0.3s; }
.flow-dot:nth-child(5) { animation-delay: 0.4s; }
.flow-dot:nth-child(6) { animation-delay: 0.5s; }
.flow-dot:nth-child(7) { animation-delay: 0.6s; }

@keyframes flow {
  0%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  50% {
    transform: translateY(-8px);
    opacity: 1;
    background-color: #4338ca; /* Slightly darker purple for emphasis */
  }
}
</style>
