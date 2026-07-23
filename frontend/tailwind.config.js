/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta AYRIA — alinhada com Lovable (dourado + dark)
        ayria: {
          bg: '#050505',
          card: '#111111',
          border: '#1E1E2E',
          // Dourado (gold) — substituindo indigo/roxo
          primary: '#f1c961',
          'primary-dark': '#da950b',
          accent: '#da950b',
          text: '#F8FAFC',
          muted: '#94A3B8',
          success: '#10B981',
          error: '#EF4444',
          admin: '#F59E0B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Cormorant Garamond"', '"Playfair Display"', 'Georgia', 'serif'],
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
      },
      backgroundImage: {
        'ayria-gradient': 'linear-gradient(135deg, #f1c961, #da950b)',
        'ayria-card-gradient': 'linear-gradient(180deg, #111111, #050505)',
        'ayria-gold-glow': 'radial-gradient(circle at center, rgba(241,201,97,0.25), transparent 70%)',
      },
      boxShadow: {
        'ayria-glow': '0 0 24px rgba(241, 201, 97, 0.4)',
        'ayria-glow-sm': '0 0 12px rgba(241, 201, 97, 0.3)',
        'ayria-glow-lg': '0 0 48px rgba(241, 201, 97, 0.5)',
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
