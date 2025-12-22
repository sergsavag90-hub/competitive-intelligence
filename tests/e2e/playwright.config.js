// Minimal Playwright config; assumes frontend at http://localhost:4173
const config = {
  testDir: './',
  timeout: 120000,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:4173',
    headless: true,
  },
};

module.exports = config;
