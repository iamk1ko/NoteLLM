<template>
  <div class="upload-container">
    <div class="card upload-card fade-in">
      <div class="upload-header">
        <h2 class="section-title"> > 上传文档_</h2>
        <p class="upload-desc">支持格式: PDF, MD, WORD, TXT (最大 50MB)</p>
      </div>

      <el-upload
        class="upload-area"
        drag
        action=""
        :auto-upload="false"
        :show-file-list="false"
        :before-upload="handleBeforeUpload"
        :on-change="handleFileChange"
      >
        <div class="upload-placeholder">
          <div class="upload-icon-box">
            <span class="pixel-icon">+</span>
          </div>
          <div class="upload-text">
            <strong>拖拽文件到这里</strong>
            <p>[ 或者点击选择 ]</p>
          </div>
        </div>
      </el-upload>

      <!-- Selected File State -->
      <div v-if="file" class="file-preview fade-in">
        <div class="file-info">
          <div class="file-icon">[FILE]</div>
          <div>
            <h4 class="file-name">{{ file.name }}</h4>
            <p class="file-size">{{ formatSize(file.size) }}</p>
          </div>
        </div>
        <button class="pixel-btn" :disabled="uploading" @click="submitUpload">
          <span v-if="!uploading">开始上传</span>
          <span v-else>上传中...</span>
        </button>
      </div>

      <!-- Progress -->
      <div v-if="progress" class="progress-container">
        <div class="progress-bar">
          <div class="progress-fill" 
               :class="{ 'vectorizing-stripe': status === 'vectorizing' || status === 'merging' }"
               :style="{ width: progress.percent + '%' }">
          </div>
        </div>
        <span class="progress-text">{{ Math.floor(progress.percent) }}%</span>
      </div>

      <!-- Status Text -->
      <div v-if="status && status !== 'idle' && status !== 'completed'" class="status-message fade-in">
        <span class="blink" v-if="status === 'vectorizing'">⚡</span>
        {{ statusText }}
      </div>

      <!-- Success Feedback -->
      <div v-if="successMessage" class="success-feedback fade-in">
        <span class="status-icon">[OK]</span>
        {{ successMessage }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useUploadStore } from "@/store/uploads";
import { formatSize } from "@/utils/format";
import { validateFileType } from "@/utils/validators";

/**
 * UploadView Component
 * --------------------
 * 文件上传页面
 * 支持拖拽和点击上传，提供文件校验和进度显示
 */

const router = useRouter();
const file = ref<File | null>(null); // 当前选中的文件
const successMessage = ref(""); // 上传成功的提示信息
const uploadStore = useUploadStore();

const uploading = computed(() => uploadStore.uploading); // 全局上传状态
const progress = computed(() => uploadStore.progress); // 进度信息
const status = computed(() => uploadStore.status);

const statusText = computed(() => {
  switch (status.value) {
    case 'uploading': return '正在上传到服务器...';
    case 'merging': return '正在合并分片...';
    case 'vectorizing': return '正在进行向量化处理 (可能需要几分钟)...';
    case 'completed': return '处理完成!';
    case 'failed': return '处理失败';
    default: return '';
  }
});

/**
 * 上传前钩子 (Before Upload)
 * 校验文件类型和大小
 */
const handleBeforeUpload = (rawFile: File) => {
  // 1. 校验文件格式 (PDF/MD/WORD/TXT)
  if (!validateFileType(rawFile.name)) {
    ElMessage.error("格式错误: 仅支持 PDF/MD/WORD/TXT");
    return false;
  }
  // 2. 校验文件大小 (Max 50MB)
  if (rawFile.size > 50 * 1024 * 1024) {
    ElMessage.error("文件过大: 最大支持 50MB");
    return false;
  }
  return true;
};

/**
 * 文件选择变更 (File Change)
 * 当用户选择新文件时触发，重置状态
 */
const handleFileChange = (uploadFile: { raw?: File }) => {
  if (uploadFile.raw) {
    file.value = uploadFile.raw;
    successMessage.value = "";
    uploadStore.reset(); // 清空旧的进度条
  }
};

/**
 * 执行上传 (Submit)
 * 调用 Store 进行文件上传，成功后跳转到聊天页面
 */
const submitUpload = async () => {
  if (!file.value) return;
  try {
    const result = await uploadStore.startUpload(file.value);
    successMessage.value = "上传完成，正在跳转...";
    file.value = null;
    
    // 上传成功后延迟跳转，让用户看到成功提示
    setTimeout(() => {
      router.push(`/chat/${result.id}`);
    }, 1500);
  } catch (error) {
    ElMessage.error("上传失败，请重试");
  }
};
</script>

<style scoped>
.upload-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 152px); /* Full height minus header/padding */
  padding: 20px;
}

.upload-card {
  width: 100%;
  max-width: 600px;
  background: var(--nl-bg);
  border: 4px solid var(--nl-border);
  box-shadow: 8px 8px 0px var(--nl-border);
  padding: 40px;
  position: relative;
}

/* Decorative corner screws */
.upload-card::after {
  content: "";
  position: absolute;
  top: 8px;
  right: 8px;
  width: 8px;
  height: 8px;
  background: var(--nl-border);
  box-shadow: 
    -570px 0 0 var(--nl-border),
    0 350px 0 var(--nl-border),
    -570px 350px 0 var(--nl-border);
  pointer-events: none;
}

.upload-header {
  margin-bottom: 32px;
  text-align: left;
  border-bottom: 4px solid var(--nl-border);
  padding-bottom: 16px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 24px;
  margin-bottom: 12px;
  color: var(--nl-text-main);
  text-transform: uppercase;
}

.upload-desc {
  font-family: var(--font-body);
  color: var(--nl-text-secondary);
  font-size: 16px;
  margin: 0;
  text-transform: uppercase;
}

.upload-area {
  margin-bottom: 32px;
}

:deep(.el-upload-dragger) {
  border: 4px dashed var(--nl-border) !important;
  border-radius: 0 !important;
  padding: 60px 20px;
  background: var(--nl-surface);
  transition: all 0.1s steps(2);
  position: relative;
  overflow: visible;
}

:deep(.el-upload-dragger:hover) {
  border-color: var(--nl-primary) !important;
  background: #f0fdf4; /* Light green tint */
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0px var(--nl-border);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.upload-icon-box {
  width: 64px;
  height: 64px;
  background: var(--nl-primary);
  border: 4px solid var(--nl-border);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 4px 4px 0px var(--nl-border);
}

.pixel-icon {
  font-family: var(--font-display);
  font-size: 32px;
  color: white;
  line-height: 1;
}

.upload-text strong {
  display: block;
  font-family: var(--font-display);
  font-size: 16px;
  margin-bottom: 8px;
  color: var(--nl-text-main);
  text-transform: uppercase;
}

.upload-text p {
  margin: 0;
  font-family: var(--font-body);
  font-size: 16px;
  color: var(--nl-text-secondary);
}

.file-preview {
  background: var(--nl-surface);
  border: 4px solid var(--nl-border);
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  box-shadow: 4px 4px 0px var(--nl-border);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 16px;
  text-align: left;
}

.file-icon {
  font-family: var(--font-display);
  font-size: 14px;
  color: var(--nl-primary);
  background: var(--nl-bg);
  padding: 8px;
  border: 2px solid var(--nl-border);
}

.file-name {
  margin: 0 0 4px 0;
  font-family: var(--font-body);
  font-size: 18px;
  font-weight: 700;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-transform: uppercase;
}

.file-size {
  margin: 0;
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--nl-text-secondary);
}

.pixel-btn {
  font-family: var(--font-display);
  font-size: 12px;
  background: var(--nl-primary);
  color: white;
  border: 4px solid var(--nl-border);
  padding: 12px 20px;
  cursor: pointer;
  box-shadow: 4px 4px 0px var(--nl-border);
  transition: all 0.1s;
  text-transform: uppercase;
}

.pixel-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px var(--nl-border);
  background: #4338ca;
}

.pixel-btn:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 0px 0px 0px var(--nl-border);
}

.pixel-btn:disabled {
  background: var(--nl-text-secondary);
  cursor: not-allowed;
  opacity: 0.7;
}

.progress-container {
  margin-top: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 24px;
  background: var(--nl-bg);
  border: 4px solid var(--nl-border);
  padding: 2px;
}

.progress-fill {
  height: 100%;
  background: var(--nl-accent);
  border-right: 2px solid var(--nl-border);
  /* Striped retro pattern */
  background-image: linear-gradient(
    45deg,
    rgba(0, 0, 0, 0.15) 25%,
    transparent 25%,
    transparent 50%,
    rgba(0, 0, 0, 0.15) 50%,
    rgba(0, 0, 0, 0.15) 75%,
    transparent 75%,
    transparent
  );
  background-size: 20px 20px;
  transition: width 0.3s steps(5);
}

.vectorizing-stripe {
  background-color: #f59e0b; /* Amber */
  animation: stripe-move 1s linear infinite;
}

@keyframes stripe-move {
  0% { background-position: 0 0; }
  100% { background-position: 40px 40px; }
}

.status-message {
  margin-top: 12px;
  font-family: var(--font-display);
  font-size: 14px;
  color: var(--nl-text-main);
  text-align: center;
  font-weight: bold;
}

.blink {
  animation: blink 1s step-end infinite;
}

@keyframes blink { 50% { opacity: 0; } }

.progress-text {
  font-family: var(--font-display);
  font-size: 14px;
  min-width: 48px;
}

.success-feedback {
  margin-top: 24px;
  padding: 16px;
  background: var(--nl-accent);
  color: white;
  border: 4px solid var(--nl-border);
  font-family: var(--font-body);
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  box-shadow: 4px 4px 0px var(--nl-border);
}

.status-icon {
  font-family: var(--font-display);
  font-size: 12px;
}
</style>
