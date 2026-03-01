<template>
  <div class="account-container">
    <div v-if="user" class="account-layout fade-in">
      
      <!-- Left Column: Profile Card -->
      <div class="card profile-card retro-window">
        <div class="window-header">
          <h2 class="window-title">> 个人档案.exe</h2>
          <div class="status-indicator" :class="user.status === 1 ? 'online' : 'offline'">
            <div class="status-dot"></div>
            <span>{{ user.status === 1 ? 'ONLINE' : 'OFFLINE' }}</span>
          </div>
        </div>

        <div class="profile-body">
          <!-- Avatar Display -->
          <div class="avatar-section">
            <div class="pixel-avatar-box" :class="{'editable': isEditing}" @click="isEditing && toggleAvatarModal()">
              <div v-if="isSystemAvatar(currentAvatarId)" v-html="getSystemAvatarSvg(currentAvatarId)" class="avatar-svg"></div>
              <span v-else class="avatar-text">{{ user.username.substring(0, 2).toUpperCase() }}</span>
              
              <div v-if="isEditing" class="edit-overlay">
                <span>[更换]</span>
              </div>
            </div>
            <div class="role-badge" :class="'role-' + user.role">{{ user.role.toUpperCase() }}</div>
          </div>

          <!-- User Info Details -->
          <div class="info-grid">
             <div class="info-row">
               <span class="info-label">UID_</span>
               <span class="info-value highlight-text">#{{ user.id.toString().padStart(6, '0') }}</span>
             </div>
             <div class="info-row">
               <span class="info-label">USER_</span>
               <span class="info-value">{{ user.username }}</span>
             </div>
             <div class="info-row">
               <span class="info-label">NAME_</span>
               <div v-if="!isEditing" class="info-value">{{ user.name || 'N/A' }}</div>
               <input v-else v-model="editForm.name" class="pixel-input" placeholder="Name..." />
             </div>
             <div class="info-row">
               <span class="info-label">MAIL_</span>
               <div v-if="!isEditing" class="info-value">{{ user.email || '未设置' }}</div>
               <input v-else v-model="editForm.email" class="pixel-input" placeholder="Email..." />
             </div>
          </div>

          <!-- Bio Section -->
          <div class="bio-section">
            <div class="bio-header">
              <span class="info-label">BIO.TXT</span>
            </div>
            <div v-if="!isEditing" class="bio-content scroll-box">
              {{ user.bio || '还没有填写个人简介。' }}
            </div>
            <textarea v-else v-model="editForm.bio" class="pixel-input bio-input" rows="4" placeholder="介绍一下你自己..."></textarea>
          </div>

          <!-- Action Buttons -->
          <div class="actions">
            <template v-if="!isEditing">
              <button class="btn btn-primary" @click="startEdit">
                <span class="icon">✏️</span> 编辑资料
              </button>
              <button class="btn btn-danger" @click="handleLogout">
                <span class="icon">🚪</span> 退出登录
              </button>
            </template>
            <template v-else>
              <button class="btn btn-success" @click="saveEdit" :disabled="saving">
                {{ saving ? '保存中...' : '💾 保存更改' }}
              </button>
              <button class="btn" @click="cancelEdit" :disabled="saving">
                ✖ 取消
              </button>
            </template>
          </div>
        </div>
      </div>

      <!-- Right Column: Stats & Quota -->
      <div class="stats-column">
        <!-- Storage Quota Card -->
        <div class="card stats-card retro-window">
          <div class="window-header small-header">
            <span class="window-title">SYS_QUOTA</span>
          </div>
          <div class="card-body">
            <div class="quota-visual">
              <div class="quota-text">
                <span>STORAGE</span>
                <span class="quota-numbers"><span class="used">{{ formatBytes(quota.used_bytes) }}</span> / {{ formatBytes(quota.total_bytes) }}</span>
              </div>
              <div class="progress-track">
                <div class="progress-fill" :style="{ width: storagePercent + '%' }" :class="{'warning': storagePercent > 80, 'danger': storagePercent > 95}"></div>
              </div>
            </div>
            <div class="stat-list">
              <div class="stat-item">
                <span class="stat-label">> FILES_UPLOADED</span>
                <span class="stat-value">{{ quota.file_count }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- System Stats / Placeholder -->
        <div class="card stats-card retro-window">
          <div class="window-header small-header">
            <span class="window-title">SERVER_INFO</span>
          </div>
          <div class="card-body">
            <div class="stat-list">
              <div class="stat-item">
                <span class="stat-label">> STATUS</span>
                <span class="stat-value status-ok">ONLINE</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">> LATENCY</span>
                <span class="stat-value">24ms</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">> CORE_VERSION</span>
                <span class="stat-value">v1.2.0</span>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Loading State -->
    <div v-else class="loading-state">
      <div class="blink-text">LOADING_PROFILE_DATA...</div>
    </div>

    <!-- Avatar Selection Modal -->
    <div v-if="showAvatarModal" class="modal-overlay" @click.self="showAvatarModal = false">
      <div class="card modal-content retro-window">
        <div class="window-header">
          <span class="window-title">SELECT_AVATAR</span>
          <button class="close-btn" @click="showAvatarModal = false">X</button>
        </div>
        <div class="modal-body">
          <div class="avatar-grid">
             <div 
              v-for="avatar in systemAvatars" 
              :key="avatar.id"
              class="avatar-option"
              :class="{ active: editForm.avatar_file_id === avatar.id }"
              @click="selectAvatar(avatar.id)"
            >
              <div class="avatar-preview" v-html="avatar.svg"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/store/user';
import { updateUser } from '@/services/auth';
import { ElMessage } from 'element-plus';
import type { Quota } from '@/services/types';

const router = useRouter();
const userStore = useUserStore();
const user = computed(() => userStore.user);

// --- State ---
const isEditing = ref(false);
const saving = ref(false);
const showAvatarModal = ref(false);

const editForm = reactive({
  name: '',
  email: '',
  bio: '',
  avatar_file_id: 0
});

// --- Mock Quota Data ---
const quota = computed<Quota>(() => {
  if (user.value?.quota) return user.value.quota;
  return {
    total_bytes: 1024 * 1024 * 1024 * 2, // 2GB
    used_bytes: 1024 * 1024 * 450, // ~450MB
    file_count: 12
  };
});

const storagePercent = computed(() => {
  if (!quota.value.total_bytes) return 0;
  return Math.min(100, (quota.value.used_bytes / quota.value.total_bytes) * 100);
});

const currentAvatarId = computed(() => {
  if (isEditing.value) return editForm.avatar_file_id;
  return user.value?.avatar_file_id || 0;
});

// --- System Avatars Data ---
const systemAvatars = [
  { id: -1, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="var(--nl-danger)"><path d="M2 2h4v1h1v4h-1v1h-4v-1h-1v-4h1v-1z"/></svg>` },
  { id: -2, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="var(--nl-primary)"><path d="M1 1h2v1h-1v1h-1v2h1v1h1v1h2v-1h1v-1h1v-2h-1v-1h-1v-1h-2z"/></svg>` },
  { id: -3, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="var(--nl-accent)"><rect x="2" y="2" width="4" height="4"/><rect x="1" y="3" width="6" height="2"/><rect x="3" y="1" width="2" height="6"/></svg>` },
  { id: -4, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="var(--nl-warning)"><path d="M0 0h2v2h2v-2h2v2h2v2h-2v2h2v2h-2v-2h-2v2h-2v-2h-2v-2h2v-2h-2z"/></svg>` },
  { id: -5, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="var(--nl-secondary)"><circle cx="4" cy="4" r="3"/></svg>` }
];

// --- Actions ---
const startEdit = () => {
  if (user.value) {
    editForm.name = user.value.name || '';
    editForm.email = user.value.email || '';
    editForm.bio = user.value.bio || '';
    editForm.avatar_file_id = user.value.avatar_file_id || 0;
    isEditing.value = true;
  }
};

const cancelEdit = () => {
  isEditing.value = false;
  showAvatarModal.value = false;
};

const saveEdit = async () => {
  if (!user.value) return;
  try {
    saving.value = true;
    const updatedUser = await updateUser(user.value.id, {
      name: editForm.name,
      email: editForm.email,
      bio: editForm.bio,
      avatar_file_id: editForm.avatar_file_id
    });
    userStore.user = updatedUser;
    ElMessage.success('资料已更新');
    isEditing.value = false;
  } catch (e) {
    ElMessage.error('更新失败');
  } finally {
    saving.value = false;
  }
};

const handleLogout = async () => {
  await userStore.logout();
  router.push('/login');
};

const toggleAvatarModal = () => {
  showAvatarModal.value = !showAvatarModal.value;
};

const selectAvatar = (id: number) => {
  editForm.avatar_file_id = id;
};

// --- Helpers ---
const formatBytes = (bytes: number, decimals = 2) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

const isSystemAvatar = (id: number) => id < 0;

const getSystemAvatarSvg = (id: number) => {
  const avatar = systemAvatars.find(a => a.id === id);
  return avatar ? avatar.svg : '';
};

onMounted(() => {
  if (!userStore.user) {
    userStore.checkAuth();
  }
});
</script>

<style scoped>
.account-container {
  display: flex;
  justify-content: center;
  max-width: 1000px;
  margin: 0 auto;
}

.account-layout {
  display: flex;
  gap: 32px;
  width: 100%;
  flex-wrap: wrap;
  align-items: flex-start;
}

/* Retro Window Styles */
.retro-window {
  padding: 0;
  overflow: hidden;
  background: var(--nl-surface);
}

.window-header {
  background: var(--nl-border);
  color: var(--nl-surface);
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.small-header {
  padding: 8px 16px;
}

.window-title {
  font-family: var(--font-display);
  font-size: 16px;
  margin: 0;
  color: #fff;
  letter-spacing: 1px;
}

.small-header .window-title {
  font-size: 14px;
}

/* Status Indicator */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 12px;
  background: #333;
  padding: 4px 8px;
  border: 2px solid #555;
}

.status-dot {
  width: 10px;
  height: 10px;
  background: var(--nl-danger);
}

.status-indicator.online .status-dot {
  background: var(--nl-accent);
  box-shadow: 0 0 8px var(--nl-accent);
}

.status-indicator.online {
  color: var(--nl-accent);
}

/* Card Body */
.profile-body {
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.card-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Columns */
.profile-card {
  flex: 1 1 600px;
}

.stats-column {
  flex: 1 1 300px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* Avatar */
.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.pixel-avatar-box {
  width: 120px;
  height: 120px;
  background: var(--nl-bg);
  border: 4px solid var(--nl-border);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: var(--nl-shadow-solid);
}

.pixel-avatar-box.editable {
  cursor: pointer;
  transition: transform 0.1s;
}

.pixel-avatar-box.editable:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px var(--nl-secondary);
}

.pixel-avatar-box.editable:hover .edit-overlay {
  opacity: 1;
}

.edit-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.7);
  color: var(--nl-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 14px;
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-svg {
  width: 80%;
  height: 80%;
}

.avatar-text {
  font-family: var(--font-display);
  font-size: 48px;
  color: var(--nl-text-main);
}

.role-badge {
  font-family: var(--font-display);
  font-size: 12px;
  padding: 4px 12px;
  border: 2px solid var(--nl-border);
  background: var(--nl-bg-grid);
  box-shadow: 2px 2px 0px var(--nl-border);
}

.role-admin {
  background: var(--nl-primary);
  color: white;
}

/* User Info Grid */
.info-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--nl-bg);
  padding: 24px;
  border: 2px solid var(--nl-border);
  box-shadow: inset 4px 4px 0px rgba(0,0,0,0.05);
}

.info-row {
  display: flex;
  align-items: center;
}

.info-label {
  font-family: var(--font-display);
  font-size: 14px;
  color: var(--nl-text-secondary);
  width: 100px;
  flex-shrink: 0;
}

.info-value {
  font-family: var(--font-body);
  font-size: 20px;
  color: var(--nl-text-main);
  font-weight: bold;
}

.highlight-text {
  color: var(--nl-secondary);
}

/* Bio Section */
.bio-section {
  display: flex;
  flex-direction: column;
}

.bio-header {
  background: var(--nl-border);
  padding: 4px 12px;
  display: inline-block;
  align-self: flex-start;
}

.bio-header .info-label {
  color: var(--nl-surface);
  width: auto;
}

.scroll-box {
  background: #fff;
  border: 2px solid var(--nl-border);
  padding: 16px;
  font-family: var(--font-body);
  font-size: 18px;
  line-height: 1.6;
  min-height: 100px;
  white-space: pre-wrap;
  box-shadow: inset 2px 2px 0px rgba(0,0,0,0.1);
}

/* Form Inputs */
.pixel-input {
  flex: 1;
  background: #fff;
  border: 2px solid var(--nl-border);
  padding: 8px 12px;
  font-family: var(--font-body);
  font-size: 18px;
  outline: none;
}

.pixel-input:focus {
  border-color: var(--nl-primary);
  background: #f0f5ff;
}

.bio-input {
  width: 100%;
  padding: 16px;
  resize: vertical;
  min-height: 100px;
}

/* Actions */
.actions {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}

.actions .btn {
  flex: 1;
}

.btn-success { background: var(--nl-accent); color: white; }
.btn-danger { background: var(--nl-danger); color: white; }

/* Stats Visuals */
.quota-visual {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quota-text {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-display);
  font-size: 12px;
}

.used {
  color: var(--nl-primary);
}

.progress-track {
  height: 24px;
  background: var(--nl-bg);
  border: 2px solid var(--nl-border);
  box-shadow: inset 2px 2px 0px rgba(0,0,0,0.2);
}

.progress-fill {
  height: 100%;
  background: var(--nl-primary);
  border-right: 2px solid var(--nl-border);
  transition: width 0.5s steps(10);
}

.progress-fill.warning { background: var(--nl-warning); }
.progress-fill.danger { background: var(--nl-danger); }

/* Stat List */
.stat-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-body);
  font-size: 18px;
  border-bottom: 2px dotted var(--nl-bg-grid);
  padding-bottom: 8px;
}

.stat-label {
  color: var(--nl-text-secondary);
  font-weight: bold;
}

.stat-value {
  font-weight: bold;
}

.status-ok {
  color: var(--nl-accent);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  width: 90%;
  max-width: 400px;
}

.close-btn {
  background: transparent;
  border: none;
  color: white;
  font-family: var(--font-display);
  font-size: 16px;
  cursor: pointer;
}

.close-btn:hover {
  color: var(--nl-danger);
}

.modal-body {
  padding: 24px;
  background: var(--nl-bg);
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
  gap: 16px;
}

.avatar-option {
  width: 64px;
  height: 64px;
  background: white;
  border: 2px solid var(--nl-border);
  cursor: pointer;
  padding: 8px;
  transition: transform 0.1s;
  box-shadow: 2px 2px 0px var(--nl-border);
}

.avatar-option:hover {
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0px var(--nl-primary);
}

.avatar-option.active {
  background: var(--nl-primary);
  border-color: var(--nl-border);
}

.avatar-option.active svg {
  fill: white !important;
}

.avatar-preview {
  width: 100%;
  height: 100%;
}

/* Loading */
.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}

.blink-text {
  font-family: var(--font-display);
  font-size: 20px;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

@media (max-width: 768px) {
  .info-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  .info-label {
    width: 100%;
  }
}
</style>