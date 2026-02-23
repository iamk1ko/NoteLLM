<template>
  <div class="export">
    <div class="card export__panel">
      <h3 class="section-title">问答记录导出</h3>
      <p class="export__desc">将选定文件的问答记录导出为 PDF 归档。</p>

      <el-select v-model="fileId" placeholder="选择文件" clearable style="width: 260px">
        <el-option
          v-for="item in files"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </el-select>

      <el-input
        v-model="range"
        placeholder="导出范围，例如 2025-01-01~2025-02-01"
        style="margin-top: 12px"
      />

      <div class="export__actions">
        <el-button type="primary" :loading="loading" @click="handleExport">
          生成 PDF
        </el-button>
        <el-button @click="reset">清空</el-button>
      </div>

      <div v-if="exported" class="export__result">
        <el-alert title="导出任务已提交" type="success" show-icon />
      </div>
    </div>

    <div class="card export__tips">
      <h3 class="section-title">导出说明</h3>
      <ul>
        <li>支持按文件或时间范围导出问答记录。</li>
        <li>后端会生成 PDF 并返回文件流。</li>
        <li>导出完成后可进行本地保存或分享。</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import { exportQaPdf } from "@/services/export";
import { useFilesStore } from "@/store/files";

const filesStore = useFilesStore();

const fileId = ref<string | undefined>(undefined);
const range = ref("");
const exported = ref(false);
const loading = ref(false);

const files = computed(() => filesStore.list);

const handleExport = async () => {
  try {
    loading.value = true;
    const blob = await exportQaPdf({ fileId: fileId.value, range: range.value || undefined });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "NoteLLM-QA.pdf";
    a.click();
    URL.revokeObjectURL(url);
    exported.value = true;
  } catch (error) {
    ElMessage.error("导出失败，请稍后重试");
  } finally {
    loading.value = false;
  }
};

const reset = () => {
  fileId.value = undefined;
  range.value = "";
};

onMounted(async () => {
  await filesStore.loadFiles();
});
</script>

<style scoped>
.export {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.export__panel {
  display: grid;
  gap: 12px;
}

.export__desc {
  margin: 0;
  color: var(--nl-muted);
}

.export__actions {
  display: flex;
  gap: 12px;
}

.export__tips ul {
  padding-left: 18px;
  margin: 0;
  color: var(--nl-muted);
}

.export__result {
  margin-top: 8px;
}

@media (max-width: 960px) {
  .export {
    grid-template-columns: 1fr;
  }
}
</style>
