<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="preview-card fade-in">
      <div class="card-header">
        <h3 class="title">> FILE_PREVIEW_</h3>
        <button class="close-btn" @click="$emit('close')">X</button>
      </div>
      
      <div class="card-body">
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>LOADING_DATA...</p>
        </div>

        <div v-else-if="error" class="error-state">
          <p class="error-text">ERROR: {{ error }}</p>
          <a :href="url" target="_blank" class="pixel-btn">OPEN_EXTERNAL</a>
        </div>

        <div v-else class="content-wrapper">
          <!-- PDF Viewer -->
          <div v-if="fileType === 'pdf'" class="pdf-container">
             <VuePdfEmbed 
                :source="url"
                @loaded="handlePdfLoad"
                class="pdf-viewer"
             />
          </div>

          <!-- Markdown Viewer -->
          <div v-else-if="fileType === 'markdown'" class="markdown-body">
            <div v-html="mdHtml"></div>
          </div>

          <!-- Image Viewer -->
          <div v-else-if="fileType === 'image'" class="image-wrapper">
            <img :src="url" alt="Preview" />
          </div>

          <!-- Text/Code Viewer -->
          <div v-else-if="fileType === 'text'" class="text-wrapper">
            <pre><code>{{ textContent }}</code></pre>
          </div>

           <!-- Audio Viewer -->
           <div v-else-if="fileType === 'audio'" class="media-wrapper">
            <audio controls :src="url"></audio>
          </div>

           <!-- Video Viewer -->
           <div v-else-if="fileType === 'video'" class="media-wrapper">
            <video controls :src="url"></video>
          </div>

          <!-- Fallback -->
          <div v-else class="fallback-state">
             <div class="pixel-icon">?</div>
             <p>PREVIEW_NOT_SUPPORTED</p>
             <p class="filename">{{ fileName }}</p>
             <a :href="url" target="_blank" class="pixel-btn primary">DOWNLOAD_FILE</a>
          </div>
        </div>
      </div>
      
      <div class="card-footer">
        <span class="file-info">{{ fileName }} | {{ fileSize }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import axios from 'axios';
import MarkdownIt from 'markdown-it';
import VuePdfEmbed from 'vue-pdf-embed';
// Styles are automatically imported or not needed for basic usage in newer versions, 
// or the path is different. Let's try removing explicit style imports if they fail,
// or check node_modules. Assuming standard v2+ usage where styles might be included or optional.

const props = defineProps<{
  url: string;
  fileName: string;
  fileSize: string;
  contentType: string;
}>();

defineEmits(['close']);

const loading = ref(true);
const error = ref('');
const textContent = ref('');
const mdHtml = ref(''); // For markdown HTML
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
});

// PDF State
const pdfSource = ref<string | Uint8Array | object | null>(null);
const page = ref<number | null>(1);
const pageCount = ref(1);

// Determine basic file type category
const fileType = computed(() => {
  const name = props.fileName.toLowerCase();
  const type = props.contentType.toLowerCase();

  if (type.includes('pdf') || name.endsWith('.pdf')) return 'pdf';
  if (type.includes('image') || /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/.test(name)) return 'image';
  if (type.includes('audio') || /\.(mp3|wav|ogg|m4a)$/.test(name)) return 'audio';
  if (type.includes('video') || /\.(mp4|webm|ogv|mov)$/.test(name)) return 'video';
  if (name.endsWith('.md') || type.includes('markdown')) return 'markdown'; // Special handling for MD
  if (type.includes('text') || type.includes('json') || type.includes('xml') || /\.(txt|json|log|py|js|ts|java|c|cpp|h|css|html|yml|yaml|ini|conf)$/.test(name)) return 'text';
  
  return 'unknown';
});

// Fetch text content if needed
const loadContent = async () => {
  loading.value = true;
  error.value = '';
  pdfSource.value = null;
  mdHtml.value = '';
  textContent.value = '';
  
  try {
    if (fileType.value === 'markdown' || fileType.value === 'text') {
      // Use axios to fetch the text content from the signed URL
      // Note: This requires CORS to be enabled on the storage server (MinIO/S3)
      const response = await axios.get(props.url, { responseType: 'text' });
      const rawText = response.data;
      
      if (fileType.value === 'markdown') {
        mdHtml.value = md.render(rawText);
      } else {
        textContent.value = rawText;
      }
    } else if (fileType.value === 'pdf') {
       // Frame loading handled by browser, but we can simulate a short load
       // to show UI feedback
       // For vue-pdf-embed, we pass the URL directly
       pdfSource.value = props.url;
    }
  } catch (e) {
    console.error("Preview load failed", e);
    // If CORS fails, we can't show text, so fallback
    if (fileType.value === 'text' || fileType.value === 'markdown') {
      error.value = "CORS_BLOCK_OR_NETWORK_ERROR";
    }
  } finally {
    // Artificial delay for effect or waiting for frame
    setTimeout(() => {
      loading.value = false;
    }, 500);
  }
};

const handlePdfLoad = (event: any) => {
    // vue-pdf-embed emits loaded event
    loading.value = false;
};

watch(() => props.url, () => {
  if (props.url) loadContent();
}, { immediate: true });

</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.preview-card {
  width: 90%;
  max-width: 1000px;
  height: 85vh;
  background: white;
  border: 4px solid black;
  box-shadow: 12px 12px 0px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
  animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes popIn {
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.card-header {
  background: #3b82f6; /* Blue header */
  padding: 12px 20px;
  border-bottom: 4px solid black;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  color: white;
  font-family: 'Courier New', monospace;
  font-weight: bold;
  font-size: 20px;
  margin: 0;
  text-shadow: 2px 2px 0px black;
}

.close-btn {
  background: #ef4444;
  border: 2px solid black;
  color: white;
  font-weight: bold;
  width: 32px;
  height: 32px;
  cursor: pointer;
  box-shadow: 2px 2px 0px black;
}

.close-btn:active {
  transform: translate(2px, 2px);
  box-shadow: none;
}

.card-body {
  flex: 1;
  overflow: hidden;
  background: #f3f4f6;
  position: relative;
  display: flex;
  flex-direction: column;
}

.content-wrapper {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: center; /* Center content */
  padding: 20px;
}

.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
  background: white;
}

.image-wrapper img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border: 2px solid black;
  box-shadow: 4px 4px 0px rgba(0,0,0,0.1);
}

.pdf-container {
  width: 100%;
  height: 100%;
  overflow: auto;
  background: #525659; /* Default PDF viewer background color */
  padding: 20px;
  display: flex;
  justify-content: center;
}

.pdf-viewer {
  width: 100%;
  max-width: 800px; /* Readability width */
  box-shadow: 0 0 10px rgba(0,0,0,0.3);
}

.markdown-body {
  width: 100%;
  height: 100%;
  background: white;
  padding: 40px;
  overflow: auto;
  font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji";
  line-height: 1.6;
  color: #24292e;
}

/* Typora-like / GitHub-like Markdown Styles */
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body :deep(p) {
  margin-bottom: 16px;
}

.markdown-body :deep(code) {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27,31,35,0.05);
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

.markdown-body :deep(pre) {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 3px;
  margin-bottom: 16px;
}

.markdown-body :deep(pre code) {
  display: inline;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
}

.markdown-body :deep(blockquote) {
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
  margin: 0 0 16px 0;
}

.markdown-body :deep(table) {
  display: block;
  width: 100%;
  overflow: auto;
  margin-bottom: 16px;
  border-spacing: 0;
  border-collapse: collapse;
}

.markdown-body :deep(table th), .markdown-body :deep(table td) {
  padding: 6px 13px;
  border: 1px solid #dfe2e5;
}

.markdown-body :deep(table tr:nth-child(2n)) {
  background-color: #f6f8fa;
}

.text-wrapper {
  width: 100%;
  height: 100%;
  background: white;
  border: 2px solid #ccc;
  padding: 20px;
  overflow: auto;
  text-align: left;
  align-items: flex-start; /* Reset align for text */
}

.text-wrapper pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 14px;
  line-height: 1.6;
}

.media-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
}

.media-wrapper video, .media-wrapper audio {
  max-width: 100%;
  border: 2px solid black;
}

.loading-state, .error-state, .fallback-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  font-family: monospace;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #3b82f6;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.pixel-icon {
  font-size: 64px;
  font-weight: bold;
  color: #9ca3af;
}

.pixel-btn {
  padding: 10px 20px;
  border: 2px solid black;
  text-decoration: none;
  background: white;
  color: black;
  font-family: monospace;
  font-weight: bold;
  box-shadow: 4px 4px 0px black;
  transition: all 0.1s;
}

.pixel-btn.primary {
  background: #10b981;
  color: white;
}

.pixel-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px black;
}

.card-footer {
  border-top: 4px solid black;
  padding: 8px 20px;
  background: #e5e7eb;
  font-family: monospace;
  font-size: 12px;
  color: #4b5563;
  text-align: right;
}
</style>