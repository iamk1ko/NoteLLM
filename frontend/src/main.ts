import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";

import App from "@/App.vue";
import router from "@/router";
// 引入全局复古风格样式 (Pixel Art/Retro Style)
import "@/assets/styles/main.css";

// 创建Vue应用实例
const app = createApp(App);

// 注册状态管理 Pinia
app.use(createPinia());
// 注册路由
app.use(router);
// 注册UI组件库 ElementPlus (主要用于部分交互组件，如Upload)
app.use(ElementPlus);

// 挂载应用到 DOM
app.mount("#app");

