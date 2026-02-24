<template>
  <div class="file-card card card--interactive" @click="emit('click')">
    <div class="file-card__header">
      <div class="file-icon" :class="fileType">
        {{ fileExt }}
      </div>
      <div class="status-indicator" :class="statusClass"></div>
    </div>

    <div class="file-card__body">
      <h3 class="file-name" :title="file.filename">{{ file.filename }}</h3>
      <p class="file-meta">
        {{ formatSize(file.file_size) }} · {{ formatTime(file.created_at) }}
      </p>
    </div>

    <div class="file-card__footer">
      <span class="pill" :class="statusPillClass">{{ statusText }}</span>
      <div class="actions" @click.stop>
        <button class="action-btn preview-btn" @click="emit('preview', String(file.id))" title="PREVIEW">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
        </button>
        <button class="action-btn delete-btn" @click="emit('delete', String(file.id))" title="DELETE">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { formatSize, formatTime } from '@/utils/format';
import type { FileItem } from '@/services/types';

/**
 * FileCard Component
 * ------------------
 * 文件展示卡片 (Pixel Art Style)
 * 展示文件的基本信息、状态指示灯和操作按钮
 */

const props = defineProps<{
  file: FileItem; // 文件数据对象
}>();

const emit = defineEmits<{
  (e: 'click'): void;
  (e: 'delete', id: string): void;
  (e: 'preview', id: string): void;
}>();

// 计算文件扩展名 (显示在图标中)
const fileExt = computed(() => {
  return props.file.filename.split('.').pop()?.toUpperCase() || 'FILE';
});

// 根据扩展名决定图标样式类
const fileType = computed(() => {
  const ext = props.file.filename.split('.').pop()?.toLowerCase();
  if (['pdf'].includes(ext || '')) return 'pdf';
  if (['doc', 'docx'].includes(ext || '')) return 'doc';
  if (['md', 'txt'].includes(ext || '')) return 'txt';
  return 'other';
});

// 状态指示灯样式 (CSS Class)
const statusClass = computed(() => {
  if (props.file.status === 2) return 'status-success'; // 2: Embedded/Ready
  if (props.file.status === 1) return 'status-vectorizing'; // 1: Uploaded (Vectorizing)
  if (props.file.status === 0) return 'status-processing'; // 0: Uploading
  if (props.file.status === 3) return 'status-failed'; // 3: Failed
  return 'status-unknown';
});

// 状态标签样式 (Pill Class)
const statusPillClass = computed(() => {
  if (props.file.status === 2) return 'pill--success';
  if (props.file.status === 1) return 'pill--warning';
  if (props.file.status === 0) return 'pill--processing';
  if (props.file.status === 3) return 'pill--failed';
  return 'pill--unknown';
});

// 状态显示文本 (Retro Text)
const statusText = computed(() => {
  const map: Record<number, string> = {
    2: '就绪',      // EMBEDDED
    1: '向量化中',   // UPLOADED (Pending Vectorization)
    0: '上传中',     // UPLOADING
    3: '失败',      // FAILED
    4: '已删除'      // DELETED
  };
  return map[props.file.status] || '未知';
});
</script>

<style scoped>
.file-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 240px;
  position: relative;
  overflow: hidden;
  border-width: 4px;
}

.file-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.file-icon {
  width: 48px;
  height: 48px;
  border: 4px solid black;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  color: black;
  background: white;
  box-shadow: 4px 4px 0px black;
  font-family: var(--font-display);
}

.file-icon.pdf { background: #ef4444; color: white; }
.file-icon.doc { background: #3b82f6; color: white; }
.file-icon.txt { background: #10b981; color: white; }

.status-indicator {
  width: 16px;
  height: 16px;
  border: 2px solid black;
  background: white;
  box-shadow: 2px 2px 0px black;
}
.status-success { background: #10b981; } /* Green */
.status-vectorizing { background: #f59e0b; animation: blink 1s step-end infinite; } /* Amber */
.status-processing { background: #3b82f6; animation: blink 0.5s step-end infinite; } /* Blue */
.status-failed { background: #ef4444; } /* Red */
.status-unknown { background: #9ca3af; }

.pill {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border: 1px solid black;
  text-transform: uppercase;
  font-family: var(--font-display);
}
.pill--success { background: #d1fae5; color: #065f46; }
.pill--warning { background: #fef3c7; color: #92400e; }
.pill--processing { background: #dbeafe; color: #1e40af; }
.pill--failed { background: #fee2e2; color: #991b1b; }
.pill--unknown { background: #f3f4f6; color: #374151; }

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
  100% { opacity: 1; }
}

.file-card__body {
  flex: 1;
}

.file-name {
  font-size: 16px;
  margin: 0 0 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
  font-family: var(--font-display);
  text-transform: uppercase;
}

.file-meta {
  font-size: 14px;
  color: var(--nl-text-secondary);
  margin: 0;
  font-family: var(--font-body);
}

.file-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 4px dashed var(--nl-border);
}

.actions {
  opacity: 1; /* Always visible in retro style */
}

.action-btn {
  background: transparent;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 4px;
  color: black;
  transition: all 0.1s;
  display: flex;
  box-shadow: none;
}

.action-btn:hover {
  background: #ef4444;
  color: white;
  border: 2px solid black;
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0px black;
}
</style>
