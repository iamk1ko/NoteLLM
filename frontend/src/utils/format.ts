import dayjs from "dayjs";

export const formatSize = (bytes: number | undefined | null): string => {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
};

export const formatTime = (value: string | number | Date | undefined | null): string => {
  if (!value) return "-";
  return dayjs(value).format("YYYY-MM-DD HH:mm");
};
