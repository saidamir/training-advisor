/**
 * Cloudflare Worker: runs the "Daily Training Advisor" GitHub workflow.
 *
 * Two ways in:
 *   - fetch: Telegram calls this worker (via a webhook) the instant you send
 *     the bot a message. The worker checks it's really Telegram and really
 *     your chat, then dispatches the workflow with the check-in text and
 *     timestamp as inputs.
 *   - scheduled: Cloudflare Cron Triggers (see wrangler.toml) dispatch the
 *     workflow at the report times. GitHub's own `schedule:` runs hours late,
 *     Cloudflare's run on the minute.
 *
 * Required secrets/vars (set with `wrangler secret put <NAME>` unless noted):
 *   GITHUB_PAT               - fine-grained PAT, "Actions: write" on this repo only
 *   GITHUB_OWNER              - e.g. "saidamir"          (plain var is fine)
 *   GITHUB_REPO               - e.g. "training-advisor"   (plain var is fine)
 *   WORKFLOW_FILE              - e.g. "daily.yml"          (plain var is fine)
 *   GITHUB_REF                 - branch to run, e.g. "main" (plain var is fine)
 *   TELEGRAM_CHAT_ID          - your chat id, so a stranger can't fire your workflow
 *   TELEGRAM_WEBHOOK_SECRET   - random string, must match Telegram's secret_token
 */

async function dispatchWorkflow(env, inputs) {
  const dispatchUrl =
    `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}` +
    `/actions/workflows/${env.WORKFLOW_FILE}/dispatches`;

  const body = { ref: env.GITHUB_REF || "main" };
  if (inputs) {
    body.inputs = inputs;
  }

  return fetch(dispatchUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_PAT}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "training-advisor-telegram-trigger",
    },
    body: JSON.stringify(body),
  });
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("ok", { status: 200 });
    }

    // Telegram sends this header on every webhook call when the webhook was
    // registered with a secret_token. Reject anything that doesn't match so
    // random internet traffic can't trigger your workflow.
    const secretHeader = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
    if (!env.TELEGRAM_WEBHOOK_SECRET || secretHeader !== env.TELEGRAM_WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }

    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("bad request", { status: 400 });
    }

    const message = update.message || update.edited_message;
    const chatId = message && message.chat && String(message.chat.id);

    // Only your own chat can fire the workflow.
    if (!chatId || chatId !== String(env.TELEGRAM_CHAT_ID)) {
      return new Response("ignored", { status: 200 });
    }

    // Ignore non-text updates (stickers, photos with no caption, etc.) —
    // there's nothing for app/main.py's check-in parser to read.
    if (!message.text) {
      return new Response("ignored", { status: 200 });
    }

    // Pass the check-in message text and timestamp as workflow inputs
    const ghResponse = await dispatchWorkflow(env, {
      checkin_text: message.text,
      checkin_timestamp: String(message.date),
    });

    if (!ghResponse.ok) {
      const body = await ghResponse.text();
      console.error(`GitHub dispatch failed: ${ghResponse.status} ${body}`);
      return new Response("dispatch failed", { status: 502 });
    }

    return new Response("dispatched", { status: 200 });
  },

  async scheduled(event, env) {
    const ghResponse = await dispatchWorkflow(env);
    if (!ghResponse.ok) {
      const body = await ghResponse.text();
      // Throwing marks the cron run as failed in the Cloudflare dashboard.
      throw new Error(`GitHub dispatch for cron "${event.cron}" failed: ${ghResponse.status} ${body}`);
    }
    console.log(`Dispatched the report for cron "${event.cron}"`);
  },
};
