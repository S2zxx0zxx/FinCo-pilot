/** Publication is a separate, explicit production release decision.
 * Preview/branch/self-hosted builds stay noindex; caller never supplies a
 * canonical domain other than the verified apex. No network or credentials.
 */
export const CANONICAL_MARKETING_ORIGIN = 'https://fincopilot.app'

export function marketingPublicationEnv(env = process.env) {
  const approved = env.FINCO_MARKETING_PUBLICATION_APPROVED === 'true'
  if (env.NEXT_PUBLIC_MARKETING_INDEXABLE === 'true' && !approved) {
    throw new Error('Do not enable marketing indexing without the publication gate')
  }
  if (approved && (env.VERCEL_ENV !== 'production' ||
      env.NEXT_PUBLIC_MARKETING_URL !== CANONICAL_MARKETING_ORIGIN)) {
    throw new Error('Marketing publication requires an explicit canonical apex and production environment')
  }
  return {
    NEXT_PUBLIC_MARKETING_INDEXABLE: approved ? 'true' : 'false',
    NEXT_PUBLIC_MARKETING_URL: approved ? CANONICAL_MARKETING_ORIGIN : (env.NEXT_PUBLIC_MARKETING_URL || ''),
  }
}
