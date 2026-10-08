# Sports Zenith sign-in modal centering fix — acceptance

The live sign-in popup was rendered under an 80-pixel sticky header stacking context; `position: fixed` used that header rather than the browser viewport, placing the email field above the visible screen. Browser reproduction before the fix at 1365×768 showed overlay height 80px, dialog y=-253px, and email y=-25px. At 390×844 the email y=-306px.

Fix is isolated to commercial_web/src/AuthShell.jsx: render the AccountModal in a React portal under document.body so transformed or backdrop-filtered header ancestors cannot constrain it; center the backdrop/dialog in the actual viewport at all breakpoints; cap height to the dynamic viewport with internal scrolling on small windows; remove mobile-disruptive email autofocus. The existing email OTP and verified code flows, auth data, form and user preferences are unchanged.

Automated Chromium/Playwright visual DOM checks PASS on isolated production build at 1365×768, 1024×600, 390×844, 375×667, 320×568 and 844×390. In every case backdrop fully covered the browser viewport, dialog centered, email visible and editable with dummy local text only, and close button removed dialog. No sign-in email was sent. All 86 existing Node/API/UI tests and Vite production build PASS with unrelated live App.jsx Props refactor preserved in the tested build.
