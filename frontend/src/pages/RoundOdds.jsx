import SortableTable from '../components/SortableTable'

function pct(probability) {
  return `${(probability * 100).toFixed(1)}%`
}

const COLUMNS = [
  { key: 'team', label: 'Team', getValue: (t) => t.team, format: (t) => t.team },
  { key: 'seed', label: 'Seed', getValue: (t) => t.seed, format: (t) => t.seed },
  { key: 'roundOf32', label: 'Round of 32', getValue: (t) => t.roundOf32.probability, format: (t) => pct(t.roundOf32.probability) },
  { key: 'sweetSixteen', label: 'Sweet 16', getValue: (t) => t.sweetSixteen.probability, format: (t) => pct(t.sweetSixteen.probability) },
  { key: 'eliteEight', label: 'Elite 8', getValue: (t) => t.eliteEight.probability, format: (t) => pct(t.eliteEight.probability) },
  { key: 'finalFour', label: 'Final Four', getValue: (t) => t.finalFour.probability, format: (t) => pct(t.finalFour.probability) },
  { key: 'championshipGame', label: 'Title Game', getValue: (t) => t.championshipGame.probability, format: (t) => pct(t.championshipGame.probability) },
  { key: 'champion', label: 'Champion', getValue: (t) => t.champion.probability, format: (t) => pct(t.champion.probability), className: 'title-pct' },
]

export default function RoundOdds({ data }) {
  return (
    <div className="wrap">
      <div className="hero" style={{ paddingBottom: 32 }}>
        <div className="eyebrow">{data.season} NCAA Tournament &mdash; Men&rsquo;s</div>
        <h1>Round Odds</h1>
        <p className="lede">
          Every team&rsquo;s odds of reaching each round, from {data.nBrackets.toLocaleString()} simulated brackets.
          Click a column to sort.
        </p>
      </div>

      <div className="section" style={{ borderBottom: 'none' }}>
        <SortableTable
          columns={COLUMNS}
          rows={data.teams}
          rowKey={(t) => t.teamId}
          defaultSort={{ key: 'champion', direction: 'desc' }}
        />
      </div>
    </div>
  )
}
