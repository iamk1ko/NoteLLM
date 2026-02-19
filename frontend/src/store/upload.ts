import { defineStore } from 'pinia'

export type UploadTask = {
  id: string
  name: string
  size: number
  md5: string
  totalChunks: number
  uploadedChunks: number
  progress: number
  status: 'waiting' | 'uploading' | 'completed' | 'failed'
  error?: string
  fileId?: number
}

type UploadState = {
  tasks: UploadTask[]
}

export const useUploadStore = defineStore('upload', {
  state: (): UploadState => ({
    tasks: [],
  }),
  actions: {
    addTask(task: UploadTask) {
      this.tasks = [task, ...this.tasks]
    },
    updateTask(id: string, patch: Partial<UploadTask>) {
      const index = this.tasks.findIndex((task) => task.id === id)
      if (index === -1) return
      this.tasks[index] = { ...this.tasks[index], ...patch }
    },
    clearCompleted() {
      this.tasks = this.tasks.filter((task) => task.status !== 'completed')
    },
  },
})
