import { createRouter, createWebHistory } from "vue-router";
import { useUserStore } from "@/store/user";

import AccountView from "@/views/AccountView.vue";
import ChatView from "@/views/ChatView.vue";
import FileListView from "@/views/FileListView.vue";
import CommunityView from "@/views/CommunityView.vue";
import NotFoundView from "@/views/NotFoundView.vue";
import LoginView from "@/views/LoginView.vue";
import RegisterView from "@/views/RegisterView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/files" },
    { 
      path: "/login", 
      name: "login", 
      component: LoginView, 
      meta: { title: "登录", public: true } 
    },
    { 
      path: "/register", 
      name: "register", 
      component: RegisterView, 
      meta: { title: "注册", public: true } 
    },
    { 
      path: "/files", 
      name: "files", 
      component: FileListView, 
      meta: { title: "文档库" } 
    },
    {
      path: "/chat/:id",
      name: "chat",
      component: ChatView,
      meta: { title: "智能问答" }
    },
    { 
      path: "/community", 
      name: "community", 
      component: CommunityView, 
      meta: { title: "社区广场" } 
    },
    { 
      path: "/account", 
      name: "account", 
      component: AccountView, 
      meta: { title: "账户管理" } 
    },
    { 
      path: "/:pathMatch(.*)*", 
      name: "notfound", 
      component: NotFoundView, 
      meta: { title: "404", public: true } 
    }
  ]
});

// Navigation Guard
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore();
  
  // Set document title
  document.title = `${to.meta.title} - NoteLLM` || "NoteLLM";

  // Check auth status if not already checked (e.g. page refresh)
  // 只有在认证状态未检查时才进行检查
  if (!userStore.authChecked) {
    await userStore.checkAuth();
  }

  const isPublic = to.meta.public;
  const isAuthenticated = userStore.isLoggedIn;

  if (!isPublic && !isAuthenticated) {
    // Redirect to login if trying to access protected route
    next({ name: 'login', query: { redirect: to.fullPath } });
  } else if ((to.name === 'login' || to.name === 'register') && isAuthenticated) {
    // Redirect to home if already logged in
    next({ name: 'files' });
  } else {
    next();
  }
});

export default router;
