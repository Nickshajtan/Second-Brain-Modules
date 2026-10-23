import js from '@eslint/js';

export default [
  {ignores: ['node_modules/**', 'dist/**', '.cache/**', '**/generated/**']},
  {
    files: ['packages/typescript/*.mjs', 'tools/*.mjs', 'eslint.config.mjs'],
    languageOptions: {ecmaVersion: 2022, sourceType: 'module', globals: {process: 'readonly', URL: 'readonly'}},
    rules: {...js.configs.recommended.rules, 'eqeqeq': ['error', 'always'], 'no-var': 'error', 'prefer-const': 'error'},
  },
];
