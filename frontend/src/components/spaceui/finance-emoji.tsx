import { useState } from 'react'

/** Space UI emoji tool assets, self-hosted with Fluent's MIT notice. */
export function FinanceEmoji({ kind = 'coin' }: { kind?: 'coin' | 'target' }) {
  const [failed, setFailed] = useState(false)
  return <span aria-hidden="true" className="inline-flex size-12 shrink-0 items-center justify-center rounded-2xl bg-muted">
    {failed ? <span className="text-2xl">{kind === 'coin' ? '🪙' : '🎯'}</span>
      : <img src={`/spaceui/${kind}.webp`} alt="" width={36} height={36} decoding="async" onError={() => setFailed(true)} />}
  </span>
}
