<template>
  <div class="notfound-container">
    <div class="card error-card">
      <h1 class="error-code">404</h1>
      <h3 class="error-title">页面丢失 PAGE_LOST</h3>
      <p class="error-desc">请求的资源在该扇区不可用 / SECTOR UNAVAILABLE</p>
      
      <button class="pixel-btn" @click="goHome">
        &lt; 返回基地 RETURN_BASE
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

const goHome = () => {
  router.push("/");
};
</script>

<style scoped>
.notfound-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.error-card {
  text-align: center;
  padding: 60px 40px;
  border: 4px solid var(--nl-border);
  box-shadow: 12px 12px 0px var(--nl-border);
  background: var(--nl-bg);
  max-width: 500px;
}

.error-code {
  font-family: var(--font-display);
  font-size: 80px;
  color: var(--nl-danger);
  margin: 0;
  line-height: 1;
  text-shadow: 4px 4px 0px rgba(0,0,0,0.1);
}

.error-title {
  font-family: var(--font-display);
  font-size: 24px;
  margin: 20px 0;
  color: var(--nl-text-main);
}

.error-desc {
  font-family: var(--font-body);
  font-size: 18px;
  color: var(--nl-text-secondary);
  margin-bottom: 40px;
}

.pixel-btn {
  font-family: var(--font-display);
  font-size: 16px;
  background: var(--nl-primary);
  color: white;
  border: 4px solid var(--nl-border);
  padding: 16px 32px;
  cursor: pointer;
  box-shadow: 4px 4px 0px var(--nl-border);
  transition: all 0.1s;
}

.pixel-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0px var(--nl-border);
  background: #4338ca;
}

.pixel-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 0px 0px 0px var(--nl-border);
}
</style>
