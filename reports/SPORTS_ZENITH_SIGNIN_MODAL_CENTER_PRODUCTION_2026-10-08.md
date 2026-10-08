# Sports Zenith sign-in modal centering — live release

UTC release date: 2026-10-08. Feature commit: cc70cb7. Rollback: `.deploy_backups/sports_zenith_auth_modal_20261008T042259Z` and recovery branch `backup/pre-sports-zenith-signin-modal-20261008T042259Z`.

**Root cause reproduced:** The account dialog's fixed backdrop was rendered inside the 80-pixel header, which has backdrop-filter/stacking-context positioning. Playwright geometry on the original live site gave overlay height 80 instead of viewport height 768 (desktop) and the email field above the visible page (email top -25 desktop, -306 on 390px mobile).

**Fix:** React `createPortal` mounts AccountModal directly in `document.body` instead of the header. Backdrop/dialog are centered vertically and horizontally with dynamic viewport height and internal scrolling on smaller screens. Mobile-disruptive automatic email input focus is removed. The existing secure email/OTP implementation was not changed.

**Verification:** 86/86 existing Node/API/UI tests PASS, Vite production build PASS, isolated real-browser preview test PASS across 1365x768, 1024x600, 390x844, 375x667, 320x568, 844x390. Published live browser smoke PASS across desktop 1365x768 and mobile 390x844, 375x667, 320x568, including full overlay, exact centered dialog, visible editable email, and working close button. No sign-in code was sent. Live web, health and Survivor endpoints HTTP 200.

**Safety:** Only `commercial_web/src/AuthShell.jsx` modified. All prior uncommitted App.jsx and PropsV2Panel.jsx work preserved byte-for-byte; the old full static site is backed up and prior hashed assets remain served for existing sessions.
