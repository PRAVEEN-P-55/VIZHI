import axios from "axios";

// In production (Render), VITE_API_URL is baked at build time and points
// directly to the backend. In local dev, falls back to /api (Vite proxy).
const BASE = import.meta.env.VITE_API_URL || "";
const client = axios.create({ baseURL: BASE });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("vizhi_access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing = null;
client.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("vizhi_refresh");
      if (refresh) {
        try {
          refreshing =
            refreshing ||
            axios.post(`${BASE}/auth/refresh`, { refresh_token: refresh });
          const { data } = await refreshing;
          refreshing = null;
          localStorage.setItem("vizhi_access", data.access_token);
          localStorage.setItem("vizhi_refresh", data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return client(original);
        } catch {
          refreshing = null;
          localStorage.removeItem("vizhi_access");
          localStorage.removeItem("vizhi_refresh");
          localStorage.removeItem("vizhi_user");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export default client;
