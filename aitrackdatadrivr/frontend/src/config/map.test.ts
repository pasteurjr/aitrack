import { resolveMapTileUrl } from './map';

describe('resolveMapTileUrl', () => {
  it('usa o provedor padrão somente na camada de configuração', () => {
    expect(resolveMapTileUrl()).toContain('tile.openstreetmap.org');
  });

  it('aceita um provedor configurado no ambiente', () => {
    expect(resolveMapTileUrl(' https://tiles.example.test/{z}/{x}/{y}.png '))
      .toBe('https://tiles.example.test/{z}/{x}/{y}.png');
  });
});
