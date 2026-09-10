import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const http = axios.create({ baseURL: API });

export const api = {
  uploadPdf: async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    const { data } = await http.post("/projects/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
  createSample: async () => (await http.post("/projects/sample")).data,
  analyze: async (pid, { templateId, useAi = true, granularity = "detail" } = {}) =>
    (await http.post(`/projects/${pid}/analyze`, null, {
      params: { ...(templateId ? { template_id: templateId } : {}), use_ai: useAi, granularity },
      timeout: 600000,
    })).data,
  getProject: async (pid) => (await http.get(`/projects/${pid}`)).data,
  listProjects: async () => (await http.get("/projects")).data,
  deleteProject: async (pid) => (await http.delete(`/projects/${pid}`)).data,
  updateDocuments: async (pid, documents) =>
    (await http.put(`/projects/${pid}/documents`, { documents })).data,
  split: async (pid) => (await http.post(`/projects/${pid}/split`)).data,
  listTemplates: async () => (await http.get("/templates")).data,
  createTemplate: async (t) => (await http.post("/templates", t)).data,
  updateTemplate: async (id, t) => (await http.put(`/templates/${id}`, t)).data,
  deleteTemplate: async (id) => (await http.delete(`/templates/${id}`)).data,
  pageImageUrl: (pid, page) => `${API}/projects/${pid}/page/${page}`,
  originalPdfUrl: (pid) => `${API}/projects/${pid}/original.pdf`,
  outputUrl: (pid, filename, download = false) =>
    `${API}/projects/${pid}/output/${encodeURIComponent(filename)}${download ? "?download=true" : ""}`,
  zipUrl: (pid) => `${API}/projects/${pid}/download-zip`,
};

export const fmtBytes = (b) => {
  if (!b) return "0 B";
  const u = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(b) / Math.log(1024));
  return `${(b / Math.pow(1024, i)).toFixed(1)} ${u[i]}`;
};

export const pageLabel = (s, e) => (s === e ? `${s}` : `${s}–${e}`);
