<template>
  <div class="app-container">
    <nav class="navbar">
      <div class="navbar-content">
        <router-link to="/" class="brand">
          <div class="logo-icon">N</div>
          <span class="logo-text">NoteLLM</span>
        </router-link>

        <div class="nav-links">
          <router-link to="/files" class="nav-item">文档库</router-link>
          <router-link to="/community" class="nav-item">社区广场</router-link>
          <router-link to="/account" class="nav-item">用户中心</router-link>
          <a
            href="https://github.com/opencode/notellm"
            target="_blank"
            class="nav-icon"
            title="GitHub"
          >
            <!-- SVG Icon -->
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path>
            </svg>
          </a>
        </div>
      </div>
    </nav>

    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <div class="crt-overlay"></div> <!-- Retro CRT effect -->
  </div>
</template>

<script setup lang="ts">
// Logic here if needed
</script>

<style scoped>
/* Previous styles remain mostly same, adjusted for Chinese font rendering */
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  height: 72px;
  background: white;
  border-bottom: 4px solid black;
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.navbar-content {
  width: 100%;
  max-width: 100%;
  padding: 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
  text-decoration: none;
  color: black;
  font-family: var(--font-display);
  font-size: 20px;
  text-transform: uppercase;
  letter-spacing: -1px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: black;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 4px 4px 0px #ec4899; /* Pink shadow */
  border: 2px solid black;
}

.logo-text {
  text-shadow: 2px 2px 0px #e2e2e2;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 40px;
}

.nav-item {
  font-family: var(--font-display);
  font-size: 16px; /* Slightly larger for Chinese readability */
  color: #555;
  position: relative;
  text-decoration: none;
  padding: 6px 12px;
  border: 2px solid transparent;
  transition: all 0.1s;
}

.nav-item:hover,
.router-link-active {
  color: white;
  background: #10b981; /* Green highlight */
  border: 2px solid black;
  box-shadow: 4px 4px 0px black;
  transform: translate(-2px, -2px);
}

.nav-icon {
  color: black;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.1s;
}

.nav-icon:hover {
  transform: scale(1.1);
}

.main-content {
  flex: 1;
  width: 100%;
  max-width: 100%;
  margin: 0;
  padding: 40px;
}

/* CRT Scanline Effect */
.crt-overlay {
  pointer-events: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    rgba(18, 16, 16, 0) 50%,
    rgba(0, 0, 0, 0.05) 50%
  );
  background-size: 100% 4px;
  z-index: 999;
  opacity: 0.3;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s steps(5);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
