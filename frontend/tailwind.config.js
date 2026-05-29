/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: 'var(--bg-void)',
        surface: 'var(--bg-surface)',
        elevated: 'var(--bg-elevated)',
        cyan: {
          400: 'var(--accent-cyan)',
        },
        blue: {
          500: 'var(--accent-blue)',
        },
        violet: {
          500: 'var(--accent-violet)',
        },
        emerald: {
          500: 'var(--accent-emerald)',
        },
        amber: {
          500: 'var(--accent-amber)',
        },
        rose: {
          500: 'var(--accent-rose)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'monospace'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 4s linear infinite',
        'marquee': 'marquee 30s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: 1, filter: 'drop-shadow(0 0 10px rgba(34,211,238,0.3))' },
          '50%': { opacity: .7, filter: 'drop-shadow(0 0 2px rgba(34,211,238,0.1))' },
        },
        'marquee': {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-33.333%)' },
        },
      }
    },
  },
  plugins: [],
}
