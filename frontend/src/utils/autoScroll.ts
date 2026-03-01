import { nextTick, ref } from "vue";

type AutoScrollOptions = {
  threshold?: number;
};

export const createAutoScroll = (options: AutoScrollOptions = {}) => {
  const autoScrollEnabled = ref(true);
  const threshold = options.threshold ?? 120;

  const scrollToBottom = (el: HTMLElement | null) => {
    if (!autoScrollEnabled.value || !el) return;
    nextTick(() => {
      el.scrollTop = el.scrollHeight;
    });
  };

  const updateAutoScroll = (el: HTMLElement | null) => {
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    autoScrollEnabled.value = distance <= threshold;
  };

  return {
    autoScrollEnabled,
    scrollToBottom,
    updateAutoScroll
  };
};
