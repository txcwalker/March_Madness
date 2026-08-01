import SortableTable from '../components/SortableTable'

function pct(value) {
  return value == null ? '—' : `${(value * 100).toFixed(1)}%`
}

const COLUMNS = [
  { key: 'team', label: 'Team', getValue: (t) => t.team, format: (t) => t.team },
  {
    key: 'roundOf32Strength',
    label: 'Round of 32',
    getValue: (t) => t.roundOf32Strength,
    format: (t) => pct(t.roundOf32Strength),
  },
  {
    key: 'sweetSixteenStrength',
    label: 'Sweet 16',
    getValue: (t) => t.sweetSixteenStrength,
    format: (t) => pct(t.sweetSixteenStrength),
  },
  {
    key: 'eliteEightStrength',
    label: 'Elite 8',
    getValue: (t) => t.eliteEightStrength,
    format: (t) => pct(t.eliteEightStrength),
  },
  {
    key: 'finalFourStrength',
    label: 'Final Four',
    getValue: (t) => t.finalFourStrength,
    format: (t) => pct(t.finalFourStrength),
  },
  {
    key: 'pathStrengthFaced',
    label: 'Path Strength Faced',
    getValue: (t) => t.pathStrengthFaced,
    format: (t) => pct(t.pathStrengthFaced),
    className: 'title-pct',
  },
  {
    key: 'pathEase',
    label: 'Path Ease',
    getValue: (t) => t.pathEase,
    format: (t) => pct(t.pathEase),
  },
]

export default function PathOfLeastResistance({ data }) {
  return (
    <div className="wrap">
      <div className="hero" style={{ paddingBottom: 32 }}>
        <div className="eyebrow">{data.season} NCAA Tournament &mdash; Men&rsquo;s</div>
        <h1>Path of Least Resistance</h1>
        <p className="lede">
          How tough is each team&rsquo;s actual draw to the Final Four, independent of how good the team itself is.
          Walks every team&rsquo;s own advancement chain across all 10,000 simulated brackets and averages the
          strength of whoever <em>actually</em> shows up in each round &mdash; not a single best- or worst-case
          guess. <strong>Path Strength Faced</strong> scores the opponents only, never the team&rsquo;s own win
          probability, so a 1-seed&rsquo;s inherent strength can&rsquo;t make its draw look artificially easy: a team
          that has to get past several genuinely strong opponents scores high here regardless of seed. <strong>Path
          Ease</strong> is the complementary, team-relative number &mdash; given the draws that actually happen, how
          likely is this team to survive them. Click a column to sort; sorted easiest-draw-first by default.
        </p>
      </div>

      <div className="section" style={{ borderBottom: 'none' }}>
        <SortableTable
          columns={COLUMNS}
          rows={data.pathOfLeastResistance}
          rowKey={(t) => t.teamId}
          defaultSort={{ key: 'pathStrengthFaced', direction: 'asc' }}
        />
      </div>
    </div>
  )
}
