export const allowedExtensions = ["pdf", "md", "doc", "docx", "txt"];

export const validateFileType = (fileName: string): boolean => {
  const ext = fileName.split(".").pop()?.toLowerCase();
  if (!ext) return false;
  return allowedExtensions.includes(ext);
};
