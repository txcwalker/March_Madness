import { useMemo, useState } from 'react'

// Shared click-to-sort table -- Round Odds and Over/Underperformers both
// need this; pulled out rather than duplicating the sort state/handler in
// each page, matching this project's one-canonical-implementation rule.
export default function SortableTable({ columns, rows, rowKey, defaultSort }) {
  const [sort, setSort] = useState(defaultSort)

  const sortedRows = useMemo(() => {
    const column = columns.find((c) => c.key === sort.key)
    const sorted = [...rows].sort((a, b) => {
      const av = column.getValue(a)
      const bv = column.getValue(b)
      if (typeof av === 'string') return av.localeCompare(bv)
      return av - bv
    })
    return sort.direction === 'desc' ? sorted.reverse() : sorted
  }, [rows, sort, columns])

  const handleSort = (key) => {
    setSort((current) =>
      current.key === key
        ? { key, direction: current.direction === 'desc' ? 'asc' : 'desc' }
        : { key, direction: 'desc' },
    )
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} onClick={() => handleSort(column.key)}>
                {column.label}
                {sort.key === column.key && (
                  <span className="sort-arrow">{sort.direction === 'desc' ? '↓' : '↑'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((column) => (
                <td key={column.key} className={column.className}>
                  {column.format(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
