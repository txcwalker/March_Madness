export default function Footer({ season, generatedAt }) {
  const generatedDate = generatedAt ? new Date(generatedAt).toLocaleDateString(undefined, { dateStyle: 'medium' }) : null

  return (
    <div className="app-footer wrap">
      <span>Model trained on KenPom ratings and Massey Ordinals. Odds shown are American, model-implied.</span>
      {season && <span>{season} season{generatedDate ? ` · model run ${generatedDate}` : ''}</span>}
    </div>
  )
}
