import sharp from 'sharp'
import { readFile } from 'node:fs/promises'
const icon = await readFile(new URL('../app/icon.svg',import.meta.url),'utf8')
const path = icon.match(/<path[^>]*d="([^"]+)"/)?.[1]
if(!path)throw new Error('Original FinCo mark missing')
const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"><rect width="1200" height="630" fill="#080b0c"/><rect x="64" y="60" width="64" height="64" rx="18" fill="#c5f4a5"/><g transform="translate(76 72) scale(.04)"><path d="${path}" fill="#15280f"/></g><text x="150" y="104" font-family="sans-serif" font-size="34" font-weight="600" fill="#eff5eb">FinCo-Pilot</text><text x="64" y="274" font-family="sans-serif" font-size="76" font-weight="600" fill="#f4f7ed">Money makes</text><text x="64" y="368" font-family="sans-serif" font-size="76" font-weight="600" fill="#c5f4a5">more sense together.</text><text x="66" y="462" font-family="sans-serif" font-size="28" fill="#afbfaf">Accounts. Spending. Budgets. Reports.</text><path d="M64 536H1136" stroke="#344638"/><text x="64" y="584" font-family="sans-serif" font-size="21" fill="#a5b5a5">fincopilot.app</text></svg>`
await sharp(Buffer.from(svg)).png().toFile(new URL('../public/social-card.png',import.meta.url).pathname)
