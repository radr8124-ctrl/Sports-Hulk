# Sports Zenith Migration & Recovery

## Current production layout
- Host: OVH VPS `vps-2ebed3cb`
- Repo: `/home/ubuntu/sports-hulk`
- Commercial frontend/server: `/home/ubuntu/sports-hulk/commercial_web`
- Commercial app port: `8510`
- User service: `sports-hulk-commercial.service`
- Temporary public tunnel: `sports-hulk-commercial-preview.service`
- Customer identity/auth: InsForge
- Source remote: GitHub `radr8124-ctrl/Sports-Hulk`

## Critical persistent state
These are not disposable build artifacts:
- `data/sports_members.sqlite3`
- `commercial_web/private_member_links.json` (temporary compatibility fallback during member migration)
- InsForge users/sessions/profile records
- InsForge member-owned tables: `survivor_entries`, `survivor_decisions`, `fantasy_leagues`, `fantasy_rosters`, `fantasy_advice`
- Future subscription/account entitlement tables
- Official forward ledgers / accountability history under `intelligence_warehouse/`
- Survivor ownership/rule/history inputs that cannot be regenerated from public feeds

Production Survivor ownership is stored in InsForge with row-level security. Authenticated customers can read only rows whose `owner_id = auth.uid()`; claim/ownership writes are server-admin only after the one-time claim code is validated. The private JSON mapping remains only as a temporary fallback until the migration is fully retired.

Never commit secrets, environment files, claim codes, private member links, or user databases to a public repository.

## Disposable / reproducible data
These can be regenerated and should not be treated as source backups:
- `commercial_web/node_modules/`
- `commercial_web/dist/`
- `commercial_web/public/*.json`
- logs, screenshots, test output, `__pycache__`

## New-server migration
1. Provision a fresh Ubuntu VPS.
2. Clone the GitHub repository into `/home/ubuntu/sports-hulk`.
3. Restore protected environment/secrets from the secure secret backup.
4. Restore persistent private state and official ledgers.
5. Install Python/Node dependencies.
6. Copy the unit files from `deploy/systemd/system/` and `deploy/systemd/user/`.
7. Run `systemctl daemon-reload` and the user daemon reload.
8. Enable the commercial app, score refresh, insights refresh, performance refresh and sport collectors.
9. Build the commercial frontend.
10. Start on a private test hostname/port and validate auth, scores, box scores, betting truth, Fantasy/DFS, Survivor, News, Brain Record and Ask.
11. Point SportsZenith.com to the new production endpoint only after acceptance tests pass.
12. Keep the old VPS online temporarily for rollback.

## Scaling path
- Phase 1: shared build VPS during development/beta.
- Phase 2: dedicated Sports Zenith VPS once traffic/subscriptions justify it.
- Phase 3: separate persistent database/storage and cache/CDN.
- Phase 4: multiple app servers behind a load balancer.

## Recovery rule
A server should be replaceable from:
1. GitHub source,
2. service/deployment files in this repo,
3. protected persistent-state backup,
4. InsForge account data,
5. environment/secrets backup.

The domain must never be the only path to the application and the VPS must never be the only copy of source or customer state.
