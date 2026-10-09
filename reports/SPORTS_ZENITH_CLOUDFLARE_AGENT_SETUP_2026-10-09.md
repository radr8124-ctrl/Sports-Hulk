# Sports Zenith — Cloudflare agent setup (2026-10-09)

This is a completed **technical integration preparation**, not a registered domain, Cloudflare account authorization, or live DNS change.

Official instructions fetched successfully from https://developers.cloudflare.com/agent-setup/prompt.md (HTTP 200; source SHA-256 8c0825e1d8f83e2c4546edef52bd86bfabddbd9e4d504d963a93f96a6be062f7).

## Completed on the OVH VPS

- Ran Cloudflare's official global skills install command for other coding agents. Sixteen new Cloudflare skills passed nonempty SKILL.md readback in the ubuntu user's global skills directory; the five existing skills remained intact.
- Verified Cloudflare, Wrangler, Cloudflare One, Workers best practices, web performance, Turnstile and other modules are readable. The installer warned that the PromptScript agent type does not support global installations; this did not prevent the sixteen canonical global skills from being installed.
- Registered the official Cloudflare MCP remote endpoint https://mcp.cloudflare.com/mcp through the OpenAI Codex CLI, persisting its configuration at the ubuntu user's Codex MCP config. Codex explicitly reports Cloudflare as **enabled but not logged in**. No access token, login credentials or billing information was saved in the project.
- The first MCP registration began a default OAuth request with very broad Cloudflare read/write scopes. That process was stopped without granting access. No domain purchase, DNS record edit, WAF edit, Cloudflare account modification or origin change occurred.
- Verified the existing Sports Zenith web API remained healthy (HTTP 200).
- Backed up the original global agent skills before installing new skills. Backup is local to the VPS, not an independent off-server restore.

## Important boundaries

This ChatGPT session does not currently have an installed Cloudflare account connector. The Codex MCP configuration on the VPS is intended for compatible coding agents; it does **not** automatically make Cloudflare account tools available in this ChatGPT conversation.

Cloudflare's beta cf CLI was not installed. Its official prompt makes this optional and asks for user confirmation before installation.

The VPS is headless, so the OAuth flow's callback to localhost cannot be completed safely from an iPhone without additional browser access or an authorized tunneled client. Avoid pasting OAuth callback URLs, API tokens or browser secrets into the chat. If account access is enabled later, start with narrowly reviewed Cloudflare permissions for discovery; request domain registration or DNS-write permissions only when the specific change is approved.

## Next prerequisites for SportsZenith.com

1. Create or sign into https://dash.cloudflare.com/ and verify the owner's account email; enable multifactor authentication.
2. Check actual domain availability and pricing through Cloudflare Registrar. A Namecheap result is not a Cloudflare price quote. Domain registration requires explicit user approval, valid contact/billing information, and confirmation immediately before charging.
3. After registration, prepare Cloudflare DNS for the existing OVH website without disturbing its working app. Configure HTTPS between Cloudflare and the origin, including a suitable secure reverse proxy; verify both domain and HTTPS before connecting iOS/Android app clients.
4. Authenticate the Cloudflare MCP from a supported authorized browser-capable agent, reviewing least-privilege scopes and billing implications. Do not approve the default broad scope list blindly.
5. Only after verified HTTPS, test native login, Survivor saving, live scores, notifications, compliance and device builds. App-store approvals remain separate.

See the machine-readable acceptance receipt at reports/SPORTS_ZENITH_CLOUDFLARE_AGENT_SETUP_ACCEPTANCE_2026-10-09.json for original source SHA, exact skills installed, account status, backup path and MCP registration verification.

**Truthful status:** agent knowledge installed; MCP endpoint registered in Codex but OAuth not connected; Cloudflare account/registrar ownership not verified; no domain purchased; no DNS changes; Sports Zenith currently online; no off-VPS restoration verified.
