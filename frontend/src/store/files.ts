import { defineStore } from "pinia";
import { fetchFileDetail, fetchFiles } from "@/services/files";
import type { FileItem } from "@/services/types";

/**
 * Files Store (Updated for API 2.3)
 */
interface FilesState {
  list: FileItem[]; // File List
  detail: FileItem | null; // Current selected file detail (same as FileItem in new API)
  loading: boolean;
  pagination: {
    page: number;
    size: number;
    total: number;
  };
}

export const useFilesStore = defineStore("files", {
  state: (): FilesState => ({
    list: [],
    detail: null,
    loading: false,
    pagination: {
      page: 1,
      size: 10,
      total: 0
    }
  }),
  actions: {
    /**
     * Load File List (Paged)
     */
    async loadFiles(params: { page?: number; size?: number; include_public?: boolean } = {}) {
      this.loading = true;
      try {
        const { items, total, page, size } = await fetchFiles(params);
        this.list = items;
        this.pagination = { page, size, total };
      } finally {
        this.loading = false;
      }
    },
    /**
     * Load Single File Detail
     * @param id File ID
     */
    async loadDetail(id: number | string) {
      this.loading = true;
      this.detail = null; 
      try {
        this.detail = await fetchFileDetail(id);
      } finally {
        this.loading = false;
      }
    },
    /**
     * Refresh Detail (Silent Update for Polling)
     */
    async refreshDetail(id: number | string) {
      // Updates detail without setting loading state or clearing previous detail
      try {
        this.detail = await fetchFileDetail(id);
      } catch (e) {
        console.error("Failed to refresh file detail", e);
      }
    }
  }
});
