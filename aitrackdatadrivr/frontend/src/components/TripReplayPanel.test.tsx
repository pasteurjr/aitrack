import { nextReplayIndex } from './tripReplayControls';

describe('TripReplayPanel', () => {
  it('avança sem ultrapassar o fim da timeline', () => {
    expect(nextReplayIndex(0, 3)).toBe(1);
    expect(nextReplayIndex(2, 3)).toBe(2);
    expect(nextReplayIndex(0, 0)).toBe(0);
  });
});
