# Sports Zenith verification-email and visible member branding

UTC date: 2026-10-08.

## Root cause and correction

Sports Zenith's frontend was already branded correctly, but the live cloud InsForge project behind passwordless sign-in still had the original **Sports-HULK** project name. The actual live backend was identified by matching the website's configured InsForge URL to its cloud project. The separate cloud branch named `sports-dashboard` was left untouched.

The live **Sports-HULK** authentication cloud project was renamed to **Sports Zenith** with the authenticated InsForge cloud CLI. A read-only subsequent project query confirmed the new project name and ACTIVE status in its existing region. No project identifiers, domains, API keys, database settings, subscription settings, or other projects were changed.

The live InsForge `request-otp` verification-email template was updated using the authenticated admin API: subject is now `{{ token }} is your Sports Zenith sign-in code`, and the template body identifies the sign-in experience as Sports Zenith. The original `{{ token }}` placeholder and five-minute code expiry wording were preserved. Other auth templates were not modified. A protected copy of the previous OTP template is stored in `.deploy_backups/zenith_otp_email_20261008T045937Z` for rollback.

Read-after-write from the InsForge admin API confirmed exact new subject, branded body and preserved OTP token placeholder. Custom SMTP remains disabled exactly as before. The auth public configuration returned HTTP 200 and still uses six-digit code verification. Commercial website, sports API and Survivor endpoints returned HTTP 200. An actual new email was not sent during testing, so recipient-side sender-header display still needs confirmation by a real user requesting their next code.

## Customer-facing UI follow-up

Corrected three remaining customer-visible Sports HULK references in main-site Survivor pick editing and saved-result cards to Sports Zenith. Added a Node regression that ensures the account and Survivor UI source no longer contains customer-visible old-brand references. The internal development repository/project retains its original HULK name; only the customer brand changes.
