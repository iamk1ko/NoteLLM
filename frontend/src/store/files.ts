import { defineStore } from 'pinia'
import type { FileStorage, FileListResponse } from '@/services/files'

type FilesState = {
  items: FileStorage[]
  total: number
  page: number
  size: number
  loading: boolean
}

export const useFilesStore = defineStore('files', {
  state: (): FilesState => ({
    items: [],
    total: 0,
    page: 1,
    size: 10,
    loading: false,
  }),
  actions: {
    setList(payload: FileListResponse) {
      this.items = payload.items
      this.total = payload.total
      this.page = payload.page
      this.size = payload.size
    },
    setLoading(value: boolean) {
      this.loading = value
    },
  },
})
