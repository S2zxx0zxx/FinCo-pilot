/** Public assets share the exported landing's path, never the finance app's assets. */
export function landingAsset(path: string) {
  return `${process.env.NEXT_PUBLIC_FINCO_LANDING_BASE_PATH || ''}${path}`
}
