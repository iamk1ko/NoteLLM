<template>
  <div class="account-container">
    <div v-if="user" class="account-layout fade-in">
      
      <!-- Left Column: Profile Card -->
      <div class="card profile-card">
        <div class="card-header">
          <h2 class="title">> 个人档案_</h2>
          <div class="status-badge" :class="user.status === 1 ? 'active' : 'inactive'">
            {{ user.status === 1 ? 'ONLINE' : 'OFFLINE' }}
          </div>
        </div>

        <div class="profile-body">
          <!-- Avatar Display -->
          <div class="avatar-wrapper">
            <div class="pixel-avatar" :class="{'editable': isEditing}" @click="isEditing && toggleAvatarModal()">
              <!-- Use SVG for system avatars (negative IDs) -->
              <div v-if="isSystemAvatar(currentAvatarId)" v-html="getSystemAvatarSvg(currentAvatarId)" class="avatar-svg"></div>
              <!-- Fallback for initials or real image if we had one -->
              <span v-else>{{ user.username.substring(0, 2).toUpperCase() }}</span>
              
              <div v-if="isEditing" class="edit-overlay">
                <span>CHANGE</span>
              </div>
            </div>
            <p class="role-badge">[{{ user.role.toUpperCase() }}]</p>
          </div>

          <!-- User Info Details -->
          <div class="info-list">
             <div class="info-item">
               <label>UID</label>
               <span>#{{ user.id.toString().padStart(6, '0') }}</span>
             </div>
             <div class="info-item">
               <label>USERNAME</label>
               <span>{{ user.username }}</span>
             </div>
             <div class="info-item">
               <label>EMAIL</label>
               <div v-if="!isEditing">{{ user.email || 'unset' }}</div>
               <input v-else v-model="editForm.email" class="pixel-input small" placeholder="Enter email..." />
             </div>
          </div>

          <!-- Bio Section -->
          <div class="bio-section">
            <label>BIO_</label>
            <div v-if="!isEditing" class="bio-content">
              {{ user.bio || 'No biography set.' }}
            </div>
            <textarea v-else v-model="editForm.bio" class="pixel-input" rows="4" placeholder="Tell us about yourself..."></textarea>
          </div>

          <!-- Action Buttons -->
          <div class="actions">
            <template v-if="!isEditing">
              <button class="pixel-btn primary" @click="startEdit">EDIT PROFILE</button>
              <button class="pixel-btn secondary" @click="handleLogout">LOGOUT</button>
            </template>
            <template v-else>
              <button class="pixel-btn success" @click="saveEdit" :disabled="saving">
                {{ saving ? 'SAVING...' : 'SAVE CHANGES' }}
              </button>
              <button class="pixel-btn danger" @click="cancelEdit" :disabled="saving">CANCEL</button>
            </template>
          </div>
        </div>
      </div>

      <!-- Right Column: Stats & Quota -->
      <div class="stats-column">
        <!-- Storage Quota Card -->
        <div class="card stats-card">
          <div class="card-header small">
            <h3>STORAGE_QUOTA</h3>
          </div>
          <div class="card-body">
            <div class="quota-visual">
              <div class="progress-track">
                <div class="progress-fill" :style="{ width: storagePercent + '%' }"></div>
              </div>
              <div class="quota-text">
                <span class="used">{{ formatBytes(quota.used_bytes) }}</span>
                <span class="separator">/</span>
                <span class="total">{{ formatBytes(quota.total_bytes) }}</span>
              </div>
            </div>
            <div class="stat-row">
              <span>Files Uploaded:</span>
              <span>{{ quota.file_count }}</span>
            </div>
          </div>
        </div>

        <!-- System Stats / Placeholder -->
        <div class="card stats-card">
          <div class="card-header small">
            <h3>SYSTEM_STATUS</h3>
          </div>
          <div class="card-body">
            <div class="stat-row">
              <span>Server:</span>
              <span class="status-ok">ONLINE</span>
            </div>
             <div class="stat-row">
              <span>Latency:</span>
              <span>24ms</span>
            </div>
            <div class="stat-row">
              <span>Version:</span>
              <span>v1.0.0-beta</span>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Loading State -->
    <div v-else class="loading-state">
      <div class="loading-spinner"></div>
      <p>LOADING PROFILE DATA...</p>
    </div>

    <!-- Avatar Selection Modal -->
    <div v-if="showAvatarModal" class="modal-overlay" @click.self="showAvatarModal = false">
      <div class="modal-content card">
        <h3>SELECT AVATAR</h3>
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
        <button class="pixel-btn secondary full-width" @click="showAvatarModal = false">CLOSE</button>
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
  avatar_file_id: 0 // Default to 0 or current
});

// --- Mock Quota Data (If backend doesn't provide it yet) ---
const quota = computed<Quota>(() => {
  if (user.value?.quota) return user.value.quota;
  // Mock fallback
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
  { id: -1, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="#ef4444"><path d="M2 2h4v1h1v4h-1v1h-4v-1h-1v-4h1v-1z"/></svg>` },
  { id: -2, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="#3b82f6"><path d="M1 1h2v1h-1v1h-1v2h1v1h1v1h2v-1h1v-1h1v-2h-1v-1h-1v-1h-2z"/></svg>` },
  { id: -3, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="#10b981"><rect x="2" y="2" width="4" height="4"/><rect x="1" y="3" width="6" height="2"/><rect x="3" y="1" width="2" height="6"/></svg>` },
  { id: -4, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="#f59e0b"><path d="M0 0h2v2h2v-2h2v2h2v2h-2v2h2v2h-2v-2h-2v2h-2v-2h-2v-2h2v-2h-2z"/></svg>` },
  { id: -5, svg: `<svg viewBox="0 0 8 8" xmlns="http://www.w3.org/2000/svg" fill="#8b5cf6"><circle cx="4" cy="4" r="3"/></svg>` }
];

// --- Actions ---

const startEdit = () => {
  if (user.value) {
    editForm.name = user.value.name;
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
    // Update store locally
    userStore.user = updatedUser;
    ElMessage.success('PROFILE UPDATED');
    isEditing.value = false;
  } catch (e) {
    ElMessage.error('UPDATE FAILED');
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
  // showAvatarModal.value = false; // Optional: close on select or keep open
};

// --- Helpers ---

const formatBytes = (bytes: number, decimals = 2) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

const isSystemAvatar = (id: number) => {
  return id < 0;
};

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
/* Variables inherited from global styles (assumed) or redefined here */
.account-container {
  display: flex;
  justify-content: center;
  padding: 40px 20px;
  min-height: 80vh;
}

.account-layout {
  display: flex;
  gap: 24px;
  width: 100%;
  max-width: 1000px;
  flex-wrap: wrap;
}

/* Card Styles */
.card {
  background: white;
  border: 4px solid black;
  box-shadow: 8px 8px 0px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
}

.card-header {
  background: #f3f4f6;
  border-bottom: 4px solid black;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header.small {
  padding: 12px 16px;
}

.card-header h3 {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-weight: bold;
}

.profile-card {
  flex: 2;
  min-width: 300px;
}

.stats-column {
  flex: 1;
  min-width: 250px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stats-card {
  width: 100%;
}

.title {
  font-family: 'Courier New', monospace;
  margin: 0;
  font-size: 24px;
  font-weight: 900;
}

.status-badge {
  font-family: monospace;
  font-size: 12px;
  padding: 4px 8px;
  border: 2px solid black;
  background: #9ca3af;
  color: white;
  font-weight: bold;
}

.status-badge.active {
  background: #10b981;
}

.profile-body {
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Avatar */
.avatar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.pixel-avatar {
  width: 128px;
  height: 128px;
  background: #e5e7eb;
  border: 4px solid black;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  font-weight: bold;
  font-family: monospace;
  position: relative;
  overflow: hidden;
}

.pixel-avatar.editable {
  cursor: pointer;
}

.pixel-avatar.editable:hover .edit-overlay {
  opacity: 1;
}

.edit-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-svg {
  width: 100%;
  height: 100%;
}

.role-badge {
  font-family: monospace;
  font-weight: bold;
  background: black;
  color: white;
  padding: 2px 8px;
  font-size: 12px;
}

/* Info List */
.info-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  border-top: 2px dashed #ccc;
  border-bottom: 2px dashed #ccc;
  padding: 20px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: monospace;
  font-size: 16px;
}

.info-item label {
  color: #6b7280;
  font-weight: bold;
}

/* Bio */
.bio-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bio-section label {
  font-family: monospace;
  font-weight: bold;
  color: #6b7280;
}

.bio-content {
  font-family: monospace;
  white-space: pre-wrap;
  line-height: 1.5;
  background: #f9fafb;
  padding: 12px;
  border: 2px solid #e5e7eb;
}

/* Form Inputs */
.pixel-input {
  width: 100%;
  padding: 12px;
  border: 2px solid black;
  font-family: monospace;
  font-size: 16px;
  background: #fff;
  transition: all 0.2s;
}

.pixel-input:focus {
  background: #f0fdf4;
  outline: none;
  box-shadow: 4px 4px 0px rgba(0,0,0,0.1);
}

.pixel-input.small {
  padding: 6px;
}

/* Buttons */
.actions {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}

.pixel-btn {
  flex: 1;
  padding: 12px;
  font-family: monospace;
  font-weight: bold;
  text-transform: uppercase;
  border: 2px solid black;
  cursor: pointer;
  background: white;
  box-shadow: 4px 4px 0px black;
  transition: all 0.1s;
}

.pixel-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px black;
}

.pixel-btn:active:not(:disabled) {
  transform: translate(0, 0);
  box-shadow: 0 0 0 black;
}

.pixel-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

.pixel-btn.primary { background: #3b82f6; color: white; }
.pixel-btn.secondary { background: #e5e7eb; color: black; }
.pixel-btn.success { background: #10b981; color: white; }
.pixel-btn.danger { background: #ef4444; color: white; }
.pixel-btn.full-width { width: 100%; margin-top: 24px; }

/* Stats Card Styles */
.card-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.quota-visual {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-track {
  height: 24px;
  background: #e5e7eb;
  border: 2px solid black;
  width: 100%;
}

.progress-fill {
  height: 100%;
  background: #10b981; /* Green */
  border-right: 2px solid black;
  width: 0%;
  transition: width 0.5s ease-out;
}

.quota-text {
  display: flex;
  justify-content: space-between;
  font-family: monospace;
  font-size: 14px;
  font-weight: bold;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-family: monospace;
  font-size: 14px;
  border-bottom: 1px dashed #e5e7eb;
  padding-bottom: 4px;
}

.status-ok {
  color: #10b981;
  font-weight: bold;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-content {
  width: 90%;
  max-width: 400px;
  padding: 24px;
  background: white;
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 24px;
  text-align: center;
  font-family: monospace;
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
  gap: 16px;
}

.avatar-option {
  width: 64px;
  height: 64px;
  border: 2px solid #e5e7eb;
  cursor: pointer;
  padding: 4px;
  transition: all 0.2s;
}

.avatar-option:hover {
  transform: scale(1.1);
  border-color: #3b82f6;
}

.avatar-option.active {
  border-color: #3b82f6;
  background: #eff6ff;
  box-shadow: 0 0 0 2px #3b82f6;
}

.avatar-preview {
  width: 100%;
  height: 100%;
}

/* Responsive */
@media (max-width: 768px) {
  .account-layout {
    flex-direction: column;
  }
  
  .profile-card, .stats-column {
    min-width: 100%;
  }
}
</style>