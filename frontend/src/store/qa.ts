import { defineStore } from "pinia";
import { 
  createSession, 
  fetchSessions, 
  sendMessage, 
  fetchMessages 
} from "@/services/qa";
import type { MessageItem, SessionItem } from "@/services/types";

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
        // 1. Send User Message
        await sendMessage(this.sessionId, question);
        
        // 2. Poll for Assistant Message (Simple polling for now)
        // In a real app, use SSE or WebSocket. Here we just wait a bit and refresh.
        await this.refreshMessages();
        
        // Polling logic: Check if last message is from user. If so, wait and refresh again.
        let attempts = 0;
        while (attempts < 10) {
          const lastMsg = this.records[this.records.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            break; 
          }
          await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1s
          await this.refreshMessages();
          attempts++;
        }
      } finally {
        this.loading = false;
      }
    }
  }
});
