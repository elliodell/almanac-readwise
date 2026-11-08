// The number device.json sends as `build`, which the server compares: 0.4.0 → 400, 1.2.3 → 10203.
export function buildNumber(version: string): number {
  // The downstream prerelease keeps the upstream Almanac service contract.
  const [major, minor, patch] = version.split('-')[0].split('.').map(Number)
  if (![major, minor, patch].every(Number.isInteger) || minor > 99 || patch > 99) {
    throw new Error(`Version ${version} has no build number: minor and patch go up to 99`)
  }
  return major * 10000 + minor * 100 + patch
}

export const builds = (deviceJson: string) => [...deviceJson.matchAll(/[?&]build=(\d+)/g)].map((m) => Number(m[1]))
