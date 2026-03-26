import axios from 'axios'

function getCookie(name) {
  const cookies = document.cookie.split(';')
  for (let cookie of cookies) {
    const [key, value] = cookie.trim().split('=')
    if (key === name) return decodeURIComponent(value)
  }
  return null
}

axios.interceptors.request.use(config => {
  if (['post', 'put', 'delete', 'patch'].includes(config.method)) {
    const token = getCookie('csrftoken')
    if (token) config.headers['X-Frappe-CSRF-Token'] = token
  }
  return config
})

export default axios
