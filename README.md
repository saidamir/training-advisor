# Training Advisor

A daily training-readiness and workout-planning report delivered to Telegram using Intervals.icu, Anthropic's Claude, and GitHub Actions.

## What it does
- Pulls recent activities and wellness data from Intervals.icu.
- Reviews recent training load, recent sessions, and available recovery signals.
- Produces a concise coaching-style report with Claude (Anthropic), using explicit profile settings.
- Sends the report to Telegram.
- Runs on a daily GitHub Actions schedule and can also be triggered manually.

This is a decision-support tool, not medical advice. It should not override your coach, symptoms, or clinician's guidance.

## Setup

### 1. Add GitHub Actions secrets
In the repository, open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `INTERVALS_API_KEY`: your Intervals.icu API key.
- `INTERVALS_ATHLETE_ID`: your athlete ID (often visible in your Intervals.icu profile/API settings).
- `ANTHROPIC_API_KEY`: your Anthropic API key.
- `TELEGRAM_BOT_TOKEN`: token from BotFather.
- `TELEGRAM_CHAT_ID`: the chat ID where the report should be sent.
- `TRAININGPEAKS_ICAL_URL` (optional): your TrainingPeaks Calendar Sync link, so reports follow your coach's plan. In TrainingPeaks: your name → Settings → Calendar sync (Premium). Changes can take up to 24 hours to appear in the feed.

Optionally add an Actions **variable** (not a secret) `ANTHROPIC_MODEL` to override the default model (`claude-sonnet-5`).

### 2. Set profile variables
Edit `config/profile.json` to set your training zones, preferred easy-day limits, weekly structure, and goals. Defaults are starter values and should be reviewed.

### 3. Run it
Go to **Actions → Daily Training Advisor → Run workflow** to test manually.

The workflow is scheduled twice daily at 01:37 and 11:27 UTC (06:37 and 16:27 Uzbekistan time, UTC+5). GitHub may start scheduled jobs later than the exact minute.

### 4. Daily check-in
Before each report (around 06:30 and 16:15), message the bot how you feel: energy, soreness, back pain, mood, fatigue, illness symptoms, motivation, in any words. To have the report follow your coach's session, add it after `Plan:`, for example `energy 6, back 2/10. Plan: 4x8 min threshold run`. Send `skip` or nothing to get a report without a check-in. Any message sent before the report actually runs is included. The evening report also takes that morning's check-in into account.

## Data and privacy
Secrets are stored in GitHub Actions and are not committed to the repository. Activity and wellness data are sent to the Anthropic API to generate the narrative report. Review your provider settings and privacy requirements before enabling the workflow.

## Troubleshooting
- Confirm the Intervals.icu API key and athlete ID.
- Confirm the Telegram bot has been started by the target chat and that the chat ID is correct.
- Check the **Actions** run log for API or configuration errors.
