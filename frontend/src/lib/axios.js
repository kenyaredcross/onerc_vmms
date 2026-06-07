import axios from 'axios'

const http = axios.create({ withCredentials: true })

http.interceptors.request.use(config => {
  if (['post','put','patch','delete'].includes(config.method?.toLowerCase())) {
    config.headers['X-Frappe-CSRF-Token'] = 'fetch'
  }
  return config
})

http.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 403) {
      window.location.href = '/vmms/login'
    }
    return Promise.reject(err)
  }
)

export default http
