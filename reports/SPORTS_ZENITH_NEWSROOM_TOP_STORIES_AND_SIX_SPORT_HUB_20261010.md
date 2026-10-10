# Sports Zenith — Newsroom: Top Stories Home + Full Sports News Hub

**Verified UTC 2026-10-10; scoped update of existing https://sportszenith.com.**

## User instruction
“**The home page just keep top news! And then the news page it can be all top news articles for sports all organized.**” User also explicitly requested recognizable color-linked symbols for Injury (red medical sign), Recap (newspaper), Fantasy and other types; premium, readable, more colorful sports broadcasting look rather than a bland dark app.

## What was wrong before
Home used an inline four-item \`HomeImpactNews\` selector from the full \`ask_retrieval.json\` research graph. It sorted purely by date and could fill all four cards with sequential weekly Fantasy ranking links. The News & Insights page rendered **at most 18** articles after filtering and did not expose the entire six-sport ESPN article collection. Its large original “Future original publishing engine” draft workbench occupied important main-column space ahead of the user's true news needs.

The source data itself contained \`661\` records in a mixed article/fact graph; **only 180** were separately marked \`event_source_type=NEWS\` with attributed ESPN links across **30 each** for NFL/NHL/NBA/MLB/college football/college basketball at the documented frozen source timestamp. The other 481 included structured injury/fact rows and must not be presented as newly authored sports news articles. Some NEWS entries were video-only highlights, duplicate article summaries, or missing URL. One original report incorrectly labeled a generic CFB expert-preview video “INJURY”; using that raw label would show a misleading injury sign.

## Exact implementation

### Home
- A single compact **Top sports news** section showing at most **four current source-linked articles from the last 48 hours**, favoring one legitimate injury, one genuine completed-game recap, plus priority/league diversity.
- Recognizable **red bandage Injury**, **warm gold Newspaper Recap**, **aqua Fantasy clipboard**, **teal Lineup**, **violet Roster move**, **blue Odds news/Headline** icons used consistently; no cartoon clip art or unlicensed images.
- Cards retain the existing Home navy background with narrow category color stripe; source name, Eastern timestamp and original article link are visible. \`All sports news\` opens **News & Insights** at \`#news\`.
- There is no fake “confirmed player injured” state: the category is an **attributed article description**, not a verified lineup/model update. If the original reporting feed is missing/stale/empty, the banner states an explicit source condition instead of presenting yesterday's item as breaking news.
- Replaced the earlier Home-only \`HomeImpactNews\` block without altering the actual Bet, Survivor, DFS, Props, PrizePicks or Brain Record content.

### Full News & Insights page
- New brighter **Zenith Newsroom** cream/ivory header with aqua-blue accents and original newspaper mark; article reading cards stay light and readable.
- Entire **six-sport collection** indexed and browsable by NFL, NHL, NBA, MLB, CFB and CBB, by story categories **All / Injuries / Recaps / Fantasy / Lineups / Roster moves / Odds news / General headlines**, by free text (player/team/title), and by priority or chronological newest-first ordering.
- Default view highlights **three cross-sport headline stories** followed by six **separate league sections**, each previewing three articles. This keeps the main page manageable on iPhone instead of dumping 160 stacked cards at once. Choosing a league shows twelve, with working **Show more** until all original source-linked league articles can be opened; the old hard \`slice(0,18)\` limit is gone.
- Opening a story launches the authentic ESPN article in a new tab with \`noopener noreferrer\`. **Full ESPN copyrighted text is not copied into Zenith.**
- A dedicated \`DATA SOURCE FAILURE\` / \`SOURCE STALE\` / \`NO QUALIFIED ARTICLES\` distinction prevents a collector failure from silently appearing as “no news.” Both Home and News use the same timestamp, 6h source-health threshold, deterministic headline classification and deduplication.
- The preexisting complete manual editorial-draft workspace (injury impact, Survivor commentary, pick-em and structured draft evidence) is **preserved** but lazily loaded under an explicit collapsed **Editorial research lab · drafts only, no automatic publishing** control rather than treated as published news.
- The small redundant floating Ref launcher is hidden only on Home and News; The Ref remains available via the shared header/nav and its dedicated Ask page. No change to the actual chatbot or odds-model logic.

### Frozen original-source proof
Compressed, byte-identical source archive:
\`reports/SPORTS_ZENITH_NEWS_SOURCE_FIXTURE_20261010.json.gz\`
- Original public research graph was generated at **2026-10-10 05:26:28.327839 UTC**
- \`661\` mixed news/fact records; \`180\` attributed article records
- **160** source-linked articles pass qualified-source and no-duplicate/no-video/no-promo validation: **NFL 30; NHL 25; NBA 22; MLB 27; CFB 27; CBB 29**; **13** distinct sports recaps (including many ESPN \`/recap?gameId=...\` URLs formerly incorrectly deduplicated to one generic \`/recap\` path).
- Original raw source SHA256: \`11eb3bb010a3055e0403a574471dfc81c7546814bba539dd973f70ef271831a1\`.
- Deterministic gzip archive SHA256: \`6a6b80f8f78b960079b8e8003e159455bb3ca1ab10a9521a523f8b457d7f888d\`.
- Stable screenshot/test fixtures now use this immutable archived source. Live user-facing Home and News always re-fetch the current JSON without cache on a five-minute interval and show fresh real counts. This means a normal source feed update does not break previously verified UI acceptance or quietly rewrite this saved source proof.

### Files
- \`commercial_web/news_curation.js\` pure article validation, source/link deduplication, type-signed category, urgency/recency scoring, diversity-limited Home four, deterministic filters and grouping.
- \`commercial_web/src/useSportsNews.js\` common source health+refresh hook.
- \`commercial_web/src/NewsStoryCard.jsx\` consistent original Lucide icons and category color system.
- \`commercial_web/src/HomeTopNews.jsx\` four-headline Home component.
- \`commercial_web/src/SportsNewsHub.jsx\` full browse/search/filter/show-more newsroom.
- \`commercial_web/src/App.jsx\` only the two news surfaces replaced; previous manual editorial work preserved under an expansion.
- \`commercial_web/news_curation.test.js\`, \`commercial_web/sports-news-hub.e2e.spec.js\`, \`commercial_web/home-theme-continuity.e2e.spec.js\` cover source snapshots, medical icon truth, separate recap game IDs, no promotional/invalid sources, six league discovery, original links, filter and pagination, Home navy continuity and other app navigation.
- Original \`App.jsx\` and \`styles.css\` copied and source-SHA checked to \`.deploy_backups/zenith_news_hub_before_20261010T0525Z\` before editing.

## Acceptance / unchanged boundaries
- First release build passed Vite; actual desktop and iPhone Playwright inspected the public HTTPS page with **0 horizontal overflow and 0 script errors**. Newsroom headline starts around y=700px on 390x844 after compacting title/filter; no fake data source or sponsored content added.
- Eight dedicated pure curation tests and nine dedicated browse/click/filter/empty-status browser tests passed before wider acceptance.
- **Completed acceptance:** **240/240** Node website tests (including **nine dedicated news curation/source-SHA cases**), **38/38** Python model and source-safety tests, and **72/72** Playwright browser tests on mobile and desktop, including **nine dedicated Newsroom browser cases**. Production Vite build PASS. The public HTTPS News page showed about **160** linked article entries across six sports at review time. iPhone 390px and desktop 1280px had **no horizontal overflow** and no page JavaScript errors.
- End-to-end navigation from Home → `#news`, category icons, articles opening true ESPN source URLs, league filters exposing all available articles by Show more, query search, top/newest sorting, source failure vs valid-empty, and unchanged private Survivor/model routes were verified.
- The Git checkpoint is stored in the same existing VPS repository; **no independent off-server restoration** has been verified as part of this news-only change.
- **No changes** to sportsbook source odds, independent prediction model, frozen forecast ledger, original Sports Zenith Survivor private account state, wagers, sportsbook connections or off-server recovery. Existing unrelated uncommitted server.js/Survivor edits are explicitly not staged.
- ESPN is currently the only public attributed article source connected to this feed. Additional editorial sources and original Zenith-authored article publishing can be considered separately, only with appropriate rights and verifiable source provenance. This release does **not** auto-author or auto-publish articles.
