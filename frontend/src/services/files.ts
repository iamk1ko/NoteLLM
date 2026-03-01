import http from "@/services/http";
import type { ApiResponse, FileItem, PaginatedResponse, UploadProgress, ChunkUploadResponse } from "@/services/types";
import SparkMD5 from "spark-md5";

// File Service matching API Documentation 2.3

// Helper: Calculate File MD5
const calculateMD5 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const chunkSize = 2097152; // 2MB
    const chunks = Math.ceil(file.size / chunkSize);
    let currentChunk = 0;
    const spark = new SparkMD5.ArrayBuffer();
    const fileReader = new FileReader();

    fileReader.onload = function (e) {
      spark.append(e.target?.result as ArrayBuffer);
      currentChunk++;

      if (currentChunk < chunks) {
        loadNext();
      } else {
        resolve(spark.end());
      }
    };

    fileReader.onerror = function () {
      reject("MD5 calculation failed");
    };

    function loadNext() {
      const start = currentChunk * chunkSize;
      const end = ((start + chunkSize) >= file.size) ? file.size : start + chunkSize;
      fileReader.readAsArrayBuffer(file.slice(start, end));
    }

    loadNext();
  });
};

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
 * API Response: { code: 0, data: { file: FileItem, progress: {...} } }
 */
export const fetchFileDetail = async (id: number | string): Promise<FileItem> => {
  const { data } = await http.get<ApiResponse<{ file: FileItem }>>(`/files/${id}`);
  return data.data.file;
};

/**
 * Get File Preview URL
 * GET /files/{id}/preview
 */
export const getFilePreview = async (id: number | string): Promise<string> => {
  const { data } = await http.get<ApiResponse<{ url: string }>>(`/files/${id}/preview`);
  return data.data.url;
};

/**
 * Upload Chunk
 * POST /files/upload/chunk
 */
const uploadChunk = async (formData: FormData): Promise<ChunkUploadResponse> => {
  // The backend expects multipart form data
  // We don't need to set Content-Type manually, axios/browser does it with boundary
  // But wait, my code explicitly sets it:
  // headers: { "Content-Type": "multipart/form-data" },
  // This is actually BAD practice with axios + FormData because it might miss the boundary.
  // Axios usually handles it if you pass FormData.
  // Let's remove the explicit header.
  const { data } = await http.post<ApiResponse<ChunkUploadResponse>>("/files/upload/chunk", formData);
  return data.data;
};

/**
 * Check Upload Completion
 * GET /files/upload/is_complete/{fileId}
 */
const checkUploadComplete = async (fileId: number): Promise<FileItem | null> => {
  try {
    const { data } = await http.get<ApiResponse<FileItem>>(`/files/upload/is_complete/${fileId}`);
    return data.data;
  } catch (e) {
    return null;
  }
};

/**
 * Upload File (Smart: Chunked)
 */
export const uploadFile = async (
  file: File,
  onProgress?: (progress: UploadProgress) => void,
  onStatusChange?: (status: 'uploading' | 'merging' | 'vectorizing' | 'completed' | 'failed') => void
): Promise<FileItem> => {
  // 1. Calculate MD5
  if (onStatusChange) onStatusChange('uploading');
  const fileMd5 = await calculateMD5(file);

  // 2. Chunk Configuration
  const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
  const totalSize = file.size;
  const totalChunks = Math.ceil(totalSize / CHUNK_SIZE);
  const fileName = file.name;

  // 3. Determine Content Type
  // Fix for markdown files appearing as octet-stream
  let contentType = file.type;
  if (!contentType || contentType === 'application/octet-stream') {
     if (fileName.toLowerCase().endsWith(".md")) contentType = "text/markdown";
     else if (fileName.toLowerCase().endsWith(".pdf")) contentType = "application/pdf";
     else if (fileName.toLowerCase().endsWith(".txt")) contentType = "text/plain";
  }

  let fileId: number | undefined;

  // 4. Upload Chunks Loop
  for (let i = 0; i < totalChunks; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, totalSize);
    const chunkBlob = file.slice(start, end);

    const formData = new FormData();
    formData.append("file_md5", fileMd5);
    formData.append("chunk_index", i.toString());
    formData.append("total_chunks", totalChunks.toString());
    formData.append("chunk_size", (end - start).toString());
    formData.append("total_size", totalSize.toString());
    formData.append("file_name", fileName);
    formData.append("content_type", contentType || "application/octet-stream"); // Fallback
    formData.append("is_public", "false");
    formData.append("file_chunk", chunkBlob, fileName); 

    const res = await uploadChunk(formData);
    
    if (res.file_id) {
      fileId = res.file_id;
    }

    if (onProgress) {
      const percent = Math.round(((i + 1) / totalChunks) * 100);
      onProgress({ loaded: end, total: totalSize, percent });
    }
  }

  if (!fileId) {
    throw new Error("Upload failed: No file ID returned from server.");
  }

  // 5. Poll for Completion (Wait for Merge & Vectorization)
  if (onStatusChange) onStatusChange('merging');
  
  // Optimization: Vectorization now happens very quickly via remote API (~1-2s).
  // Strategy: Start polling almost immediately with a short interval, then back off slightly.
  
  // Step A: Minimal initial wait
  await new Promise(r => setTimeout(r, 500)); 

  let delay = 500; // Start with 500ms interval
  const maxDelay = 3000; // Cap at 3s interval
  const maxTime = 180000; // 3 minutes timeout
  let elapsedTime = 0;

  while (elapsedTime < maxTime) {
     // Check status
     const fileObj = await checkUploadComplete(fileId);
     
     if (fileObj) {
       // Status: 2=Embedded(Success), 3=Failed
       if (fileObj.status === 2) {
         if (onStatusChange) onStatusChange('completed');
         return fileObj;
       }
       
       if (fileObj.status === 3) {
         if (onStatusChange) onStatusChange('failed');
         throw new Error("Upload failed: Server processing error.");
       }

       // Status: 1=Uploaded(Merging/Vectorizing)
       if (fileObj.status === 1) {
         if (onStatusChange) onStatusChange('vectorizing');
       }
     }

     // Wait for next poll
     await new Promise(r => setTimeout(r, delay));
     elapsedTime += delay;

     // Adaptive backoff: Increase delay slightly each time
     delay = Math.min(delay + 500, maxDelay);
  }

  throw new Error("Upload timeout: File processing taking too long.");
};

/**
 * Delete File
 * DELETE /files/{id}
 */
export const deleteFile = async (id: number | string): Promise<void> => {
  await http.delete(`/files/${id}`);
};

/**
 * Re-vectorize File (Retry)
 * POST /files/{id}/retry
 */
export const reVectorizeFile = async (id: number | string): Promise<void> => {
  const { data } = await http.post<ApiResponse<{ success: boolean }>>(`/files/${id}/retry`);
  return data.data;
};

// Public files if needed
export const fetchPublicFiles = async (params: { page?: number; size?: number } = {}): Promise<PaginatedResponse<FileItem>> => {
  const { data } = await http.get<ApiResponse<PaginatedResponse<FileItem>>>("/files/public", { params });
  return data.data;
};
