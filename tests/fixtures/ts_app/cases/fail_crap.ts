export function messy(a: boolean, b: boolean, c: boolean): number {
  if (a) {
    if (b) {
      return 1;
    }
    return 2;
  }
  if (c) {
    return 3;
  }
  return 0;
}
