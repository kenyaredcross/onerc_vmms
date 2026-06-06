import axios from 'axios'

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
        'X-Frappe-CSRF-Token': 'fetch'
      }
    }
  )
  return res.data.message
}
