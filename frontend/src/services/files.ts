import http from "@/services/http";
import type { ApiResponse, FileItem, PaginatedResponse, UploadProgress } from "@/services/types";

// File Service matching API Documentation 2.3

/**
 * Get Files List (Paged)
 * GET /files
 */
export const fetchFiles = async (params: { page?: number; size?: number; include_public?: boolean } = {}): Promise<PaginatedResponse<FileItem>> => {
  const { data } = await http.get<ApiResponse<PaginatedResponse<FileItem>>>("/files", { params });
  return data.data; 
};

/**
 * Get File Detail
 * GET /files/{id}
 */
export const fetchFileDetail = async (id: number | string): Promise<FileItem> => {
  const { data } = await http.get<ApiResponse<FileItem>>(`/files/${id}`);
  return data.data;
};

/**
 * Simple File Upload
 * POST /files
 */
export const uploadFile = async (
  file: File,
  onProgress?: (progress: UploadProgress) => void
): Promise<FileItem> => {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await http.post<ApiResponse<FileItem>>("/files", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (!onProgress) return;
      const total = event.total ?? 0;
      const percent = total ? Math.round((event.loaded / total) * 100) : 0;
      onProgress({ loaded: event.loaded, total, percent });
    },
  });
  return data.data;
};

/**
 * Delete File
 * DELETE /files/{id}
 */
export const deleteFile = async (id: number | string): Promise<void> => {
  await http.delete(`/files/${id}`);
};

// Public files if needed
export const fetchPublicFiles = async (params: { page?: number; size?: number } = {}): Promise<PaginatedResponse<FileItem>> => {
  const { data } = await http.get<ApiResponse<PaginatedResponse<FileItem>>>("/files/public", { params });
  return data.data;
};
