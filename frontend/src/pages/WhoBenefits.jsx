import { useMemo, useState } from 'react'

const RESULTS_SHOWN = 10

function pct(probability) {
  return `${(probability * 100).toFixed(1)}%`
}

function StackedBarSection({ title, note, entries, beforeKey, afterKey }) {
  const maxValue = Math.max(...entries.map((entry) => Math.max(entry[beforeKey], entry[afterKey])), 0.001)

  return (
    <div className="section">
      <div className="section-head">
        <div className="section-title">{title}</div>
        <div className="section-note">{note}</div>
      </div>
      <div className="bar-chart">
        {entries.map((entry) => {
          const before = entry[beforeKey]
          const after = entry[afterKey]
          const isGain = after >= before
          const baseWidth = (Math.min(before, after) / maxValue) * 100
          const deltaWidth = (Math.abs(after - before) / maxValue) * 100
          return (
            <div className="stacked-row" key={entry.teamId}>
              <div className="bar-label">{entry.team}</div>
              <div className="stacked-track">
                <div className="stacked-base" style={{ width: `${baseWidth}%` }} />
                <div
                  className={`stacked-delta ${isGain ? 'gain' : 'loss'}`}
                  style={{ left: `${baseWidth}%`, width: `${deltaWidth}%` }}
                />
              </div>
              <div className="stacked-value">
                {pct(before)} &rarr; {pct(after)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function WhoBenefits({ data }) {
  const sortedTeams = useMemo(() => [...data.teams].sort((a, b) => a.team.localeCompare(b.team)), [data.teams])
  const [teamXId, setTeamXId] = useState(String(data.teams[0].teamId))

  const benefitList = data.benefitIfLoses[teamXId] ?? []
  // Each section ranks and slices independently, not a shared top-10: Final
  // Four benefit is exactly 0 for every team outside TeamX's own region (see
  // analysis/round_advancement.py's benefit_if_team_loses()), so sorting by
  // it always surfaces TeamX's region; championship benefit is real for
  // every team regardless of region, so that ranking spans the whole field.
  const finalFourShown = useMemo(
    () => [...benefitList].sort((a, b) => b.finalFourBenefit - a.finalFourBenefit).slice(0, RESULTS_SHOWN),
    [benefitList]
  )
  const championshipShown = useMemo(
    () => [...benefitList].sort((a, b) => b.championBenefit - a.championBenefit).slice(0, RESULTS_SHOWN),
    [benefitList]
  )
  const teamX = data.teams.find((t) => String(t.teamId) === teamXId)

  return (
    <div className="wrap">
      <div className="hero" style={{ paddingBottom: 24 }}>
        <div className="eyebrow">{data.season} NCAA Tournament &mdash; Men&rsquo;s</div>
        <h1>Who Benefits if Team X Loses</h1>
        <p className="lede">
          Pick a team. &ldquo;Loses&rdquo; means that team doesn&rsquo;t reach the Final Four. Each row shows a
          team&rsquo;s normal, full-field odds versus its odds in just the simulated brackets where your pick
          doesn&rsquo;t reach the Final Four. Final Four odds only move for teams in your pick&rsquo;s own region
          (only one team per region reaches the Final Four, so it&rsquo;s ranked there); championship odds move for
          any team, any region, since eliminating a contender makes the eventual final easier for the whole field.
        </p>
        <label className="finder-select" style={{ maxWidth: 280, marginTop: 24 }}>
          <span className="stat-label">If this team loses early&hellip;</span>
          <select value={teamXId} onChange={(event) => setTeamXId(event.target.value)}>
            {sortedTeams.map((team) => (
              <option key={team.teamId} value={team.teamId}>
                {team.team}
              </option>
            ))}
          </select>
        </label>
      </div>

      <StackedBarSection
        title="Final Four Odds"
        note={`Baseline vs. ${teamX?.team} eliminated before the Final Four — ${teamX?.team}'s region only`}
        entries={finalFourShown}
        beforeKey="finalFourShareBaseline"
        afterKey="finalFourShareIfXEliminated"
      />

      <StackedBarSection
        title="Championship Odds"
        note={`Baseline vs. ${teamX?.team} eliminated before the Final Four — all teams`}
        entries={championshipShown}
        beforeKey="championShareBaseline"
        afterKey="championShareIfXEliminated"
      />
    </div>
  )
}
