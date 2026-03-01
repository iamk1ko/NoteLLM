import { defineStore } from "pinia";
import {
  createSession,
  fetchSessions,
  sendMessageStream,
  fetchMessages
} from "@/services/qa";
import type { MessageItem, SessionItem } from "@/services/types";
import { createStreamFlusher } from "@/utils/streaming";

interface QaState {
  sessionId: number | null; // Current active session ID
  records: MessageItem[];   // Messages for the current session
  loading: boolean;
}

export const useQaStore = defineStore("qa", {
  state: (): QaState => ({
    sessionId: null,
    records: [],
    loading: false
  }),
  actions: {
    /**
     * Load History for a specific file (context)
     * 1. Try to find an existing session for this file.
     * 2. If not found, create a new session.
     * 3. Fetch messages for that session.
     */
    async loadHistory(fileId: string) {
      this.loading = true;
      this.sessionId = null;
      this.records = [];
      
      try {
        // 1. Find existing session (very simplified: check first page)
        // Ideally backend should support filtering by context_id
        const sessions = await fetchSessions({ size: 100 }); 
        const existingSession = sessions.items.find(s => String(s.context_id) === String(fileId));
        
        if (existingSession) {
          this.sessionId = existingSession.id;
        } else {
          // 2. Create new session
          const newSession = await createSession({
            title: `File Chat ${fileId}`,
            biz_type: "ai_chat",
            context_id: String(fileId)
          });
          this.sessionId = newSession.id;
        }
        
        // 3. Fetch messages
        if (this.sessionId) {
          await this.refreshMessages();
        }
      } catch (error) {
        console.error("Failed to load QA history:", error);
      } finally {
        this.loading = false;
      }
    },

    /**
     * Refresh messages for current session
     */
    async refreshMessages() {
      if (!this.sessionId) return;
      const msgs = await fetchMessages(this.sessionId, { size: 100 });
      // Sort by create_time ascending for chat view
      this.records = msgs.items.sort((a, b) => 
        new Date(a.create_time).getTime() - new Date(b.create_time).getTime()
      );
    },
    
    /**
     * Send Question
     */
    async sendQuestion(question: string, fileId?: string) {
      if (!this.sessionId && fileId) {
        await this.loadHistory(fileId);
      }
      if (!this.sessionId) return;

      this.loading = true;
      try {
        const now = new Date().toISOString();
        // 这里生成临时消息，确保用户体验流畅且不依赖后端立即返回
        const userMsg: MessageItem = {
          id: Date.now(),
          session_id: this.sessionId,
          user_id: 0,
          role: "user",
          content: question,
          create_time: now,
        };
        this.records.push(userMsg);

        // AI 消息占位，内容将通过流式输出逐步拼接
        const aiMsg: MessageItem = {
          id: Date.now() + 1,
          session_id: this.sessionId,
          user_id: 0,
          role: "assistant",
          content: "",
          create_time: now,
        };
        this.records.push(aiMsg);

        // 使用统一的流式缓冲器控制刷新频率，避免频繁触发响应式更新
        const flusher = createStreamFlusher({
          onFlush: (chunk) => {
            aiMsg.content += chunk;
            this.records = [...this.records];
          }
        });

        await sendMessageStream(
          this.sessionId,
          question,
          (chunk) => {
            // 累积片段，达到阈值或间隔后统一刷新
            flusher.push(chunk);
          },
          async () => {
            flusher.flush();
            this.loading = false;
            await this.refreshMessages();
          },
          (error) => {
            flusher.flush();
            this.loading = false;
            aiMsg.content += `\n\n[Error: ${error}]`;
          }
        );
      } finally {
        this.loading = false;
      }
    }
  }
});
