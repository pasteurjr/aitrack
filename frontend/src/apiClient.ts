import axios from 'axios';


const baseURL = (process.env.REACT_APP_API_BASE_URL || 'http://localhost:5009/api').replace(/\/+$/, '');

export const apiClient = axios.create({ baseURL, timeout: 15000, withCredentials: true });

apiClient.interceptors.request.use(config => {
  if (typeof document !== 'undefined' && ['post', 'put', 'patch', 'delete'].includes((config.method || '').toLowerCase())) {
    const csrf = document.cookie.split('; ').find(item => item.startsWith('aitrack_csrf='))?.split('=', 2)[1];
    if (csrf) config.headers.set('X-CSRF-Token', decodeURIComponent(csrf));
  }
  return config;
});

export const authApi = {
  me: () => apiClient.get('/auth/me'),
  login: (email: string, password: string) => apiClient.post('/auth/login', { email, password }),
  logout: () => apiClient.post('/auth/logout'),
};
