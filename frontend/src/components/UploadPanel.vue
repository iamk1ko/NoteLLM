<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadChunk, listFiles } from '@/services/files'
import { useUploadStore } from '@/store/upload'
import { hashFile } from '@/utils/hash'

const uploadStore = useUploadStore()
const isPublic = ref(false)
const chunkSize = 5 * 1024 * 1024

const handleFiles = async (files: File[]) => {
  for (const file of files) {
    const taskId = `${file.name}-${file.size}-${Date.now()}`
    uploadStore.addTask({
      id: taskId,
      name: file.name,
      size: file.size,
      md5: '',
      totalChunks: 0,
      uploadedChunks: 0,
      progress: 0,
      status: 'waiting',
    })

    try {
      uploadStore.updateTask(taskId, { status: 'uploading' })
      const md5 = await hashFile(file)
      const totalChunks = Math.ceil(file.size / chunkSize)
      uploadStore.updateTask(taskId, { md5, totalChunks })

      let uploaded = 0
      for (let index = 0; index < totalChunks; index += 1) {
        const start = index * chunkSize
        const end = Math.min(start + chunkSize, file.size)
        const blob = file.slice(start, end)

        const result = await uploadChunk({
          file_md5: md5,
          chunk_index: index,
          total_chunks: totalChunks,
          chunk_size: blob.size,
          total_size: file.size,
          file_name: file.name,
          content_type: file.type || 'application/octet-stream',
          is_public: isPublic.value,
          file_chunk: new File([blob], file.name, {
            type: file.type || 'application/octet-stream',
          }),
        })

        if (!result.uploaded) {
          throw new Error(result.error || '上传失败')
        }

        uploaded += 1
        const progress = Math.round((uploaded / totalChunks) * 100)
        uploadStore.updateTask(taskId, {
          uploadedChunks: uploaded,
          progress,
        })
      }

      try {
        const fileList = await listFiles(1, 50, true)
        const match = fileList.items.find(
          (item) => item.etag === md5 && item.filename === file.name,
        )
        uploadStore.updateTask(taskId, { status: 'completed', fileId: match?.id })
      } catch {
        uploadStore.updateTask(taskId, { status: 'completed' })
      }
      ElMessage.success(`文件 ${file.name} 上传完成`)
    } catch {
      uploadStore.updateTask(taskId, {
        status: 'failed',
        error: '上传失败',
      })
      ElMessage.error(`文件 ${file.name} 上传失败`)
    }
  }
}

const onChange = async (file: File | undefined) => {
  if (!file) return
  await handleFiles([file])
}
</script>

<template>
  <div class="card">
    <div class="section-title">
      <h2>分片上传</h2>
      <span class="tag">后端校验</span>
    </div>
    <div class="table-header">
      <el-upload
        drag
        multiple
        :auto-upload="false"
        :show-file-list="false"
        :before-upload="() => false"
        :on-change="(file) => onChange(file.raw)"
      >
        <div class="el-upload__text">拖拽文件到此处，或点击上传</div>
        <div class="muted">支持大文件分片上传，自动计算 MD5</div>
      </el-upload>
      <el-switch v-model="isPublic" active-text="公开" inactive-text="私有" />
    </div>
  </div>
</template>
