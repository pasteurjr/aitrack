import { resolveApiBaseUrl } from './api';

describe('resolveApiBaseUrl', () => {
  it('usa o backend local quando não existe configuração', () => {
    expect(resolveApiBaseUrl()).toBe('http://localhost:5009/api');
  });

  it('aceita backend configurado e remove barras finais', () => {
    expect(resolveApiBaseUrl(' https://api.exemplo.com/v1/// ')).toBe('https://api.exemplo.com/v1');
  });
});
