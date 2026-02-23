/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a5f',
        },
        risk: {
          low: '#22c55e',
          moderate: '#eab308',
          elevated: '#f97316',
          high: '#ef4444',
          critical: '#dc2626',
        },
      },
    },
  },
  plugins: [],
}
