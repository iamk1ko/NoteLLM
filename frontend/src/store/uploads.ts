import { defineStore } from "pinia";

import { uploadFile } from "@/services/files";
import type { FileItem, UploadProgress } from "@/services/types";

export type UploadStatus = 'idle' | 'uploading' | 'merging' | 'vectorizing' | 'completed' | 'failed';

interface UploadState {
  progress: UploadProgress | null;
  uploading: boolean;
  status: UploadStatus;
}

export const useUploadStore = defineStore("uploads", {
  state: (): UploadState => ({
    progress: null,
    uploading: false,
    status: 'idle'
  }),
  actions: {
    async startUpload(file: File): Promise<FileItem> {
      this.uploading = true;
      this.status = 'uploading';
      this.progress = { loaded: 0, total: file.size, percent: 0 };
      
      try {
        const result = await uploadFile(
          file, 
          (progress) => {
            this.progress = progress;
            if (progress.percent === 100 && this.status === 'uploading') {
              this.status = 'merging';
            }
          },
          (status) => {
            // Map service status to store status (they are compatible strings mostly)
            this.status = status as UploadStatus;
          }
        );
        this.status = 'completed';
        return result;
      } catch (error) {
        this.status = 'failed';
        throw error;
      } finally {
        this.uploading = false;
      }
    },
    reset() {
      this.progress = null;
      this.uploading = false;
      this.status = 'idle';
    }
  }
});
