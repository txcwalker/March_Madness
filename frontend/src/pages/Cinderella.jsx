const ROUND_LABELS = {
  R2: 'Sweet 16',
  R3: 'Elite 8',
  R4: 'Final Four',
  R5: 'Title Game',
  R6: 'Champion',
}

function pct(probability) {
  return `${(probability * 100).toFixed(1)}%`
}

export default function Cinderella({ data }) {
  const seeds = [...new Set(data.cinderella.map((c) => c.minSeed))].sort((a, b) => a - b)
  const rounds = [...new Set(data.cinderella.map((c) => c.round))]
  const byKey = Object.fromEntries(data.cinderella.map((c) => [`${c.minSeed}-${c.round}`, c.probability]))

  return (
    <div className="wrap">
      <div className="hero" style={{ paddingBottom: 32 }}>
        <div className="eyebrow">{data.season} NCAA Tournament &mdash; Men&rsquo;s</div>
        <h1>Cinderella Watch</h1>
        <p className="lede">
          The odds that at least one team seeded this far down (or worse) reaches each round, across{' '}
          {data.nBrackets.toLocaleString()} simulated brackets. Darker cells mean a Cinderella run of that depth is
          more likely, not less.
        </p>
      </div>

      <div className="section" style={{ borderBottom: 'none' }}>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Seed or worse</th>
                {rounds.map((round) => (
                  <th key={round}>{ROUND_LABELS[round] ?? round}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {seeds.map((seed) => (
                <tr key={seed}>
                  <td>{seed}+</td>
                  {rounds.map((round) => {
                    const probability = byKey[`${seed}-${round}`] ?? 0
                    return (
                      <td
                        key={round}
                        style={{
                          background: `color-mix(in srgb, var(--accent) ${Math.round(probability * 100)}%, transparent)`,
                        }}
                      >
                        {pct(probability)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
