/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta oficial AYRIA (do DESIGN_SYSTEM)
        ayria: {
          bg: '#050505',
          card: '#111111',
          border: '#1E1E2E',
          primary: '#6366F1',
          accent: '#A855F7',
          text: '#F8FAFC',
          muted: '#94A3B8',
          success: '#10B981',
          error: '#EF4444',
          admin: '#F59E0B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
      },
      backgroundImage: {
        'ayria-gradient': 'linear-gradient(135deg, #6366F1, #A855F7)',
        'ayria-card-gradient': 'linear-gradient(180deg, #111111, #050505)',
      },
      boxShadow: {
        'ayria-glow': '0 0 24px rgba(99, 102, 241, 0.4)',
        'ayria-glow-sm': '0 0 12px rgba(99, 102, 241, 0.3)',
      },
      backdropBlur: {
        'glass': '12px',
      },
      animation: {
        'typing-dot': 'pulse 1.4s infinite ease-in-out',
      },
    },
  },
  plugins: [],
};
