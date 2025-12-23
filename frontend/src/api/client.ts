import axios from "axios";

// API endpoint: use Vite env if provided, else fall back to localhost:8100.
const viteEnv = (import.meta as any).env || {};
const apiBase = viteEnv.VITE_API_URL || "http://localhost:8100";

if (import.meta?.env?.DEV) {
  const isVersioned = /\/api(\/v1)?/.test(apiBase);
  if (!isVersioned) {
    // eslint-disable-next-line no-console
    console.warn(`[api] VITE_API_URL "${apiBase}" does not include /api prefix; ensure routes include it.`);
  }
}

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
