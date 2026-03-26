import axios from 'axios'

function getCookie(name) {
  const cookies = document.cookie.split(';')
  for (let cookie of cookies) {
    const [key, value] = cookie.trim().split('=')
    if (key === name) return decodeURIComponent(value)
  }
  return null
}

export async function frappeCall(method, args = {}) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(args)) {
    params.append(key, typeof value === 'object' ? JSON.stringify(value) : value)
  }

  const res = await axios.post(
    `/api/method/${method}`,
    params,
    {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Frappe-CSRF-Token': getCookie('csrftoken') || 'fetch'
      }
    }
  )
  return res.data.message
}
