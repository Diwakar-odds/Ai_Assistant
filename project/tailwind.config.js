/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#0A0E27',
        secondary: '#6C5CE7',
        accent: '#00CEC9',
        success: '#00B894',
        warning: '#E17055',
      },
      animation: {
        breathe: 'breathe 4s ease-in-out infinite',
        float: 'float 3s ease-in-out infinite',
        'slide-in': 'slide-in 0.5s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
      },
    },
  },
  plugins: [],
};
