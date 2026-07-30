function formatPct(probability) {
  return `${(probability * 100).toFixed(1)}%`
}

export default function Home({ data, navigate }) {
  const favorite = data.teams[0]
  const mostWideOpen = [...data.regions].sort(
    (a, b) => a.topSeedFinalFourShare - b.topSeedFinalFourShare,
  )[0]
  const topTeams = data.teams.slice(0, 8)
  const maxChampionProbability = topTeams[0].champion.probability

  return (
    <div className="wrap">
      <div className="hero">
        <div className="eyebrow">{data.season} NCAA Tournament &mdash; Men&rsquo;s</div>
        <h1>{data.nBrackets.toLocaleString()} simulated brackets. One favorite emerges.</h1>
        <p className="lede">
          Team efficiency (KenPom-adjusted) feeds a trained win-probability model, played out across{' '}
          {data.nBrackets.toLocaleString()} Monte Carlo bracket simulations. Every number below is the share of
          those simulations in which that outcome actually happened.
        </p>
      </div>

      <div className="stat-line">
        <div className="stat-item">
          <div className="stat-label">Teams Modeled</div>
          <div className="stat-num">{data.teams.length}</div>
          <div className="stat-sub">Full at-large field</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Brackets Simulated</div>
          <div className="stat-num">{data.nBrackets.toLocaleString()}</div>
          <div className="stat-sub">Monte Carlo runs</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Title Favorite</div>
          <div className="stat-num">{favorite.team}</div>
          <div className="stat-sub">{formatPct(favorite.champion.probability)} share</div>
        </div>
        <div className="stat-item">
          <div className="stat-label">Most Wide-Open Region</div>
          <div className="stat-num">Region {mostWideOpen.region}</div>
          <div className="stat-sub">{formatPct(mostWideOpen.topSeedFinalFourShare)} held by its #1 seed</div>
        </div>
      </div>

      <div className="section">
        <div className="section-head">
          <div className="section-title">Championship Odds</div>
          <button className="nav-link" onClick={() => navigate('round-odds')}>
            All teams, every round &rarr;
          </button>
        </div>
        <div className="bar-chart">
          {topTeams.map((team) => (
            <div className="bar-row" key={team.teamId}>
              <div className="bar-label">{team.team}</div>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{ width: `${(team.champion.probability / maxChampionProbability) * 100}%` }}
                />
              </div>
              <div className="bar-value">{formatPct(team.champion.probability)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="section">
        <div className="section-head">
          <div className="section-title">Region Outlook</div>
          <div className="section-note">Share of {data.nBrackets.toLocaleString()} runs producing that region&rsquo;s champion</div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Region</th>
              <th>Top Seed</th>
              <th>Top Seed Reaches F4</th>
              <th>Champion Share</th>
            </tr>
          </thead>
          <tbody>
            {data.regions.map((region) => (
              <tr key={region.region}>
                <td>Region {region.region}</td>
                <td>{region.topSeedTeam}</td>
                <td>{formatPct(region.topSeedFinalFourShare)}</td>
                <td className="title-pct">{formatPct(region.championshipShare)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="section" style={{ borderBottom: 'none' }}>
        <div className="section-head">
          <div className="section-title">Most Simulated Final Fours</div>
          <button className="nav-link" onClick={() => navigate('final-four-finder')}>
            Full lookup &rarr;
          </button>
        </div>
        <div className="combo-list">
          {data.finalFourCombos.slice(0, 3).map((combo, index) => (
            <div className="combo-row" key={combo.teamIds.join('-')}>
              <span className="combo-rank">{index + 1}</span>
              <span className="combo-teams">{combo.teams.join(' · ')}</span>
              <span className="combo-meta">
                {combo.count.toLocaleString()} <span className="combo-pct">{formatPct(combo.probability)}</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
