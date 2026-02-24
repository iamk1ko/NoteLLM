<template>
  <div class="auth-container">
    <div class="auth-card card fade-in">
      <div class="auth-header">
        <h2 class="section-title"> > 用户注册_</h2>
      </div>

      <form @submit.prevent="handleSubmit" class="auth-form">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input 
            v-model="form.username" 
            type="text" 
            class="pixel-input" 
            placeholder="USER_ID"
            required
            autofocus
          />
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <input 
            v-model="form.password" 
            type="password" 
            class="pixel-input" 
            placeholder="PASSWORD"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">确认密码</label>
          <input 
            v-model="form.confirmPassword" 
            type="password" 
            class="pixel-input" 
            placeholder="CONFIRM PASSWORD"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">昵称 (Name)</label>
          <input 
            v-model="form.name" 
            type="text" 
            class="pixel-input" 
            placeholder="DISPLAY NAME"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">邮箱 (可选)</label>
          <input 
            v-model="form.email" 
            type="email" 
            class="pixel-input" 
            placeholder="EMAIL@EXAMPLE.COM"
          />
        </div>

        <button type="submit" class="pixel-btn submit-btn" :disabled="loading">
          <span v-if="!loading">注册</span>
          <span v-else>注册中...</span>
        </button>

        <div class="auth-footer">
          <p>已有账号? <router-link to="/login">直接登录</router-link></p>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/store/user';
import { ElMessage } from 'element-plus';

const router = useRouter();
const userStore = useUserStore();

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  name: '',
  email: ''
});

const loading = ref(false);

const handleSubmit = async () => {
  if (form.password !== form.confirmPassword) {
    ElMessage.error('两次密码输入不一致');
    return;
  }

  try {
    loading.value = true;
    await userStore.register({
      username: form.username,
      password: form.password,
      name: form.name,
      email: form.email || undefined
    });
    ElMessage.success('注册成功，请登录');
    router.push('/login');
  } catch (error: any) {
    const msg = error.response?.data?.detail || '注册失败，请重试';
    ElMessage.error(msg);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* Reuse styles from LoginView via scoped copy or common CSS, copying for now for isolation */
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 152px);
  padding: 20px;
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: var(--nl-bg);
  border: 4px solid var(--nl-border);
  box-shadow: 8px 8px 0px var(--nl-border);
  padding: 40px;
}

.auth-header {
  margin-bottom: 32px;
  text-align: center;
  border-bottom: 4px solid var(--nl-border);
  padding-bottom: 16px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 24px;
  color: var(--nl-text-main);
  text-transform: uppercase;
  margin: 0;
}

.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  font-family: var(--font-display);
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--nl-text-main);
  text-transform: uppercase;
}

.pixel-input {
  width: 100%;
  padding: 12px;
  font-family: var(--font-body);
  font-size: 16px;
  border: 4px solid var(--nl-border);
  background: var(--nl-surface);
  color: var(--nl-text-main);
  outline: none;
  box-shadow: inset 4px 4px 0px rgba(0,0,0,0.05);
  transition: all 0.1s;
}

.pixel-input:focus {
  border-color: var(--nl-primary);
  background: white;
}

.submit-btn {
  width: 100%;
  margin-top: 16px;
  font-family: var(--font-display);
  font-size: 16px;
  background: var(--nl-primary);
  color: white;
  border: 4px solid var(--nl-border);
  padding: 16px;
  cursor: pointer;
  box-shadow: 4px 4px 0px var(--nl-border);
  transition: all 0.1s;
  text-transform: uppercase;
}

.submit-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px var(--nl-border);
  background: #4338ca;
}

.submit-btn:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 0px 0px 0px var(--nl-border);
}

.submit-btn:disabled {
  background: var(--nl-text-secondary);
  cursor: not-allowed;
  opacity: 0.7;
}

.auth-footer {
  margin-top: 24px;
  text-align: center;
  font-family: var(--font-body);
  font-size: 14px;
}

.auth-footer a {
  color: var(--nl-primary);
  text-decoration: none;
  font-weight: bold;
}

.auth-footer a:hover {
  text-decoration: underline;
}
</style>
