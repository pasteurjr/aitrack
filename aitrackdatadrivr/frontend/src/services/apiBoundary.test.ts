import fs from 'fs';
import path from 'path';

function listSourceFiles(directory: string): string[] {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) return listSourceFiles(target);
    return /\.(ts|tsx)$/.test(entry.name) && !entry.name.includes('.test.') ? [target] : [];
  });
}

test('componentes não acessam Axios nem endereço do backend diretamente', () => {
  const componentsDirectory = path.resolve(__dirname, '../components');
  const violations = listSourceFiles(componentsDirectory).filter(file => {
    const source = fs.readFileSync(file, 'utf8');
    return /localhost:5009/.test(source) || /from\s+['"]axios['"]/.test(source);
  });

  expect(violations).toEqual([]);
});

test('código de produção não importa diretórios de dados mockados', () => {
  const sourceDirectory = path.resolve(__dirname, '..');
  const violations = listSourceFiles(sourceDirectory).filter(file => (
    fs.readFileSync(file, 'utf8').includes('mockData')
  ));

  expect(violations).toEqual([]);
});
