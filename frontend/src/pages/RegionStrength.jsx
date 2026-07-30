function pct(probability) {
  return `${(probability * 100).toFixed(1)}%`
}

export default function RegionStrength({ data }) {
  const maxShare = Math.max(...data.regions.map((r) => r.championshipShare))
  const byFragility = [...data.regions].sort((a, b) => a.topSeedFinalFourShare - b.topSeedFinalFourShare)

  return (
    <div className="wrap">
      <div className="hero" style={{ paddingBottom: 32 }}>
        <div className="eyebrow">{data.season} NCAA Tournament &mdash; Men&rsquo;s</div>
        <h1>Region Strength</h1>
        <p className="lede">
          Which region&rsquo;s teams actually win the national championship in simulation, and how fragile or
          competitive each region is on its own terms &mdash; how often its own #1 seed is the one to emerge from
          it, regardless of what happens afterward. Region letters are Kaggle&rsquo;s internal labels for the
          season, not real-world names like &ldquo;East&rdquo; &mdash; mapping those is a known follow-up, not done
          yet.
        </p>
      </div>

      <div className="section">
        <div className="section-head">
          <div className="section-title">Championship Share by Region</div>
          <div className="section-note">Share of {data.nBrackets.toLocaleString()} runs</div>
        </div>
        <div className="bar-chart">
          {data.regions.map((region) => (
            <div className="bar-row" key={region.region}>
              <div className="bar-label">Region {region.region}</div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${(region.championshipShare / maxShare) * 100}%` }} />
              </div>
              <div className="bar-value">{pct(region.championshipShare)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="section" style={{ borderBottom: 'none' }}>
        <div className="section-head">
          <div className="section-title">Fragile &rarr; Competitive</div>
          <div className="section-note">Share of all runs the region&rsquo;s own #1 seed reaches the Final Four</div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Region</th>
              <th>Top Seed</th>
              <th>Reaches Final Four</th>
              <th>...and then wins it all</th>
            </tr>
          </thead>
          <tbody>
            {byFragility.map((region) => (
              <tr key={region.region}>
                <td>Region {region.region}</td>
                <td>{region.topSeedTeam}</td>
                <td className="title-pct">{pct(region.topSeedFinalFourShare)}</td>
                <td>{pct(region.topSeedChampionshipShare)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
