import { create } from 'zustand'

interface ThemeStore {
  dark: boolean
  toggle: () => void
}

function applyTheme(dark: boolean) {
  if (dark) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

const stored = localStorage.getItem('theme')
const prefersDark = stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)
applyTheme(prefersDark)

export const useThemeStore = create<ThemeStore>((set) => ({
  dark: prefersDark,
  toggle: () =>
    set((state) => {
      const next = !state.dark
      localStorage.setItem('theme', next ? 'dark' : 'light')
      applyTheme(next)
      return { dark: next }
    }),
}))
