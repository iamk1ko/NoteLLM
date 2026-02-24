import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { getCurrentUser, login as apiLogin, logout as apiLogout, register as apiRegister } from '@/services/auth';
import type { LoginParams, RegisterParams, UserProfile } from '@/services/auth';

export const useUserStore = defineStore('user', () => {
  const user = ref<UserProfile | null>(null);
  const loading = ref(false);

  const isLoggedIn = computed(() => !!user.value);

  // Initial Check (Try to fetch user info on app load)
  async function checkAuth() {
    try {
      loading.value = true;
      const userData = await getCurrentUser();
      user.value = userData;
    } catch (error) {
      user.value = null;
    } finally {
      loading.value = false;
    }
  }

  async function login(params: LoginParams) {
    try {
      loading.value = true;
      const userData = await apiLogin(params);
      user.value = userData;
      return userData;
    } finally {
      loading.value = false;
    }
  }

  async function register(params: RegisterParams) {
    try {
      loading.value = true;
      const userData = await apiRegister(params);
      user.value = userData;
      return userData;
    } finally {
      loading.value = false;
    }
  }

  async function logout() {
    try {
      loading.value = true;
      await apiLogout();
    } finally {
      user.value = null;
      loading.value = false;
      // Clear any local storage if used (not used for auth token here, but maybe other prefs)
    }
  }

  return {
    user,
    loading,
    isLoggedIn,
    checkAuth,
    login,
    register,
    logout
  };
});
