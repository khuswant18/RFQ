/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        pageBg: '#F4F7FA',
        surface: {
          DEFAULT: '#FFFFFF',
          panel: '#EDF2F7',
          border: '#D6DEE8',
          text: '#0D1B2A',
          muted: '#385170',
          subtle: '#6B8AA6'
        },
        primary: {
          DEFAULT: '#16324F',
          dark: '#0D1B2A',
          light: '#385170',
          soft: '#6B8AA6',
          pale: '#DCEAF5'
        },
        accent: {
          amber: '#A06A1B',
          success: '#2F6B4F',
          danger: '#C0392B',
          warning: '#C28A2C',
        }
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        card: '12px',
        input: '10px',
        btn: '8px',
        table: '6px'
      },
      boxShadow: {
        'subtle': '0 1px 2px rgba(13, 27, 42, 0.04)',
      },
      animation: {
        'fade-in': 'fadeIn 150ms ease-out',
        'slide-up': 'slideUp 150ms ease-out',
        'spin-fast': 'spin 500ms linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}
