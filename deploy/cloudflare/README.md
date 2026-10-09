# Sports Zenith — Cloudflare live tunnel

**Current state (Oct 9, 2026):** `sportszenith.com` and `www.sportszenith.com` were routed through Cloudflare to the existing OVH site at `http://127.0.0.1:8510`. DNS, TLS (verified public HTTPS), existing web app, and authorized public health API passed. Local user-systemd service `sports-zenith-cloudflared.service` is running and enabled, and the ubuntu user has `Linger=yes`.

Tunnel name: `sports-zenith-ovh`, ID: `37727b31-5a2a-4376-b28d-629af6926d61`.

## Architecture

- Browser: `https://sportszenith.com` or `https://www.sportszenith.com`
- Cloudflare edge: public TLS certificate, proxy DNS and Cloudflare Tunnel
- Outbound tunnel: `/home/ubuntu/bin/cloudflared`, authenticated with a private named-tunnel credentials JSON
- On this VPS only: `http://127.0.0.1:8510` (existing Sports Zenith API/server)
- The public website, browser PWA, and packaged iOS/Android React UI use **one** backend. No paid Workers or second website were created.

The actual connector configuration lives at `/home/ubuntu/.cloudflared/config.yml` (mode 0600). It matches the versioned, non-secret `config.yml.example`. Private account certificate `cert.pem` (0600) and tunnel JSON (0400) are NOT in Git, not in any public repo, and never passed to user-visible output. Local-only private recovery archive is stored in `.deploy_backups/zenith_cloudflare_live_tunnel_20261009T1710Z/PRIVATE_cloudflared_credentials_do_not_publish.tar.gz` with mode 0600; its four files passed checksum restore on this same VPS. **Off-VPS recovery remains unverified.**

## Live checks

```sh
bash scripts/verify_sports_zenith_cloudflare.sh
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
systemctl --user status sports-zenith-cloudflared.service
journalctl --user -u sports-zenith-cloudflared.service -n 30 --no-pager
/home/ubuntu/bin/cloudflared tunnel info sports-zenith-ovh
/home/ubuntu/bin/cloudflared tunnel --config /home/ubuntu/.cloudflared/config.yml ingress validate
```

Do not run cloudflared with debug header logging while handling authenticated user sessions; it can log access tokens. Do not print the private `cert.pem` or tunnel JSON.

## Remaining security task — Cloudflare dashboard

The tunnel and valid HTTPS certificate are working, but Cloudflare initially also permitted ordinary HTTP responses (200 rather than redirect). **The domain owner must enable Cloudflare SSL/TLS → Edge Certificates → Always Use HTTPS**, rather than adding a redirect inside the OVH app (Cloudflare specifically warns origin redirects can cause loops). Check that SSL/TLS mode is not Off; leave other unrelated rules/settings unchanged. Then re-run `scripts/verify_sports_zenith_cloudflare.sh` and require a 301/308 redirect from HTTP to HTTPS for both hosts. Official reference: https://developers.cloudflare.com/ssl/edge-certificates/additional-options/always-use-https/

The existing OVH listener on `0.0.0.0:8510` is **still reachable directly via the VPS IP** so the former IP-based site and existing integrations do not break. If we later want to require Cloudflare only, arrange a migration window and explicit approval before changing bind/firewall rules. No original Sports Zenith server code, picks, data, betting models, or user sessions were edited to create this tunnel.

## Safe recovery

1. Verify the local private tunnel recovery archive's authenticity and keep permissions strict (do not commit, publish or paste it).
2. On the owner-authorized VPS, restore the real `/home/ubuntu/.cloudflared` contents only after checking whether new credentials already exist, and copy `sports-zenith-cloudflared.user.service` to `~/.config/systemd/user/sports-zenith-cloudflared.service`.
3. `systemctl --user daemon-reload && systemctl --user enable --now sports-zenith-cloudflared.service` with the correct `XDG_RUNTIME_DIR` and user bus. Preserve Ubuntu linger.
4. Confirm the existing local API works and that Cloudflare's apex and www DNS CNAME records route to `37727b31-5a2a-4376-b28d-629af6926d61.cfargotunnel.com`.
5. For recovery of other server/database/user files, this tunnel archive is insufficient. Keep independent disaster backups of the website and all data, and verify restoration off-VPS.

To stop the tunnel temporarily: `systemctl --user stop sports-zenith-cloudflared.service` (public hostname would stop working, but original IP-based backend remains). DNS rollback is performed only with deliberate change approval in the Cloudflare dashboard, not by deleting the working tunnel blindly.

## Mobile

On Oct 9, the shared React UI was rebuilt with verified `ZENITH_MOBILE_API_ORIGIN=https://sportszenith.com`, 51 obsolete JSON feed snapshots were stripped, and the bundle was synced into both Capacitor platform source trees. This is **not an Apple/Google release**. No iOS .ipa or Android .apk/.aab has been signed, and native OTP, Survivor pick saving, push notifications, real-device testing and sports betting/DFS store compliance must still pass.
