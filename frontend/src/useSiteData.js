import { useEffect, useState } from 'react'

// Fetches the static JSON written by scripts/export_site_data.py
// (public/data/current.json). One shared hook so every page gets the same
// loading/error handling instead of duplicating a fetch per page.
export function useSiteData() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch('/data/current.json')
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
        return res.json()
      })
      .then((json) => {
        if (!cancelled) setData(json)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { data, error, loading: !data && !error }
}
