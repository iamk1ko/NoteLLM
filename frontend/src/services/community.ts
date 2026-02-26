import http from "@/services/http";
import type { ApiResponse } from "@/services/types";

export interface CommunityShare {
  id: number;
  title: string;
  description: string;
  tags: string[];
  user_id: number;
  user_name?: string; // Optional: Backend might join this
  view_count: number;
  like_count: number;
  fork_count: number;
  create_time: string;
  is_liked?: boolean; // Current user liked status
}

export interface PublishSharePayload {
  source_file_id: number;
  session_id: number;
  title: string;
  description?: string;
  tags?: string[];
  is_public_source?: boolean;
}

export interface ShareListParams {
  page?: number;
  size?: number;
  sort?: "latest" | "popular";
  tag?: string;
}

export const communityService = {
  // Get list of shared items
  getShares: async (params: ShareListParams = {}) => {
    const { data } = await http.get<ApiResponse<{ items: CommunityShare[]; total: number }>>("/shares", { params });
    return data.data;
  },

  // Publish a share
  publishShare: async (payload: PublishSharePayload) => {
    const { data } = await http.post<ApiResponse<{ share_id: number; publish_time: string }>>("/shares", payload);
    return data.data;
  },

  // Fork a share
  forkShare: async (shareId: number) => {
    const { data } = await http.post<ApiResponse<{ new_file_id: number; new_session_id: number }>>(
      `/shares/${shareId}/fork`
    );
    return data.data;
  },

  // Like/Unlike
  likeShare: async (shareId: number, action: "like" | "unlike") => {
    const { data } = await http.post<ApiResponse<{ success: boolean; like_count: number }>>(
      `/shares/${shareId}/like`, 
      { action }
    );
    return data.data;
  },
  
  // Generate Summary (Note feature)
  generateSummary: async (sessionId: number, focusTopics?: string[]) => {
    const { data } = await http.post<ApiResponse<{ summary_content: string; created_at: string }>>(
      `/sessions/${sessionId}/summary`, 
      { focus_topics: focusTopics }
    );
    return data.data;
  }
};
