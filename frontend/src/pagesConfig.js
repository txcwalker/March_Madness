// Page metadata driving Navbar links and App's hash-based page switching --
// same router-free pattern as ../NFL_Exploration/frontend/src/pagesConfig.js,
// appropriate at this page count without pulling in react-router.
export const PAGES = [
  { id: 'home', label: 'Home', showInNav: false },
  { id: 'round-odds', label: 'Round Odds', showInNav: true },
  { id: 'over-underperformers', label: 'Over/Underperformers', showInNav: true },
  { id: 'cinderella', label: 'Cinderella Watch', showInNav: true },
  { id: 'final-four-finder', label: 'Final Four Finder', showInNav: true },
  { id: 'region-strength', label: 'Region Strength', showInNav: true },
  { id: 'path-of-least-resistance', label: 'Path of Least Resistance', showInNav: true },
  { id: 'who-benefits', label: 'Who Benefits', showInNav: true },
  { id: 'seed-prediction', label: 'Seed Prediction', showInNav: true },
]
