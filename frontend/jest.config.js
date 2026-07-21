// eslint-disable-next-line @typescript-eslint/no-require-imports
const nextJest = require("next/jest");

const createJestConfig = nextJest({
  // Path to the Next.js app (loads next.config.js and .env files)
  dir: "./",
});

// react-markdown and the unified/remark ecosystem ship as pure ESM; allow
// the SWC transform to compile them instead of treating them as CJS.
const esmPackages =
  "react-markdown|remark-.*|unified|unist-.*|micromark.*|mdast-.*|hast-.*|" +
  "vfile.*|bail|trough|is-plain-obj|decode-named-character-reference|" +
  "character-entities.*|property-information|space-separated-tokens|" +
  "comma-separated-tokens|web-namespaces|zwitch|html-void-elements|ccount|" +
  "escape-string-regexp|markdown-table|estree-util-.*|html-url-attributes|" +
  "trim-lines|devlop|longest-streak";

/** @type {import("jest").Config} */
const config = {
  testEnvironment: "jest-environment-jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  // tsconfig has paths but no baseUrl, so next/jest does not map the @/
  // alias for jest.mock() calls — map it explicitly.
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
  },
  testMatch: ["<rootDir>/__tests__/**/*.test.{ts,tsx}"],
  collectCoverageFrom: [
    "app/**/*.{ts,tsx}",
    "components/**/*.{ts,tsx}",
    "context/**/*.{ts,tsx}",
    "lib/**/*.{ts,tsx}",
    "!**/*.d.ts",
    // Root layout pulls in next/font/google and is not unit-testable
    "!app/layout.tsx",
    "!lib/theme.ts",
  ],
  coverageThreshold: {
    global: {
      statements: 70,
      functions: 70,
      lines: 70,
    },
  },
};

module.exports = async () => {
  const resolved = await createJestConfig(config)();
  // next/jest seeds transformIgnorePatterns with a blanket node_modules rule,
  // which would ignore the ESM packages above. Replace the list entirely.
  resolved.transformIgnorePatterns = [
    `[\\\\/]node_modules[\\\\/](?!(${esmPackages})[\\\\/])`,
    "^.+\\.module\\.(css|sass|scss)$",
  ];
  return resolved;
};
