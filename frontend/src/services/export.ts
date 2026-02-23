import http from "@/services/http";

export const exportQaPdf = async (payload: { fileId?: string; range?: string }) => {
  const { data } = await http.post("/export/qa", payload, {
    responseType: "blob"
  });
  return data as Blob;
};
