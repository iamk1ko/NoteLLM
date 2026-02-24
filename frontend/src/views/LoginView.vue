<template>
  <div class="auth-container">
    <div class="auth-card card fade-in">
      <div class="auth-header">
        <h2 class="section-title"> > 用户登录_</h2>
      </div>

      <form @submit.prevent="handleSubmit" class="auth-form">
        <div class="form-group">
          <label class="form-label">用户名 / 邮箱</label>
          <input 
            v-model="form.username_or_email" 
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

        <button type="submit" class="pixel-btn submit-btn" :disabled="loading">
          <span v-if="!loading">登录</span>
          <span v-else>登录中...</span>
        </button>

        <div class="auth-footer">
          <p>没有账号? <router-link to="/register">立即注册</router-link></p>
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
  username_or_email: '',
  password: ''
});

const loading = ref(false);

const handleSubmit = async () => {
  if (!form.username_or_email || !form.password) return;

  try {
    loading.value = true;
    await userStore.login(form);
    ElMessage.success('登录成功');
    router.push('/files');
  } catch (error: any) {
    const msg = error.response?.data?.detail || '登录失败，请检查用户名或密码';
    ElMessage.error(msg);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
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
