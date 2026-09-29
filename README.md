# Training Advisor

A daily training-readiness and workout-planning report delivered to Telegram using Intervals.icu, Anthropic's Claude, and GitHub Actions.

## What it does
- Pulls recent activities and wellness data from Intervals.icu
- Reviews recent training load, sessions, and recovery signals
- Produces a concise coaching-style report with Claude (Anthropic), using your profile settings
- Sends the report to Telegram
- Runs automatically on schedule AND instantly when you message the bot
- Optionally integrates with your coach's TrainingPeaks plan

**This is a decision-support tool, not medical advice.** It should not override your coach, symptoms, or clinician's guidance.

---

## Complete Setup Guide

### Prerequisites

You'll need accounts for:
- **Intervals.icu** (free or paid) - for training data
- **Anthropic Console** (https://console.anthropic.com) - for Claude API (requires credits/billing)
- **Telegram** - for receiving reports
- **GitHub** - to host and run the automation
- **Cloudflare** (free) - optional, for instant webhook triggering

---

## Part 1: Core Setup (Required)

### Step 1: Fork this repository

1. Click **Fork** at the top right of this repository
2. This creates your own copy where you'll add your secrets

### Step 2: Get your Intervals.icu credentials

1. Go to https://intervals.icu
2. Log in to your account
3. Go to **Settings → API**
4. Click **Generate API Key** (copy this)
5. Note your **Athlete ID** (visible in the URL or API section)

### Step 3: Get your Anthropic API key

1. Go to https://console.anthropic.com (or platform.claude.com)
2. **Add billing/credits** (Settings → Billing) - API requires payment
   - Add a payment method OR purchase prepaid credits (minimum $5)
   - The API is separate from Claude Pro subscription
3. Go to **Settings → API Keys**
4. Click **Create Key**
5. Copy the key (starts with `sk-ant-api...`)

### Step 4: Create a Telegram bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. BotFather will give you a **bot token** - copy it
4. Start a chat with your new bot (send `/start`)
5. Get your **Chat ID**:
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for `"chat":{"id":123456789}` - that number is your Chat ID

### Step 5: Add GitHub Actions secrets

In your forked repository:

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret** for each of these:

| Secret Name | Value | Where to get it |
|------------|-------|-----------------|
| `INTERVALS_API_KEY` | Your Intervals.icu API key | Intervals.icu → Settings → API |
| `INTERVALS_ATHLETE_ID` | Your athlete ID | Intervals.icu profile/API section |
| `ANTHROPIC_API_KEY` | Your Anthropic API key | console.anthropic.com → API Keys |
| `TELEGRAM_BOT_TOKEN` | Your bot token | @BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | Your numeric chat ID | From getUpdates API call |
| `TRAININGPEAKS_ICAL_URL` | (Optional) Calendar sync URL | TrainingPeaks → Settings → Calendar sync |

**Important:** These secrets are encrypted and never exposed in logs or code.

### Step 6: Configure your profile

1. Edit `config/profile.json` in your repository
2. Update with your actual training zones, goals, and limits:
   - `timezone`: Your local timezone (e.g., "America/New_York", "Europe/London")
   - `vt1_hr_bpm`, `vt2_hr_bpm`: Your heart rate zones
   - `ftp_watts`: Your functional threshold power (if cycling)
   - `weekly_training_hours_target`: Target weekly volume
   - `goal`: Your current training goal

### Step 7: Test it!

1. Go to **Actions** tab in your repository
2. Click **Daily Training Advisor**
3. Click **Run workflow → Run workflow**
4. Wait 30-60 seconds
5. Check Telegram - you should receive your first report!

**If it fails:** Check the Actions log for errors (usually API key issues or missing Intervals.icu data)

---

## Part 2: Instant Webhook Trigger (Optional but Recommended)

By default, reports run on a schedule (06:37 and 16:27 UTC). Add webhook triggering to get instant reports when you message the bot!

### Step 1: Install Node.js and wrangler

On your computer:
```bash
# macOS
brew install node
npm install -g wrangler

# Or download from https://nodejs.org
```

### Step 2: Deploy the Cloudflare Worker

```bash
cd telegram-trigger
wrangler login
wrangler deploy
```

Copy the worker URL that's displayed (e.g., `https://training-advisor-telegram-trigger.YOUR-SUBDOMAIN.workers.dev`)

### Step 3: Create a GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click **Generate new token**
3. Configure:
   - Token name: "Training Advisor Telegram Trigger"
   - Repository access: **Only select repositories** → select your training-advisor fork
   - Permissions: **Actions** → Read and write
4. Generate and copy the token

### Step 4: Set worker secrets

```bash
cd telegram-trigger

# Set GitHub PAT
wrangler secret put GITHUB_PAT
# Paste your GitHub token when prompted

# Set Telegram Chat ID
wrangler secret put TELEGRAM_CHAT_ID
# Paste your numeric Telegram chat ID

# Generate and set webhook secret
openssl rand -hex 24
# Copy the output, then:
wrangler secret put TELEGRAM_WEBHOOK_SECRET
# Paste the random string
```

**Save that random string - you'll need it in the next step!**

### Step 5: Register the webhook with Telegram

Replace the placeholders and run:

```bash
curl "https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook" \
  -d "url=https://training-advisor-telegram-trigger.YOUR-SUBDOMAIN.workers.dev" \
  -d "secret_token=<RANDOM_STRING_FROM_STEP_4>"
```

You should see: `{"ok":true,"result":true,...}`

### Step 6: Test instant triggering

Send any message to your bot → you should get a report within 5-10 seconds!

---

## How to Use

### Daily check-ins

Message your bot with how you're feeling:

```
energy 7, legs feel good, slept well
```

Or include your coach's planned session:

```
energy 6, bit tired. Plan: 4x8 min threshold run
```

The report will:
- Summarize your check-in
- Consider your data from Intervals.icu
- Follow your coach's plan (if provided)
- Recommend today's training or rest

### Special messages

- Send `skip` if you want the scheduled report without a check-in
- Bot commands like `/start` are ignored

### Scheduled reports

Even without messaging, reports automatically run at:
- **06:37 UTC** (morning report)
- **16:27 UTC** (afternoon report)

*Change these times in `.github/workflows/daily.yml` if needed*

---

## Customization

### Change the schedule

Edit `.github/workflows/daily.yml`, lines 17-18:

```yaml
- cron: "37 1 * * *"   # Format: "minute hour * * *" in UTC
- cron: "27 11 * * *"
```

Use https://crontab.guru to help with cron syntax.

### Change the AI model

The default model is `claude-sonnet-4-5-20250929` (Claude Sonnet 5).

To use a different model:
1. Go to **Settings → Secrets and variables → Actions → Variables**
2. Add a new variable named `ANTHROPIC_MODEL`
3. Set the value to your preferred model ID (e.g., `claude-3-5-sonnet-20240620`)

### Adjust training recommendations

Edit `config/profile.json` to refine:
- Heart rate zones
- Power zones
- Weekly volume targets
- Training goals

The AI uses these to tailor recommendations to your fitness level.

---

## Data & Privacy

- **Secrets** are stored encrypted in GitHub Actions (never in code)
- **Training data** from Intervals.icu is sent to Anthropic's API to generate reports
- **No data is stored** beyond the report generation
- Review Anthropic's privacy policy at https://www.anthropic.com/privacy

**Recommendation:** Review your data sharing preferences with both Intervals.icu and Anthropic before enabling.

---

## Troubleshooting

### "Error: Missing required environment variable"
- Check that all secrets are set in GitHub Actions secrets
- Secret names must match exactly (case-sensitive)

### "credential validation failed" or "404 model not found"
- Verify your Anthropic API key at console.anthropic.com
- Ensure you have credits/billing set up
- Check that your account has access to the model being used

### "409 Conflict" from Telegram
- You can't use both `getUpdates` and webhooks simultaneously
- If you set up webhooks, the scheduled cron will work but manual API calls won't
- This is expected behavior

### Workflow runs but no message received
- Check Telegram bot was started (send `/start` to your bot)
- Verify `TELEGRAM_CHAT_ID` is correct (numeric ID, not username)
- Check Actions logs for Telegram API errors

### No Intervals.icu data
- Verify your `INTERVALS_API_KEY` and `INTERVALS_ATHLETE_ID`
- Ensure your Intervals.icu account has recent activities
- Check that API access is enabled in your Intervals.icu settings

### Webhook not triggering
- Run `wrangler tail` while sending a message to see worker logs
- Check webhook status: `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"`
- Verify all worker secrets are set correctly

---

## Cost Estimate

- **GitHub Actions**: Free (within limits - ~2,000 minutes/month)
- **Cloudflare Workers**: Free tier (100,000 requests/day)
- **Intervals.icu**: Free or $8/month for premium
- **Anthropic API**: Pay-as-you-go (~$0.01-0.05 per report, depending on model)
- **Telegram**: Free

**Estimated monthly cost:** $1-5 for API calls, depending on model and usage.

---

## Credits

Built with:
- [Intervals.icu](https://intervals.icu) - Training analytics
- [Anthropic Claude](https://www.anthropic.com) - AI coaching insights
- [Telegram Bot API](https://core.telegram.org/bots) - Message delivery
- [GitHub Actions](https://github.com/features/actions) - Automation
- [Cloudflare Workers](https://workers.cloudflare.com) - Webhook handling

---

## License

MIT License - feel free to fork, modify, and share!

---

## Contributing

Found a bug or have a feature idea? Open an issue or pull request!

**Before sharing your fork:** Make sure no secrets are committed in your git history. All credentials should only be in GitHub Actions secrets.
