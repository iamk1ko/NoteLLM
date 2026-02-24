import { createRouter, createWebHistory } from "vue-router";

import AccountView from "@/views/AccountView.vue";
import ChatView from "@/views/ChatView.vue";
import FileListView from "@/views/FileListView.vue";
import CommunityView from "@/views/CommunityView.vue"; // Add import
import NotFoundView from "@/views/NotFoundView.vue";
import UploadView from "@/views/UploadView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/files" },
    { path: "/upload", name: "upload", component: UploadView, meta: { title: "文件上传" } },
    { path: "/files", name: "files", component: FileListView, meta: { title: "文档库" } },
    {
      path: "/chat/:id",
      name: "chat",
      component: ChatView,
      meta: { title: "智能问答" }
    },
    { path: "/community", name: "community", component: CommunityView, meta: { title: "社区广场" } }, // Add route
    { path: "/account", name: "account", component: AccountView, meta: { title: "账户管理" } },
    { path: "/:pathMatch(.*)*", name: "notfound", component: NotFoundView, meta: { title: "404" } }
  ]
});

export default router;
