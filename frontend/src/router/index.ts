import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '@/views/UploadView.vue'
import FilesView from '@/views/FilesView.vue'
import SearchView from '@/views/SearchView.vue'

const routes = [
  {
    path: '/',
    redirect: '/upload',
  },
  {
    path: '/upload',
    name: 'Upload',
    component: UploadView,
  },
  {
    path: '/files',
    name: 'Files',
    component: FilesView,
  },
  {
    path: '/search',
    name: 'Search',
    component: SearchView,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
