<template>
  <div class="detail">
    <div class="card">
      <div class="detail__header">
        <div>
          <h3 class="section-title">{{ detail?.filename }}</h3>
          <p class="detail__meta">
            {{ detail?.content_type || "未知类型" }} · {{ formatSize(detail?.file_size || 0) }} ·
            {{ formatTime(detail?.created_at || "") }}
          </p>
        </div>
        <span class="pill" :class="statusClass(detail?.status)">
          {{ statusText(detail?.status) }}
        </span>
      </div>

      <div class="detail__summary">
        <div>
          <p class="detail__label">智能摘要</p>
          <p class="detail__value">{{ "暂无摘要 (API pending)" }}</p>
        </div>
        <div>
          <p class="detail__label">向量化状态</p>
          <p class="detail__value">{{ statusText(detail?.status) }}</p>
        </div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <h3 class="section-title">文档预览</h3>
        <div class="preview" v-if="false">
          <!-- iframe :src="detail.previewUrl" title="preview" / -->
        </div>
        <div class="preview__empty">暂无预览 (API pending)</div>
      </div>
      <div class="card">
        <h3 class="section-title">相关问答</h3>
        <div v-if="qaRecords.length" class="qa-list">
          <div v-for="item in qaRecords" :key="item.id" class="qa-item">
            <p class="qa-item__q">Q: {{ item.question }}</p>
            <p class="qa-item__a">A: {{ item.answer }}</p>
          </div>
        </div>
        <div v-else class="preview__empty">暂无问答记录。</div>
      </div>
    </div>

    <div class="card">
      <h3 class="section-title">向量检索片段</h3>
      <div v-if="false" class="chunk-list">
        <!-- div v-for="chunk in detail.chunks" :key="chunk.id" class="chunk">
          <p>{{ chunk.content }}</p>
          <span>相似度 {{ chunk.score.toFixed(2) }}</span>
        </div -->
      </div>
      <div class="preview__empty">暂无检索片段 (API pending)</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";

import { useFilesStore } from "@/store/files";
import { useQaStore } from "@/store/qa";
import { formatSize, formatTime } from "@/utils/format";

const route = useRoute();
const filesStore = useFilesStore();
const qaStore = useQaStore();

const detail = computed(() => filesStore.detail);
const qaRecords = computed(() => qaStore.records.slice(0, 3));

const statusClass = (status?: number) => {
  if (status === 2) return "pill--success";
  if (status === 1) return "pill--warning";
  if (status === 3) return "pill--failed";
  return "";
};

const statusText = (status?: number) => {
  const map: Record<number, string> = {
    2: "已完成",
    1: "向量化中",
    0: "上传中",
    3: "失败",
    4: "已删除"
  };
  return map[status ?? -1] || "未知";
};

onMounted(async () => {
  const id = route.params.id as string;
  if (!id) return;
  await filesStore.loadDetail(id);
  await qaStore.loadHistory(id);
});
</script>

<style scoped>
.detail {
  display: grid;
  gap: 18px;
}

.detail__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.detail__meta {
  margin: 4px 0 0;
  color: var(--nl-muted);
}

.detail__summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--nl-border);
}

.detail__label {
  margin: 0;
  color: var(--nl-muted);
  font-size: 12px;
}

.detail__value {
  margin: 6px 0 0;
  font-weight: 500;
}

.preview {
  height: 320px;
}

.preview iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 12px;
}

.preview__empty {
  color: var(--nl-muted);
  padding: 24px 0;
}

.qa-list {
  display: grid;
  gap: 12px;
}

.qa-item__q {
  margin: 0;
  font-weight: 600;
}

.qa-item__a {
  margin: 6px 0 0;
  color: var(--nl-muted);
}

.chunk-list {
  display: grid;
  gap: 12px;
}

.chunk {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--nl-border);
  background: rgba(255, 255, 255, 0.7);
}

.chunk span {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: var(--nl-muted);
}

@media (max-width: 960px) {
  .detail__summary {
    grid-template-columns: 1fr;
  }
}
</style>
