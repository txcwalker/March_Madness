function pct(probability) {
  return `${(probability * 100).toFixed(1)}%`
}

function num(value, digits = 1) {
  return value == null ? '—' : value.toFixed(digits)
}

export default function RegionStrength({ data }) {
  const maxShare = Math.max(...data.regions.map((r) => r.championshipShare))
  const byFragility = [...data.regions].sort((a, b) => a.topSeedFinalFourShare - b.topSeedFinalFourShare)
  const byCompetitiveness = [...data.regions].sort(
    (a, b) => (b.competitiveness ?? -1) - (a.competitiveness ?? -1)
  )

  return (
    <div className="wrap">
      <div className="hero" style={{ paddingBottom: 32 }}>
        <div className="eyebrow">{data.season} NCAA Tournament &mdash; Men&rsquo;s</div>
        <h1>Region Strength</h1>
        <p className="lede">
          Which region&rsquo;s teams actually win the national championship in simulation, and two complementary
          views of how fragile or competitive each region is &mdash; whether the presumed favorite actually
          delivers, whether the region&rsquo;s own games are genuinely close, and how open the region is if that
          favorite falls short. A region can look dominant by one of these and wide open by another &mdash; a
          strong favorite that keeps winning close games isn&rsquo;t the same as a region with no real drama.
          Region letters are Kaggle&rsquo;s internal labels for the season, not real-world names like
          &ldquo;East&rdquo; &mdash; mapping those is a known follow-up, not done yet.
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

      <div className="section">
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

      <div className="section" style={{ borderBottom: 'none' }}>
        <div className="section-head">
          <div className="section-title">Outcome Uncertainty &amp; Effective Contenders</div>
          <div className="section-note">
            How unpredictable the region&rsquo;s own games are, and how open it is if the favorite falls short
          </div>
        </div>
        <p className="section-note" style={{ marginBottom: 16 }}>
          Outcome Uncertainty averages how close to a coin flip every game played within the region actually is
          (1.00 = every game a true toss-up, 0.00 = every game a lock) &mdash; it measures how unpredictable the
          <em> winner</em> is, not the final score, so a heavy favorite can still score low here even in a game it
          wins by one point. The favorite shown is the model&rsquo;s own strongest team in the region (by average
          win probability against the full field), not necessarily the #1 seed. Effective Contenders is how many
          realistic backups the region has if that favorite doesn&rsquo;t reach the Final Four &mdash; 1 means one
          clear backup and nobody else close, higher means several teams are genuinely live.
        </p>
        <table>
          <thead>
            <tr>
              <th>Region</th>
              <th>Model Favorite</th>
              <th>Outcome Uncertainty</th>
              <th>Effective Contenders if Favorite Falls</th>
            </tr>
          </thead>
          <tbody>
            {byCompetitiveness.map((region) => (
              <tr key={region.region}>
                <td>Region {region.region}</td>
                <td>{region.favoriteTeam ?? '—'}</td>
                <td className="title-pct">{region.competitiveness == null ? '—' : pct(region.competitiveness)}</td>
                <td>{num(region.effectiveContenders)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
