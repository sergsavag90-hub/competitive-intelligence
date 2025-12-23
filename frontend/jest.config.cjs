/** @type {import('jest').Config} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "jsdom",
  moduleNameMapper: {
    "^@api/(.*)$": "<rootDir>/src/api/$1",
    "^@components/(.*)$": "<rootDir>/src/components/$1",
    "^@hooks/(.*)$": "<rootDir>/src/hooks/$1",
    "^@pages/(.*)$": "<rootDir>/src/pages/$1",
    "^@types/(.*)$": "<rootDir>/src/types/$1",
    "^@utils/(.*)$": "<rootDir>/src/utils/$1",
  },
  setupFilesAfterEnv: ["@testing-library/jest-dom"],
  testMatch: ["**/?(*.)+(spec|test).[tj]s?(x)"],
};
