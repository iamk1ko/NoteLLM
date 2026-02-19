<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { checkHealth, getInfraDemo } from '@/services/system'

const route = useRoute()
const healthStatus = ref('检测中')
const infraStatus = ref('待检测')

const navItems = [
  { path: '/upload', label: '文件上传', detail: '分片上传与进度' },
  { path: '/files', label: '文件列表', detail: '向量化状态' },
  { path: '/search', label: '检索验证', detail: '会话与消息' },
]

const activePath = computed(() => route.path)

const loadHealth = async () => {
  try {
    const health = await checkHealth()
    healthStatus.value = health.status
  } catch {
    healthStatus.value = '异常'
    ElMessage.error('健康检查失败')
  }
}

const loadInfra = async () => {
  try {
    const infra = await getInfraDemo()
    infraStatus.value = infra.redis && infra.minio_temp_bucket_exists ? '可用' : '异常'
  } catch {
    infraStatus.value = '异常'
    ElMessage.error('基础设施检查失败')
  }
}

onMounted(() => {
  loadHealth()
  loadInfra()
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <img src="@/assets/brand.svg" alt="RAG" width="54" height="54" />
        <div>
          <div class="brand-title">RAG 流程验证台</div>
          <div class="brand-subtitle">FastAPI + Vue3 验证前端</div>
        </div>
      </div>
      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="sidebar-link"
          :class="{ active: activePath === item.path }"
        >
          <div>
            <div>{{ item.label }}</div>
            <div class="brand-subtitle">{{ item.detail }}</div>
          </div>
        </router-link>
      </nav>
      <div class="sidebar-card">
        <div>健康检查：{{ healthStatus }}</div>
        <div>基础设施：{{ infraStatus }}</div>
      </div>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="topbar-title">
          <h1>{{ navItems.find((item) => item.path === activePath)?.label || '控制台' }}</h1>
          <span>对接 /api/v1 接口，快速回归核心业务流程</span>
        </div>
        <div class="status-pill">API: {{ healthStatus }}</div>
      </header>
      <router-view />
    </main>
  </div>
</template>
