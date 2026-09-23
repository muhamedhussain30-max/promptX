import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ── Neon arcade palette ────────────────────────────────────────────
        bg:   { DEFAULT: '#0B0B14', card: '#0F0F1E', hover: '#141428' },
        cyan: {
          DEFAULT: '#00E5FF',
          dim: '#00B8D9',
          glow: 'rgba(0,229,255,0.25)',
        },
        violet: {
          DEFAULT: '#BF5FFF',
          dim: '#9940CC',
          glow: 'rgba(191,95,255,0.25)',
        },
        neon: {
          red:    '#FF3B5C',
          green:  '#39FF9A',
          yellow: '#FFD600',
          orange: '#FF8C00',
        },
        // legacy surface colours kept for backward compat
        surface: {
          900: '#0B0B14',
          800: '#0F0F1E',
          700: '#161628',
          600: '#1E1E36',
          500: '#272748',
        },
        brand: {
          400: '#00E5FF',
          500: '#00B8D9',
          600: '#008FAD',
        },
        accent: {
          yellow: '#FFD600',
          green:  '#39FF9A',
          red:    '#FF3B5C',
          purple: '#BF5FFF',
          cyan:   '#00E5FF',
        },
      },
      fontFamily: {
        display: ['"Orbitron"', '"Space Grotesk"', 'system-ui', 'sans-serif'],
        heading: ['"Space Grotesk"', '"Orbitron"', 'system-ui', 'sans-serif'],
        sans:    ['"Inter"', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        card: '16px',
        'card-lg': '20px',
      },
      boxShadow: {
        // Cyan glow variants
        'cyan':    '0 0 20px rgba(0,229,255,0.35), 0 0 40px rgba(0,229,255,0.12)',
        'cyan-sm': '0 0 10px rgba(0,229,255,0.28)',
        'cyan-lg': '0 0 40px rgba(0,229,255,0.50)',
        // Violet glow
        'violet':    '0 0 20px rgba(191,95,255,0.35), 0 0 40px rgba(191,95,255,0.12)',
        'violet-sm': '0 0 10px rgba(191,95,255,0.28)',
        // Red glow
        'red':    '0 0 20px rgba(255,59,92,0.45)',
        'red-sm': '0 0 10px rgba(255,59,92,0.35)',
        // Green glow
        'green':    '0 0 20px rgba(57,255,154,0.45)',
        'green-sm': '0 0 10px rgba(57,255,154,0.30)',
        // Generic card depth
        'card':   '0 4px 32px rgba(0,0,0,0.55)',
        // Legacy compat
        glow:        '0 0 20px rgba(0,229,255,0.35)',
        'glow-sm':   '0 0 10px rgba(0,229,255,0.28)',
        'glow-yellow':'0 0 16px rgba(255,214,0,0.4)',
        'glow-red':   '0 0 16px rgba(255,59,92,0.4)',
        'glow-green': '0 0 16px rgba(57,255,154,0.4)',
      },
      animation: {
        // Timer
        'timer-pulse': 'timerPulse 0.8s ease-in-out infinite',
        // Forbidden word shake
        'shake': 'shake 0.4s ease-in-out',
        // Score bars
        'bar-fill': 'barFill 0.9s cubic-bezier(0.22,1,0.36,1) forwards',
        // Count-up shimmer on score
        'score-pop': 'scorePop 0.5s cubic-bezier(0.22,1,0.36,1) forwards',
        // Image shimmer placeholder
        'shimmer': 'shimmer 1.6s linear infinite',
        // Neon flicker on glow
        'flicker': 'flicker 3s ease-in-out infinite',
        // Generic fade
        'fade-in': 'fadeIn 0.35s ease-out',
        'slide-up': 'slideUp 0.35s ease-out',
        // Legacy
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'countdown': 'countdown 1s linear',
        'rank-up': 'rankUp 0.6s ease-out',
        'rank-down': 'rankDown 0.6s ease-out',
      },
      keyframes: {
        timerPulse: {
          '0%,100%': { opacity: '1', transform: 'scale(1)' },
          '50%':     { opacity: '0.7', transform: 'scale(1.04)' },
        },
        shake: {
          '0%,100%': { transform: 'translateX(0)' },
          '20%': { transform: 'translateX(-6px)' },
          '40%': { transform: 'translateX(6px)' },
          '60%': { transform: 'translateX(-4px)' },
          '80%': { transform: 'translateX(4px)' },
        },
        barFill: {
          '0%':   { width: '0%' },
          '100%': { width: 'var(--bar-pct)' },
        },
        scorePop: {
          '0%':   { transform: 'scale(0.7)', opacity: '0' },
          '60%':  { transform: 'scale(1.12)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-800px 0' },
          '100%': { backgroundPosition: '800px 0' },
        },
        flicker: {
          '0%,96%,100%': { opacity: '1' },
          '97%': { opacity: '0.85' },
          '98%': { opacity: '1' },
          '99%': { opacity: '0.9' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        countdown: {
          '0%':   { transform: 'scale(1.4)', opacity: '0' },
          '20%':  { transform: 'scale(1.1)', opacity: '1' },
          '80%':  { transform: 'scale(1.0)', opacity: '1' },
          '100%': { transform: 'scale(0.8)', opacity: '0' },
        },
        rankUp: {
          '0%':   { transform: 'translateY(8px)', background: 'rgba(57,255,154,0.15)' },
          '100%': { transform: 'translateY(0)',   background: 'transparent' },
        },
        rankDown: {
          '0%':   { transform: 'translateY(-8px)', background: 'rgba(255,59,92,0.15)' },
          '100%': { transform: 'translateY(0)',    background: 'transparent' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config
