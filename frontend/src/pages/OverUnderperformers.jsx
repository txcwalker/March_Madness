import SortableTable from '../components/SortableTable'

const CHART_TEAMS_PER_SIDE = 8

function signed(value, digits = 2) {
  const formatted = value.toFixed(digits)
  return value > 0 ? `+${formatted}` : formatted
}

const COLUMNS = [
  { key: 'team', label: 'Team', getValue: (t) => t.team, format: (t) => t.team },
  { key: 'seed', label: 'Seed', getValue: (t) => t.seed, format: (t) => t.seed },
  {
    key: 'simulatedAverageWins',
    label: 'Simulated Avg Wins',
    getValue: (t) => t.simulatedAverageWins,
    format: (t) => t.simulatedAverageWins.toFixed(2),
  },
  {
    key: 'historicalAverageWins',
    label: "Seed's Historical Avg",
    getValue: (t) => t.historicalAverageWins,
    format: (t) => t.historicalAverageWins.toFixed(2),
  },
  {
    key: 'winsOverSeedExpectation',
    label: 'Wins Over Expectation',
    getValue: (t) => t.winsOverSeedExpectation,
    format: (t) => signed(t.winsOverSeedExpectation),
    className: 'title-pct',
  },
]

export default function OverUnderperformers({ data }) {
  const sorted = [...data.teams].sort((a, b) => b.winsOverSeedExpectation - a.winsOverSeedExpectation)
  const chartTeams = [...sorted.slice(0, CHART_TEAMS_PER_SIDE), ...sorted.slice(-CHART_TEAMS_PER_SIDE)]
  const maxMagnitude = Math.max(...chartTeams.map((t) => Math.abs(t.winsOverSeedExpectation)))

  return (
    <div className="wrap">
      <div className="hero" style={{ paddingBottom: 32 }}>
        <div className="eyebrow">{data.season} NCAA Tournament &mdash; Men&rsquo;s</div>
        <h1>Over/Underperformers</h1>
        <p className="lede">
          Simulated average wins per team, measured against{' '}
          <a href="https://bracketodds.cs.illinois.edu/seedadv.html" target="_blank" rel="noreferrer">
            the historical average
          </a>{' '}
          for that seed line. Positive means the model expects this team to outperform its seed; negative means it
          expects them to miss it.
        </p>
      </div>

      <div className="section">
        <div className="section-head">
          <div className="section-title">Biggest Over/Underperformers</div>
          <div className="section-note">Wins over seed expectation</div>
        </div>
        <div className="diverging-chart">
          {chartTeams.map((team) => {
            const magnitude = (Math.abs(team.winsOverSeedExpectation) / maxMagnitude) * 50
            const isOver = team.winsOverSeedExpectation >= 0
            return (
              <div className="diverging-row" key={team.teamId}>
                <div className="bar-label">{team.team}</div>
                <div className="diverging-track">
                  <div className="diverging-axis" />
                  <div
                    className={`diverging-fill ${isOver ? 'over' : 'under'}`}
                    style={{ width: `${magnitude}%` }}
                  />
                </div>
                <div className="bar-value">{signed(team.winsOverSeedExpectation)}</div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="section" style={{ borderBottom: 'none' }}>
        <div className="section-head">
          <div className="section-title">Every Team</div>
          <div className="section-note">Click a column to sort</div>
        </div>
        <SortableTable
          columns={COLUMNS}
          rows={data.teams}
          rowKey={(t) => t.teamId}
          defaultSort={{ key: 'winsOverSeedExpectation', direction: 'desc' }}
        />
      </div>
    </div>
  )
}
