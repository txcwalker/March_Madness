import { useMemo, useState } from 'react'

const TOP_N = 10

function pct(probability) {
  return `${(probability * 100).toFixed(1)}%`
}

function buildRegionTeams(teams) {
  const byRegion = {}
  for (const team of teams) {
    if (!team.region) continue
    ;(byRegion[team.region] ??= []).push(team)
  }
  for (const region of Object.keys(byRegion)) {
    byRegion[region].sort((a, b) => a.seed - b.seed)
  }
  return byRegion
}

export default function FinalFourFinder({ data }) {
  const regionTeams = useMemo(() => buildRegionTeams(data.teams), [data.teams])
  const regions = useMemo(() => Object.keys(regionTeams).sort(), [regionTeams])
  const [selections, setSelections] = useState({})

  const selectedTeamIds = Object.values(selections).filter(Boolean).map(Number)

  const filtered = useMemo(() => {
    if (selectedTeamIds.length === 0) return data.finalFourCombos
    return data.finalFourCombos.filter((combo) =>
      selectedTeamIds.every((teamId) => combo.teamIds.includes(teamId)),
    )
  }, [data.finalFourCombos, selectedTeamIds])

  const top = filtered.slice(0, TOP_N)
  const maxProbability = top.length > 0 ? top[0].probability : 0
  const matchedTotal = filtered.reduce((sum, combo) => sum + combo.count, 0)

  const handleSelect = (region, value) => {
    setSelections((current) => ({ ...current, [region]: value || null }))
  }

  return (
    <div className="wrap">
      <div className="hero" style={{ paddingBottom: 24 }}>
        <div className="eyebrow">{data.season} NCAA Tournament &mdash; Men&rsquo;s</div>
        <h1>Final Four Finder</h1>
        <p className="lede">
          Pick a team in one or more regions to see how often that partial or full Final Four actually occurred
          across {data.nBrackets.toLocaleString()} simulated brackets. Leave a region on &ldquo;Any&rdquo; to keep
          it open.
        </p>
      </div>

      <div className="finder-selects">
        {regions.map((region) => (
          <label className="finder-select" key={region}>
            <span className="stat-label">Region {region}</span>
            <select
              value={selections[region] ?? ''}
              onChange={(event) => handleSelect(region, event.target.value)}
            >
              <option value="">Any</option>
              {regionTeams[region].map((team) => (
                <option key={team.teamId} value={team.teamId}>
                  {team.seed}. {team.team}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>

      <div className="section">
        <div className="section-head">
          <div className="section-title">
            {selectedTeamIds.length === 0 ? 'Most Common Final Fours' : `Matching Final Fours (top ${top.length})`}
          </div>
          <div className="section-note">
            {filtered.length.toLocaleString()} combination{filtered.length === 1 ? '' : 's'} matched &middot;{' '}
            {matchedTotal.toLocaleString()} of {data.nBrackets.toLocaleString()} runs
          </div>
        </div>
        {top.length === 0 ? (
          <p className="page-status">That combination never occurred in any simulated bracket.</p>
        ) : (
          <div className="bar-chart">
            {top.map((combo) => (
              <div className="bar-row" key={combo.teamIds.join('-')}>
                <div className="bar-label">{combo.teams.join(' · ')}</div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${(combo.probability / maxProbability) * 100}%` }} />
                </div>
                <div className="bar-value">{pct(combo.probability)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="section" style={{ borderBottom: 'none' }}>
        <div className="combo-list">
          {top.map((combo, index) => (
            <div className="combo-row" key={combo.teamIds.join('-')}>
              <span className="combo-rank">{index + 1}</span>
              <span className="combo-teams">{combo.teams.join(' · ')}</span>
              <span className="combo-meta">
                {combo.count.toLocaleString()} <span className="combo-pct">{pct(combo.probability)}</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
