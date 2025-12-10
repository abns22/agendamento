/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#004B6B',
        success: '#2ECC71',
        highlight: '#F39C12',
        neutral: {
          light: '#F4F4F4',
          dark: '#2C3E50',
        },
        text: '#333333',
        dark: '#121212',
      },
      fontFamily: {
        sans: ['Poppins', 'Inter', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}


