import { PAGES } from '../pagesConfig'

const THEME_LABEL = { null: 'Auto', light: 'Light', dark: 'Dark' }

export default function Navbar({ currentPage, navigate, theme, toggleTheme }) {
  const navLinks = PAGES.filter((p) => p.showInNav)

  return (
    <div className="navbar">
      <div className="wrap navbar-inner">
        <button className="brand" onClick={() => navigate('home')}>
          Cut<em>down</em>
        </button>
        <div className="nav-links">
          {navLinks.map((page) => (
            <button
              key={page.id}
              className={`nav-link${currentPage === page.id ? ' active' : ''}`}
              onClick={() => navigate(page.id)}
            >
              {page.label}
            </button>
          ))}
          <button className="theme-toggle" onClick={toggleTheme} title="Cycle theme: auto / light / dark">
            {THEME_LABEL[theme]}
          </button>
        </div>
      </div>
    </div>
  )
}
