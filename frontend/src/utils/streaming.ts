type StreamFlusherOptions = {
  flushInterval?: number;
  flushThreshold?: number;
  onFlush: (chunk: string) => void;
};

export const createStreamFlusher = (options: StreamFlusherOptions) => {
  const flushInterval = options.flushInterval ?? 16;
  const flushThreshold = options.flushThreshold ?? 80;

  let pending = "";
  let flushTimer: ReturnType<typeof setTimeout> | null = null;

  const flushPending = () => {
    if (!pending) return;
    options.onFlush(pending);
    pending = "";
  };

  const clearTimer = () => {
    if (!flushTimer) return;
    clearTimeout(flushTimer);
    flushTimer = null;
  };

  return {
    // 接收流式片段，按阈值/时间批量刷新
    push(chunk: string) {
      pending += chunk;
      if (pending.length >= flushThreshold) {
        clearTimer();
        flushPending();
        return;
      }
      if (!flushTimer) {
        flushTimer = setTimeout(() => {
          flushTimer = null;
          flushPending();
        }, flushInterval);
      }
    },
    // 流式结束或出错时强制刷新剩余内容
    flush() {
      clearTimer();
      flushPending();
    }
  };
};
