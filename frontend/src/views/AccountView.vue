<template>
  <div class="account-container">
    <div class="card account-card fade-in">
      <div class="card-header">
        <h2 class="section-title">> 用户中心_</h2>
        <span class="system-id">ID: 0x1A4F</span>
      </div>

      <div class="profile-section">
        <div class="avatar-box">
          <div class="pixel-avatar">
            <div class="face">
              <div class="eye left"></div>
              <div class="eye right"></div>
              <div class="mouth"></div>
            </div>
          </div>
          <div class="user-badge">ADMIN</div>
        </div>
        
        <div class="user-info">
          <div class="info-row">
            <span class="label">用户名称:</span>
            <span class="value">管理员 (Administrator)</span>
          </div>
          <div class="info-row">
            <span class="label">当前权限:</span>
            <span class="value highlight">LEVEL 99</span>
          </div>
          <div class="info-row">
            <span class="label">注册时间:</span>
            <span class="value">2024-01-01</span>
          </div>
        </div>
      </div>

      <div class="dashboard-grid">
        <!-- Storage Status -->
        <div class="status-panel">
          <h3 class="panel-title">存储空间 STORAGE</h3>
          <div class="storage-visual">
            <div class="progress-bar">
              <div class="progress-fill" style="width: 35%"></div>
            </div>
            <div class="storage-text">
              <span>已用: 350MB</span>
              <span>总量: 1GB</span>
            </div>
          </div>
        </div>

        <!-- System Status -->
        <div class="status-panel">
          <h3 class="panel-title">系统状态 SYSTEM</h3>
          <div class="system-check">
            <div class="check-item">
              <span class="indicator on"></span>
              <span>API 连接正常</span>
            </div>
            <div class="check-item">
              <span class="indicator on"></span>
              <span>向量数据库在线</span>
            </div>
            <div class="check-item">
              <span class="indicator on"></span>
              <span>文件系统读写就绪</span>
            </div>
          </div>
        </div>
      </div>

      <div class="actions-section">
        <button class="pixel-btn warning">
          重置缓存 CLEAR_CACHE
        </button>
        <button class="pixel-btn danger">
          登出系统 LOGOUT
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// No logic needed for this mock view yet
</script>

<style scoped>
.account-container {
  display: flex;
  justify-content: center;
  padding: 40px 20px;
  min-height: calc(100vh - 152px); /* Full height minus header/padding */
}

.account-card {
  width: 100%;
  max-width: 800px;
  background: var(--nl-bg);
  border: 4px solid var(--nl-border);
  box-shadow: 8px 8px 0px var(--nl-border);
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 4px solid var(--nl-border);
  padding-bottom: 16px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 24px;
  color: var(--nl-text-main);
}

.system-id {
  font-family: var(--font-body);
  background: var(--nl-text-main);
  color: var(--nl-bg);
  padding: 4px 8px;
  font-size: 14px;
}

/* Profile Section */
.profile-section {
  display: flex;
  gap: 32px;
  align-items: center;
  background: var(--nl-surface);
  border: 2px solid var(--nl-border);
  padding: 24px;
  box-shadow: 4px 4px 0px var(--nl-border);
}

.avatar-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.pixel-avatar {
  width: 80px;
  height: 80px;
  background: var(--nl-primary);
  border: 4px solid var(--nl-border);
  position: relative;
}

.face {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
}

.eye {
  position: absolute;
  width: 8px;
  height: 8px;
  background: white;
  top: 24px;
}
.eye.left { left: 20px; }
.eye.right { right: 20px; }

.mouth {
  position: absolute;
  width: 24px;
  height: 4px;
  background: white;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
}

.user-badge {
  background: var(--nl-accent);
  color: white;
  font-family: var(--font-display);
  font-size: 12px;
  padding: 2px 6px;
  border: 2px solid var(--nl-border);
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-body);
  font-size: 18px;
  border-bottom: 1px dashed var(--nl-border);
  padding-bottom: 4px;
}

.info-row:last-child {
  border-bottom: none;
}

.label {
  color: var(--nl-text-secondary);
  width: 100px;
}

.value {
  color: var(--nl-text-main);
  font-weight: bold;
}

.highlight {
  color: var(--nl-primary);
}

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

@media (max-width: 600px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  .profile-section {
    flex-direction: column;
    text-align: center;
  }
}

.status-panel {
  background: var(--nl-surface);
  border: 2px solid var(--nl-border);
  padding: 16px;
}

.panel-title {
  font-family: var(--font-display);
  font-size: 14px;
  background: var(--nl-text-main);
  color: white;
  display: inline-block;
  padding: 4px 8px;
  margin: -24px 0 16px -8px; /* Offset title style */
  box-shadow: 4px 4px 0px rgba(0,0,0,0.2);
}

/* Storage Visual */
.storage-visual {
  margin-top: 8px;
}

.progress-bar {
  height: 24px;
  background: var(--nl-bg);
  border: 2px solid var(--nl-border);
  margin-bottom: 8px;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: var(--nl-primary);
  background-image: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 5px,
    rgba(255,255,255,0.2) 5px,
    rgba(255,255,255,0.2) 10px
  );
}

.storage-text {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-display);
  font-size: 12px;
  color: var(--nl-text-secondary);
}

/* System Check */
.system-check {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-body);
  font-size: 16px;
}

.indicator {
  width: 12px;
  height: 12px;
  border: 2px solid var(--nl-border);
  background: var(--nl-bg);
}

.indicator.on {
  background: var(--nl-accent);
  box-shadow: 0 0 4px var(--nl-accent);
}

/* Actions */
.actions-section {
  display: flex;
  gap: 16px;
  justify-content: flex-end;
  border-top: 4px solid var(--nl-border);
  padding-top: 24px;
}

.pixel-btn {
  font-family: var(--font-display);
  font-size: 14px;
  border: 2px solid var(--nl-border);
  padding: 10px 20px;
  cursor: pointer;
  box-shadow: 4px 4px 0px var(--nl-border);
  background: var(--nl-surface);
  transition: all 0.1s;
}

.pixel-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px var(--nl-border);
}

.pixel-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 0px 0px 0px var(--nl-border);
}

.pixel-btn.warning {
  background: var(--nl-warning);
  color: black;
}

.pixel-btn.danger {
  background: var(--nl-danger);
  color: white;
}
</style>