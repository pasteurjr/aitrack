export function nextReplayIndex(current: number, total: number): number {
  return total === 0 ? 0 : Math.min(current + 1, total - 1);
}
