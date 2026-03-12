/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0b1121',
          card: '#111827',
          surface: '#1e293b',
          border: '#1e3a5f',
          hover: '#172554',
        },
      },
    },
  },
  plugins: [],
}
