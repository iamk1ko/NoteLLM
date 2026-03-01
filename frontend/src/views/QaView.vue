<template>
  <div class="qa">
    <div class="card qa__panel">
      <div class="qa__header">
        <h3 class="section-title">智能问答</h3>
        <el-select v-model="fileId" placeholder="选择文件" clearable style="width: 220px">
          <el-option
            v-for="item in files"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </div>

      <el-input
        v-model="question"
        type="textarea"
        :rows="4"
        placeholder="请输入你想问的问题"
      />

      <div class="qa__actions">
        <el-button type="primary" :loading="loading" @click="submitQuestion">发送问题</el-button>
        <el-button @click="reset">清空</el-button>
      </div>
    </div>

    <div class="card qa__history" ref="historyRef">
      <h3 class="section-title">问答记录</h3>
      <div v-if="records.length" class="qa__list">
        <div v-for="item in records" :key="item.id" class="qa__item">
          <p class="qa__q">Q: {{ item.question }}</p>
          <p class="qa__a">A: {{ item.answer }}</p>
          <div class="qa__sources" v-if="item.sources?.length">
            <p class="qa__label">相关片段</p>
            <ul>
              <li v-for="source in item.sources" :key="source.title">
                <strong>{{ source.title }}</strong> - {{ source.snippet }} ({{
                  source.score.toFixed(2)
                }})
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div v-else class="qa__empty">暂无问答记录</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";

import { useFilesStore } from "@/store/files";
import { useQaStore } from "@/store/qa";
import { createAutoScroll } from "@/utils/autoScroll";

const filesStore = useFilesStore();
const qaStore = useQaStore();

const question = ref("");
const fileId = ref<string | undefined>(undefined);
const historyRef = ref<HTMLElement | null>(null);
const { scrollToBottom, updateAutoScroll } = createAutoScroll({
  threshold: 120
});
const handleScroll = () => updateAutoScroll(historyRef.value);

const loading = computed(() => qaStore.loading);
const records = computed(() => qaStore.records);
const files = computed(() => filesStore.list);

const submitQuestion = async () => {
  if (!question.value.trim()) {
    ElMessage.warning("请输入问题");
    return;
  }
  await qaStore.sendQuestion(question.value, fileId.value);
  question.value = "";
};

const reset = () => {
  question.value = "";
};

const scrollToBottomIfNeeded = () => scrollToBottom(historyRef.value);

watch(fileId, async (value) => {
  await qaStore.loadHistory(value);
});

watch(records, () => {
  scrollToBottomIfNeeded();
}, { deep: true });

onMounted(async () => {
  await filesStore.loadFiles();
  await qaStore.loadHistory();
  scrollToBottomIfNeeded();
  if (historyRef.value) {
    historyRef.value.addEventListener("scroll", handleScroll, { passive: true });
  }
});

onUnmounted(() => {
  if (historyRef.value) {
    historyRef.value.removeEventListener("scroll", handleScroll);
  }
});
</script>

<style scoped>
.qa {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 20px;
}

.qa__panel {
  display: grid;
  gap: 16px;
}

.qa__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.qa__actions {
  display: flex;
  gap: 12px;
}

.qa__history {
  max-height: 560px;
  overflow: auto;
}

.qa__list {
  display: grid;
  gap: 16px;
}

.qa__item {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--nl-border);
}

.qa__q {
  margin: 0;
  font-weight: 600;
}

.qa__a {
  margin: 6px 0 0;
  color: var(--nl-muted);
}

.qa__sources {
  margin-top: 10px;
  font-size: 12px;
  color: var(--nl-muted);
}

.qa__sources ul {
  margin: 6px 0 0;
  padding-left: 16px;
}

.qa__label {
  margin: 0;
  font-weight: 600;
}

.qa__empty {
  color: var(--nl-muted);
  padding: 24px 0;
}

@media (max-width: 960px) {
  .qa {
    grid-template-columns: 1fr;
  }
}
</style>
