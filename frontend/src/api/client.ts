import axios from "axios";

// API endpoint: use Vite env if provided, else same host on backend port 8100.
const viteEnv = (import.meta as any).env || {};
const rawBase =
  viteEnv.VITE_API_URL ||
  `${window.location.protocol}//${window.location.hostname}:8100`;

// Strip trailing /api/v1 if someone passed a fully-qualified API path;
// our callers already include the /api/v1 prefix in their request URLs.
const apiBase = rawBase.replace(/\/api\/v1\/?$/, "");

const client = axios.create({
  baseURL: apiBase,
  withCredentials: true,
});

export const setAuthToken = (token?: string | null) => {
  if (token) {
    client.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete client.defaults.headers.common.Authorization;
  }
};

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        const refreshResponse = await client.post("/auth/refresh", {});
        const newAccess = refreshResponse.data?.access_token;
        if (newAccess) {
          setAuthToken(newAccess);
        }
        return client.request(error.config);
      } catch (refreshErr) {
        return Promise.reject(refreshErr);
      }
    }
    return Promise.reject(error);
  }
);

export default client;
