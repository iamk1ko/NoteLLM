<template>
  <div class="card status">
    <div class="status__header">
      <h3 class="section-title">SYSTEM_STATUS</h3>
      <span class="pill pill--success">ONLINE</span>
    </div>
    <div class="status__items">
      <div class="status__item">
        <p class="status__label">FILES</p>
        <p class="status__value">{{ stats.totalFiles }}</p>
      </div>
      <div class="status__item">
        <p class="status__label">VECTORS</p>
        <p class="status__value">{{ stats.vectorized }}</p>
      </div>
      <div class="status__item">
        <p class="status__label">QUERIES</p>
        <p class="status__value">{{ stats.qaCount }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  stats: {
    totalFiles: number;
    vectorized: number;
    qaCount: number;
  };
}>();
</script>

<style scoped>
.status {
  background: var(--nl-surface);
  border: 4px solid var(--nl-border);
  box-shadow: 4px 4px 0px var(--nl-border);
}

.status__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 2px solid var(--nl-border);
  padding-bottom: 8px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 14px;
  color: var(--nl-text-main);
  margin: 0;
}

.status__items {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.status__item {
  border: 2px solid var(--nl-border);
  padding: 8px;
  text-align: center;
  background: var(--nl-bg);
}

.status__label {
  margin: 0;
  font-family: var(--font-display);
  font-size: 10px;
  color: var(--nl-text-secondary);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.status__value {
  margin: 0;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 24px;
  color: var(--nl-primary);
}

@media (max-width: 960px) {
  .status__items {
    grid-template-columns: 1fr;
  }
}
</style>
