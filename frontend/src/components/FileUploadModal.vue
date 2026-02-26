<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="upload-modal card fade-in">
      <div class="modal-header">
        <h3 class="title">> 上传文档_</h3>
        <button class="close-btn" @click="$emit('close')" :disabled="uploading">X</button>
      </div>

      <div class="modal-body">
        <el-upload
          class="upload-area"
          drag
          action=""
          :auto-upload="false"
          :show-file-list="false"
          :before-upload="handleBeforeUpload"
          :on-change="handleFileChange"
          :disabled="uploading"
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

        <p class="upload-desc">支持格式: PDF, MD, WORD, TXT (最大 50MB)</p>

        <!-- Selected File State -->
        <div v-if="file" class="file-preview fade-in">
          <div class="file-info">
            <div class="file-icon">[FILE]</div>
            <div class="file-details">
              <h4 class="file-name" :title="file.name">{{ file.name }}</h4>
              <p class="file-size">{{ formatSize(file.size) }}</p>
            </div>
          </div>
        </div>

        <!-- Progress -->
        <div v-if="uploading || (progress && progress.percent > 0)" class="progress-section">
          <div class="progress-bar">
            <div class="progress-fill" 
                 :class="{ 'vectorizing-stripe': status === 'vectorizing' || status === 'merging' }"
                 :style="{ width: (progress ? progress.percent : 0) + '%' }">
            </div>
          </div>
          <span class="progress-text">{{ progress ? Math.floor(progress.percent) : 0 }}%</span>
        </div>

        <!-- Status Text -->
        <div v-if="status && status !== 'idle'" class="status-message">
          <span v-if="status === 'vectorizing' || status === 'merging'" class="blink">⚡</span>
          {{ statusText }}
        </div>

      </div>

      <div class="modal-footer">
        <button class="pixel-btn secondary" @click="$emit('close')" :disabled="uploading">取消</button>
        <button class="pixel-btn primary" :disabled="!file || uploading" @click="submitUpload">
          <span v-if="!uploading">确认上传</span>
          <span v-else>处理中...</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { useUploadStore } from "@/store/uploads";
import { formatSize } from "@/utils/format";
import { validateFileType } from "@/utils/validators";

const emit = defineEmits(['close', 'upload-success']);

const file = ref<File | null>(null);
const uploadStore = useUploadStore();

const uploading = computed(() => uploadStore.uploading);
const progress = computed(() => uploadStore.progress);
const status = computed(() => uploadStore.status);

const statusText = computed(() => {
  switch (status.value) {
    case 'uploading': return '正在上传...';
    case 'merging': return '正在合并分片...';
    case 'vectorizing': return '正在后台处理...'; // Just a hint, we close on this
    case 'completed': return '完成!';
    case 'failed': return '失败';
    default: return '';
  }
});

// Reset state when component mounts
onMounted(() => {
  file.value = null;
  uploadStore.reset();
});

const handleBeforeUpload = (rawFile: File) => {
  if (!validateFileType(rawFile.name)) {
    ElMessage.error("格式错误: 仅支持 PDF/MD/WORD/TXT");
    return false;
  }
  if (rawFile.size > 50 * 1024 * 1024) {
    ElMessage.error("文件过大: 最大支持 50MB");
    return false;
  }
  return true;
};

const handleFileChange = (uploadFile: { raw?: File }) => {
  if (uploadFile.raw) {
    file.value = uploadFile.raw;
    uploadStore.reset();
  }
};

const submitUpload = async () => {
  if (!file.value) return;
  try {
    // startUpload resolves when status becomes 'completed' normally, 
    // but the store logic waits for vectorization.
    // We want to intervene or modify store logic?
    // Actually, looking at services/files.ts, it polls until 'completed' (vectorized) or 'failed'.
    // BUT the requirement is: "Once uploaded (vectorization starts), close window".
    
    // We cannot easily change the Promise behavior of `uploadStore.startUpload` without changing `services/files.ts`
    // OR we can just fire and forget the store action, but we need to know when "uploading/merging" is done.
    
    // Let's modify the store approach in `startUpload`? No, let's keep it robust.
    // We can watch the `status` computed property.
    
    // Start the process
    const uploadPromise = uploadStore.startUpload(file.value);
    
    // We don't await the full promise here if we want to close early.
    // However, if we close, we might want to ensure the background process continues?
    // JS Promises continue even if component unmounts (store is global).
    // So we can watch status.
    
  } catch (error) {
    ElMessage.error("启动上传失败");
  }
};

// Watch status to auto-close when vectorization starts
import { watch } from 'vue';
watch(status, (newStatus) => {
  if (newStatus === 'vectorizing' || newStatus === 'completed') {
    // Requirement: "After upload success, close window, don't wait for vectorization"
    // 'vectorizing' means upload & merge is done.
    ElMessage.success("上传成功，正在后台处理");
    emit('upload-success');
    emit('close');
  }
});

</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-modal {
  width: 90%;
  max-width: 500px;
  background: white;
  border: 4px solid black;
  box-shadow: 12px 12px 0px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
}

.modal-header {
  background: #f3f4f6;
  padding: 16px 20px;
  border-bottom: 4px solid black;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-weight: bold;
}

.close-btn {
  background: #ef4444;
  border: 2px solid black;
  color: white;
  width: 24px;
  height: 24px;
  cursor: pointer;
  line-height: 1;
  font-weight: bold;
}

.modal-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Upload Area Styles */
:deep(.el-upload) { width: 100%; }
:deep(.el-upload-dragger) {
  width: 100% !important;
  border: 2px dashed #9ca3af !important;
  border-radius: 0 !important;
  background: #f9fafb;
  height: auto !important;
  padding: 30px 0;
}
:deep(.el-upload-dragger:hover) {
  border-color: #3b82f6 !important;
  background: #eff6ff;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-icon-box {
  width: 48px;
  height: 48px;
  background: #3b82f6;
  border: 2px solid black;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  box-shadow: 4px 4px 0px rgba(0,0,0,0.1);
}

.upload-text strong {
  display: block;
  font-family: monospace;
  font-size: 16px;
  margin-bottom: 4px;
}

.upload-desc {
  font-size: 12px;
  color: #6b7280;
  text-align: center;
  margin: 0;
  font-family: monospace;
}

/* File Preview */
.file-preview {
  border: 2px solid black;
  padding: 12px;
  background: #f0fdf4;
  display: flex;
  align-items: center;
}

.file-info {
  display: flex;
  gap: 12px;
  align-items: center;
  width: 100%;
}

.file-icon {
  font-weight: bold;
  font-family: monospace;
}

.file-details {
  flex: 1;
  overflow: hidden;
}

.file-name {
  margin: 0;
  font-size: 14px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: monospace;
}

.file-size {
  margin: 0;
  font-size: 12px;
  color: #666;
}

/* Progress Bar */
.progress-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 16px;
  background: #e5e7eb;
  border: 2px solid black;
}

.progress-fill {
  height: 100%;
  background: #10b981;
  width: 0%;
  transition: width 0.2s;
  background-image: linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent);
  background-size: 1rem 1rem;
}

.vectorizing-stripe {
  background-color: #f59e0b;
  animation: stripe-move 1s linear infinite;
}

@keyframes stripe-move {
  0% { background-position: 0 0; }
  100% { background-position: 1rem 1rem; }
}

.progress-text {
  font-family: monospace;
  font-weight: bold;
  font-size: 14px;
}

.status-message {
  text-align: center;
  font-family: monospace;
  font-size: 12px;
  color: #4b5563;
}

/* Footer */
.modal-footer {
  padding: 16px 24px;
  background: #f9fafb;
  border-top: 4px solid black;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.pixel-btn {
  padding: 8px 16px;
  border: 2px solid black;
  font-family: monospace;
  font-weight: bold;
  cursor: pointer;
  background: white;
  box-shadow: 2px 2px 0px black;
  transition: all 0.1s;
}

.pixel-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0px black;
}

.pixel-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.pixel-btn.primary { background: #3b82f6; color: white; }
.pixel-btn.secondary { background: white; color: black; }

.blink { animation: blink 1s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }
</style>