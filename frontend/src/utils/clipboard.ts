export function copyToClipboard(text: string): void {
  navigator.clipboard.writeText(text);
}

export function maskKey(key: string): string {
  if (key.length <= 8) return "********";
  return key.slice(0, 4) + "********" + key.slice(-4);
}
