import { PAGES } from '../pagesConfig'

// Placeholder for the five analytics pages not built yet this pass (see
// GOAL_TRACKER.md Milestone 2) -- keeps every nav link live instead of
// dead-ending, without faking data that doesn't exist yet.
export default function ComingSoon({ pageId }) {
  const page = PAGES.find((p) => p.id === pageId)

  return (
    <div className="wrap coming-soon">
      <div className="eyebrow">In progress</div>
      <h1>{page?.label ?? 'This page'}</h1>
      <p>The underlying analysis already exists in the pipeline -- this page&rsquo;s frontend view is next up.</p>
    </div>
  )
}
