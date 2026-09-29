# Telegram → GitHub Actions trigger

A small Cloudflare Worker that makes your Telegram check-in message fire the
"Daily Training Advisor" workflow immediately, instead of waiting on
GitHub's `schedule:` cron (which can run hours late).

The existing `schedule:` cron in `.github/workflows/daily.yml` stays in
place as a fallback for the days you forget to check in. **This means on a
day you message the bot right around 06:37 or 16:27 Tashkent time, you may
get two reports close together.** That's a known, accepted tradeoff, not a
bug — see the main README's Troubleshooting section if you want to change
it later (e.g. drop the cron, or add dedup).

## What it does

1. Telegram calls the worker's URL the instant you send the bot a message.
2. The worker checks the request really came from Telegram (secret token)
   and really is your chat (chat ID), then calls GitHub's API to dispatch
   `daily.yml` on `main`.
3. `app/main.py` reads your check-in text itself via the Telegram API, same
   as it does today — this worker only controls *when* the workflow runs,
   it doesn't touch the check-in content.

## One-time setup

### 1. Create a GitHub PAT
GitHub → Settings → Developer settings → **Fine-grained personal access
token** → scope it to only this repository → permission **Actions: Read
and write**. Nothing else. Copy the token.

### 2. Install wrangler and log in
```bash
npm install -g wrangler
wrangler login
```

### 3. Deploy the worker
```bash
cd telegram-trigger
wrangler deploy
```
This prints your worker's URL, e.g.
`https://training-advisor-telegram-trigger.<your-subdomain>.workers.dev`.

### 4. Set the secrets
```bash
wrangler secret put GITHUB_PAT
# paste the PAT from step 1

wrangler secret put TELEGRAM_CHAT_ID
# paste your numeric Telegram chat id (same value as the
# TELEGRAM_CHAT_ID GitHub Actions secret)

wrangler secret put TELEGRAM_WEBHOOK_SECRET
# make up any random string, e.g.: openssl rand -hex 24
```

### 5. Register the webhook with Telegram
Use the **same** random string you just set as `TELEGRAM_WEBHOOK_SECRET`:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -d "url=https://training-advisor-telegram-trigger.<your-subdomain>.workers.dev" \
  -d "secret_token=<the random string>"
```

Telegram replies `{"ok":true,"result":true,...}` on success.

### 6. Test it
Message the bot anything. Check **Actions** in the repo — a new run of
"Daily Training Advisor" should appear within a few seconds, triggered by
`workflow_dispatch`, not `schedule`.

## Troubleshooting
- `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"` shows the
  current webhook and the last delivery error, if any.
- `wrangler tail` streams the worker's live logs while you send a test
  message.
- A `403` from the worker means the secret token didn't match — re-check
  step 4/5 used the exact same string.
