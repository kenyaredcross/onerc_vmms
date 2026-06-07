import axios from 'axios'

const http = axios.create({
  withCredentials: true,
  headers: { 'Accept': 'application/json' }
})

http.interceptors.request.use(config => {
  if (['post','put','patch','delete'].includes(config.method?.toLowerCase())) {
    config.headers['X-Frappe-CSRF-Token'] = 'fetch'
  }
  return config
})

http.interceptors.response.use(
  res => res,
  err => {
    const url = err.config?.url || ''
    // 403 from get_logged_user means "guest" — let auth store handle it, don't redirect
    if (err.response?.status === 403 && !url.includes('get_logged_user')) {
      window.location.href = '/vmms/login'
    }
    return Promise.reject(err)
  }
)

export default http
