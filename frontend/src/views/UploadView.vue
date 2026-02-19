<script setup lang="ts">
import UploadPanel from '@/components/UploadPanel.vue'
import UploadQueue from '@/components/UploadQueue.vue'

const highlights = [
  { title: '分片策略', detail: '默认 5MB 切片，适配断点续传流程。' },
  { title: 'MD5 校验', detail: '前端计算文件 MD5，后端复用存储任务。' },
  { title: '任务队列', detail: '实时展示分片进度与失败提示。' },
]
</script>

<template>
  <div class="content-grid">
    <div class="card">
      <div class="section-title">
        <h2>上传说明</h2>
        <span class="tag">任务概览</span>
      </div>
      <div style="display: grid; gap: 12px">
        <div v-for="item in highlights" :key="item.title">
          <strong>{{ item.title }}</strong>
          <div class="muted">{{ item.detail }}</div>
        </div>
      </div>
    </div>
    <UploadPanel />
    <UploadQueue />
  </div>
</template>
