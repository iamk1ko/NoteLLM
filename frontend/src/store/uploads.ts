import { defineStore } from "pinia";

import { uploadFile } from "@/services/files";
import type { FileItem, UploadProgress } from "@/services/types";

/**
 * 上传状态管理 (Upload Store)
 * 专门管理文件上传过程中的进度和状态
 */

interface UploadState {
  progress: UploadProgress | null; // 当前上传进度
  uploading: boolean; // 是否正在上传中
}

export const useUploadStore = defineStore("uploads", {
  state: (): UploadState => ({
    progress: null,
    uploading: false
  }),
  actions: {
    /**
     * 开始上传文件 (Start Upload Task)
     * @param file 用户选择的文件对象
     * @returns {Promise<FileItem>} 上传成功后的文件信息
     */
    async startUpload(file: File): Promise<FileItem> {
      this.uploading = true;
      this.progress = { loaded: 0, total: file.size, percent: 0 }; // 初始化进度
      
      try {
        const result = await uploadFile(file, (progress) => {
          // 实时更新进度状态
          this.progress = progress;
        });
        return result;
      } catch (error) {
        // 上传失败时抛出错误供组件捕获
        throw error;
      } finally {
        this.uploading = false;
      }
    },
    /**
     * 重置上传状态 (Reset State)
     * 用于上传完成后或重新选择文件时
     */
    reset() {
      this.progress = null;
      this.uploading = false;
    }
  }
});
