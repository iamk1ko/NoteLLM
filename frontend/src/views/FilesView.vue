<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useFilesStore } from '@/store/files'
import { listFiles, deleteFile } from '@/services/files'
import { formatBytes, formatDateTime, formatStatus } from '@/utils/format'
import StatusTag from '@/components/StatusTag.vue'

const filesStore = useFilesStore()

const loadFiles = async (page = 1) => {
  try {
    filesStore.setLoading(true)
    const payload = await listFiles(page, filesStore.size, true)
    filesStore.setList(payload)
  } catch {
    ElMessage.error('文件列表加载失败')
  } finally {
    filesStore.setLoading(false)
  }
}

const handleDelete = async (fileId: number) => {
  try {
    await deleteFile(fileId)
    ElMessage.success('文件已删除')
    await loadFiles(filesStore.page)
  } catch {
    ElMessage.error('文件删除失败')
  }
}

onMounted(() => {
  loadFiles()
})
</script>

<template>
  <div class="content-grid">
    <div class="card">
      <div class="section-title">
        <h2>文件列表</h2>
        <span class="tag">向量化状态</span>
      </div>
      <el-table v-loading="filesStore.loading" :data="filesStore.items" style="width: 100%">
        <el-table-column prop="filename" label="文件" min-width="220" />
        <el-table-column label="大小" width="140">
          <template #default="scope">
            <span class="muted">{{ formatBytes(scope.row.file_size) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="140">
          <template #default="scope">
            <StatusTag v-bind="formatStatus(scope.row.status)" />
          </template>
        </el-table-column>
        <el-table-column label="公开" width="90">
          <template #default="scope">
            <span class="muted">{{ scope.row.is_public ? '是' : '否' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="180">
          <template #default="scope">
            <span class="muted">{{ formatDateTime(scope.row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="scope">
            <el-button size="small" type="danger" plain @click="handleDelete(scope.row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 16px; display: flex; justify-content: flex-end">
        <el-pagination
          background
          layout="prev, pager, next"
          :page-size="filesStore.size"
          :current-page="filesStore.page"
          :total="filesStore.total"
          @current-change="loadFiles"
        />
      </div>
    </div>
  </div>
</template>
