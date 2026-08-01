import { useEffect, useState } from 'react'
import { PAGES } from './pagesConfig'
import { useSiteData } from './useSiteData'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import Home from './pages/Home'
import RoundOdds from './pages/RoundOdds'
import OverUnderperformers from './pages/OverUnderperformers'
import Cinderella from './pages/Cinderella'
import FinalFourFinder from './pages/FinalFourFinder'
import RegionStrength from './pages/RegionStrength'
import PathOfLeastResistance from './pages/PathOfLeastResistance'
import WhoBenefits from './pages/WhoBenefits'
import ComingSoon from './pages/ComingSoon'

const THEME_KEY = 'cutdown-theme'

function readStoredTheme() {
  const stored = localStorage.getItem(THEME_KEY)
  return stored === 'light' || stored === 'dark' ? stored : null
}

export default function App() {
  const [currentPage, setCurrentPage] = useState('home')
  const [theme, setTheme] = useState(readStoredTheme)
  const { data, error, loading } = useSiteData()

  // Hash sync so pages are bookmarkable and the back button works, same
  // pattern as ../NFL_Exploration/frontend/src/App.jsx.
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '')
      const validPages = PAGES.map((p) => p.id)
      setCurrentPage(validPages.includes(hash) ? hash : 'home')
    }
    handleHashChange()
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  useEffect(() => {
    if (theme) {
      document.documentElement.setAttribute('data-theme', theme)
      localStorage.setItem(THEME_KEY, theme)
    } else {
      document.documentElement.removeAttribute('data-theme')
      localStorage.removeItem(THEME_KEY)
    }
  }, [theme])

  const navigate = (pageId) => {
    setCurrentPage(pageId)
    window.location.hash = pageId === 'home' ? '' : pageId
  }

  const toggleTheme = () => {
    // Cycle: follow-system -> light -> dark -> follow-system.
    setTheme((current) => {
      if (current === null) return 'light'
      if (current === 'light') return 'dark'
      return null
    })
  }

  const renderPage = () => {
    if (loading) return <p className="page-status">Loading model output&hellip;</p>
    if (error) return <p className="page-status page-status-error">Couldn&rsquo;t load model data: {error.message}</p>

    switch (currentPage) {
      case 'home':
        return <Home data={data} navigate={navigate} />
      case 'round-odds':
        return <RoundOdds data={data} />
      case 'over-underperformers':
        return <OverUnderperformers data={data} />
      case 'cinderella':
        return <Cinderella data={data} />
      case 'final-four-finder':
        return <FinalFourFinder data={data} />
      case 'region-strength':
        return <RegionStrength data={data} />
      case 'path-of-least-resistance':
        return <PathOfLeastResistance data={data} />
      case 'who-benefits':
        return <WhoBenefits data={data} />
      case 'seed-prediction':
        return <ComingSoon pageId={currentPage} />
      default:
        return <Home data={data} navigate={navigate} />
    }
  }

  return (
    <div className="app-shell">
      <Navbar currentPage={currentPage} navigate={navigate} theme={theme} toggleTheme={toggleTheme} />
      <main className="app-main">{renderPage()}</main>
      <Footer season={data?.season} generatedAt={data?.generatedAt} />
    </div>
  )
}
