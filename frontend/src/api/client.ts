import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        await client.post("/auth/refresh");
        return client.request(error.config);
      } catch (refreshErr) {
        return Promise.reject(refreshErr);
      }
    }
    return Promise.reject(error);
  }
);

export default client;
