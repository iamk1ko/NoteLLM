import {defineStore} from 'pinia';
import {computed, ref} from 'vue';
import type {LoginParams, RegisterParams, UserProfile} from '@/services/auth';
import {getCurrentUser, login as apiLogin, logout as apiLogout, register as apiRegister} from '@/services/auth';

export const useUserStore = defineStore('user', () => {
    const user = ref<UserProfile | null>(null);
    const loading = ref(false);
    const authChecked = ref(false); // 新增：标记是否已完成认证检查

    const isLoggedIn = computed(() => !!user.value);

    async function checkAuth() {
        // 如果正在检查中，等待完成
        if (loading.value) {
            return new Promise<void>((resolve) => {
                const checkInterval = setInterval(() => {
                    if (!loading.value) {
                        clearInterval(checkInterval);
                        resolve();
                    }
                }, 100);
            });
        }

        // 如果已检查过且有用户，直接返回
        if (authChecked.value && user.value) {
            return;
        }

        try {
            loading.value = true;
            user.value = await getCurrentUser();
        } catch (error: any) {
            if (error.response?.status === 401) {
                console.log('Session expired or invalid');
            }
            user.value = null;
        } finally {
            loading.value = false;
            authChecked.value = true;
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
        }
    }

    return {
        user,
        loading,
        authChecked,
        isLoggedIn,
        checkAuth,
        login,
        register,
        logout
    };
});
