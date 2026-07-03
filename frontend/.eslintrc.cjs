// ESLint para el frontend. Complementa a `tsc` (que ya cubre tipos y variables sin
// usar vía noUnusedLocals): aquí se aporta lo que el compilador NO valida, sobre todo
// las reglas de los hooks de React (rules-of-hooks + exhaustive-deps).
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  plugins: ["@typescript-eslint", "react-hooks"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  ignorePatterns: ["dist", "node_modules", "*.config.js", "*.config.cjs", "*.config.ts"],
  rules: {
    // Las variables/imports sin usar los cubre `tsc` (noUnusedLocals/Parameters) con
    // más precisión de tipos: se apaga aquí para no duplicar la regla.
    "@typescript-eslint/no-unused-vars": "off",
    // `any` puntual e intencional (p. ej. el catch de errores de axios).
    "@typescript-eslint/no-explicit-any": "off",
  },
};
