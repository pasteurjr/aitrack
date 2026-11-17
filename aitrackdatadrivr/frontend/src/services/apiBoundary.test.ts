import fs from 'fs';
import path from 'path';

function listSourceFiles(directory: string): string[] {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) return listSourceFiles(target);
    return /\.(ts|tsx)$/.test(entry.name) && !entry.name.includes('.test.') ? [target] : [];
  });
}

function directNetworkViolations(source: string): string[] {
  const checks: Array<[string, RegExp]> = [
    ['URL HTTP absoluta', /https?:\/\//i],
    ['endereço IP literal', /\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b/],
    ['localhost literal', /\blocalhost(?::\d+)?\b/i],
    ['import direto de Axios', /from\s+['"]axios['"]/],
    ['uso direto de fetch', /\bfetch\s*\(/],
  ];
  return checks.filter(([, pattern]) => pattern.test(source)).map(([label]) => label);
}

test('componentes não acessam rede nem endereços diretamente', () => {
  const componentsDirectory = path.resolve(__dirname, '../components');
  const violations = listSourceFiles(componentsDirectory).flatMap(file => {
    const source = fs.readFileSync(file, 'utf8');
    return directNetworkViolations(source).map(reason => `${path.basename(file)}: ${reason}`);
  });

  expect(violations).toEqual([]);
});

test.each([
  ['URL absoluta', "fetch('https://api.example.test/vehicles')"],
  ['IP literal', "const endpoint = 'http://192.168.0.10:5009/api'"],
  ['localhost', "const endpoint = 'localhost:5009/api'"],
  ['Axios direto', "import axios from 'axios'"],
  ['fetch relativo', "fetch('/api/vehicles')"],
])('a fronteira detecta regressão por %s', (_case, source) => {
  expect(directNetworkViolations(source)).not.toEqual([]);
});

test('código de produção não importa diretórios de dados mockados', () => {
  const sourceDirectory = path.resolve(__dirname, '..');
  const violations = listSourceFiles(sourceDirectory).filter(file => (
    fs.readFileSync(file, 'utf8').includes('mockData')
  ));

  expect(violations).toEqual([]);
});
