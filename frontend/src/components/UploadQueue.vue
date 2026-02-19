<script setup lang="ts">
import { computed } from 'vue'
import { useUploadStore } from '@/store/upload'
import { formatBytes } from '@/utils/format'
import StatusTag from './StatusTag.vue'

const uploadStore = useUploadStore()
const tasks = computed(() => uploadStore.tasks)

const statusLabel = (status: string) => {
  switch (status) {
    case 'waiting':
      return { label: '等待中', type: 'waiting' }
    case 'uploading':
      return { label: '上传中', type: 'waiting' }
    case 'completed':
      return { label: '完成', type: 'success' }
    case 'failed':
      return { label: '失败', type: 'error' }
    default:
      return { label: '未知', type: 'waiting' }
  }
}
</script>

<template>
  <div class="card">
    <div class="section-title">
      <h2>上传队列</h2>
      <span class="tag">实时进度</span>
    </div>
    <el-table :data="tasks" style="width: 100%">
      <el-table-column prop="name" label="文件" min-width="200" />
      <el-table-column label="大小" width="120">
        <template #default="scope">
          <span class="muted">{{ formatBytes(scope.row.size) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="进度" min-width="220">
        <template #default="scope">
          <el-progress :percentage="scope.row.progress" :stroke-width="10" />
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="scope">
          <StatusTag v-bind="statusLabel(scope.row.status)" />
        </template>
      </el-table-column>
      <el-table-column label="文件ID" width="120">
        <template #default="scope">
          <span class="muted">{{ scope.row.fileId ?? '-' }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
