# Choosing a manual-first financial workflow

**Unpublished editorial draft — 15 October 2026.** Topic: evaluate transaction-import and record-review workflows, not an overall winner or a feature/price ranking. No new public URL is assigned; do not add this draft to the sitemap. Product facts require the selected deployed version's acceptance before publication.

## Reader-facing draft

Connecting a bank is not the only way to start organizing financial records. A small manual account and a carefully reviewed file can help you learn a budgeting workspace before deciding whether a connected service fits your needs.

When comparing products, try the same harmless synthetic file. Check whether you can select the destination account, understand the dates and money signs, review duplicates and see why a row failed. Confirm the account currency and keep an independent record of the starting balance. A history of imported transactions does not establish the amount currently available to spend.

Actual Budget's official import documentation describes file imports, CSV mappings, date interpretation, amount options and duplicate matching. Its documentation also separates manual entry from bank-connected imports. The details are useful questions to test in any product; they do not establish how every bank export will behave.

Monarch's official tracking page organizes its explanation around account tracking, transactions, reports and recurring activity. YNAB's feature page connects product explanations with import, targets and reporting help. These are different ways to explain the jobs a reader may want to do. A screenshot or a marketing description is not a tested guarantee of outcomes or a substitute for checking current eligibility.

FinCo-Pilot's preview guide explains a file-first review sequence using synthetic records. Its source includes manual accounts, transaction preview/mapping and import controls. Confirm which modules, formats and services are enabled in the application you will actually use before applying real records. No universal bank connection, country eligibility, savings outcome or certification is promised here.

Use the questions below to evaluate the active products rather than assuming that similar labels mean identical behavior.

| Question | Why it matters | FinCo-Pilot evidence boundary |
|---|---|---|
| Can I begin with a manual account? | A bank connection may be unavailable or unnecessary for the first task | Manual account UI/API and existing synthetic test fixtures; selected live runtime still needs acceptance |
| Can I inspect date and amount interpretation? | Ambiguous dates and sign conventions can change records | Preview/mapping implementation and source-backed guide; verify your actual file |
| What happens on repeated import? | Overlapping files can produce duplicates | Existing duplicate/reimport tests; review enabled options rather than assuming universal deduplication |
| Can I identify excluded or failed rows? | A partial import must be recognizable | Preview/error/exclusion paths exist; check counts and samples before applying |
| What does a displayed balance include? | An incomplete history may omit the opening balance or obligations | Guide explicitly separates net flow from confirmed balance |
| What are the current price, support and regional limits? | These can differ by plan, provider and deployment | Read the active application's current information; no unverified comparison numbers reproduced |

A small verified workflow is a better basis for choosing than an unsupported feature total. Keep your original files, use synthetic records while learning, and review the product's current policies before providing real financial information.

## Dated evidence matrix

Official public sources read on 15 October 2026; statements are each vendor's description, not independent product testing. Desktop viewport captures are under `evidence/competitors/`.

| Product | Official source | Browser evidence | Editorial consequence |
|---|---|---|---|
| Actual Budget | https://actualbudget.org/docs/transactions/importing/ | `actual-2026-10-15.jpg`; documentation sidebar, breadcrumbs, task headings and in-page navigation visible | Link educational claims to an actual task guide. Keep bank and file workflows distinct |
| Monarch | https://www.monarch.com/features/tracking | `monarch-2026-10-15.jpg`; task-focused hero, app imagery, CTA and visible consent panel | Use original product evidence and a focused next action. Cookie panel visibility is recorded, not scored as a product defect |
| YNAB | https://www.ynab.com/features | `ynab-2026-10-15.jpg`; distinct hierarchy, illustrative product screen, CTA and consent notice | Keep visual hierarchy clear. Do not borrow review totals, security claims, results or artwork |
| PocketGuard | https://pocketguard.com/ | `pocketguard-2026-10-15.jpg`; browser displayed a regional-unavailability message | Current page text retrieved by search and region-restricted browser state are separate observations. No conclusion about the user's country or global service availability |

Earlier local automation captures failed; `captures.json` retains that historical attempt. The later cloud-browser observations in `visual-captures-2026-10-15.json` add successful evidence without rewriting failure history. No sign-in, private product scraping or restriction bypass occurred. Captures are research evidence only; do not reuse competitors' artwork as FinCo-Pilot marketing assets.

## Editorial acceptance before publication

- Confirm the selected FinCo-Pilot release with the synthetic manual-account/import checks and its actual availability/permissions.
- Recheck official competitors' facts and current regional destinations. This draft omits volatile prices, trial terms and unsupported superiority claims.
- Confirm question demand from actual search/customer evidence; label current intent as a hypothesis.
- Assign one canonical destination only after the intent/cannibalization review. Link to the existing import guide rather than duplicating it.
- Obtain factual/editorial approval; render and test the final page before adding it to the eligible sitemap.
