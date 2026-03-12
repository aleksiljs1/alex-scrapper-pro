import { Link } from 'react-router-dom'
import { PlusCircle, Sun, Moon } from 'lucide-react'
import { useThemeStore } from '../../stores/themeStore'

export default function Header() {
  const { dark, toggle } = useThemeStore()

  return (
    <header className="bg-white dark:bg-dark-card border-b border-gray-200 dark:border-dark-border px-6 py-3 flex items-center justify-between">
      <div>
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Facebook Profile Scraper</h2>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={toggle}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 dark:border-dark-border text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-surface transition-colors text-sm"
          aria-label="Toggle dark mode"
        >
          {dark ? <Sun size={16} /> : <Moon size={16} />}
          {dark ? 'Light' : 'Dark'}
        </button>
        <Link
          to="/add"
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <PlusCircle size={16} />
          Add Profile
        </Link>
      </div>
    </header>
  )
}
