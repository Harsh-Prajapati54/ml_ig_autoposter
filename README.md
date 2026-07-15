# ML/AI Instagram Auto-Poster

Automated pipeline: picks an ML/AI topic → writes a caption + slide copy with an LLM
(Groq) → renders dark-themed image card(s) with Pillow → hands the finished post off for
publishing. Runs on a daily schedule via GitHub Actions — no server needed.

Two publish modes, controlled by one setting (`PUBLISH_MODE`) — **no code changes** to
switch between them:

- **`drive`** (default, current mode) — saves each post as a dated Google Drive folder
  (images + `caption.txt`) for you to open and upload to Instagram yourself.
- **`instagram`** — publishes straight to Instagram via the official Graph API, once your
  IG Business account is linked. See "Switching to instagram mode later" at the bottom.

```
topics.py ──► content_generator.py ──► image_generator.py ──► drive_uploader.py (mode=drive)
 (pick a       (Groq: caption,          (Pillow: dark-themed          or
  topic)        slides, hashtags,        PNG card(s), single      github_host.py + instagram_publisher.py (mode=instagram)
                format: single/           or carousel)
                carousel)
```

`github_host.py` is also used regardless of mode, just for small JSON state files
(topic rotation history, post log) — it's cheap, and it already lives in the repo you
push this code to.

## One-time setup (Drive mode — do this first)

### 1. Get a Groq API key
Sign up at [console.groq.com](https://console.groq.com) and grab an API key.

### 2. Create a GitHub repo + token
- Create a **public** GitHub repo (this same repo works fine) — used to store small state
  files (`data/used_topics.json`, `data/posts_log.json`).
- For **local testing only**: create a fine-grained Personal Access Token with
  `Contents: Read and write` scoped to that repo. (Not needed in GitHub Actions — see below.)

### 3. Setting up Google Drive
1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create a new
   project (e.g. `ml-ig-autoposter`).
2. **APIs & Services → Library** → search **Google Drive API** → **Enable**.
3. **APIs & Services → OAuth consent screen**:
   - User type: **External**
   - Fill in app name, your email as support/developer contact
   - Scopes: add `https://www.googleapis.com/auth/drive.file` (this is a **non-sensitive**
     scope, so it doesn't require Google's manual review process)
   - Test users: add your own Google account
   - Once set up, click **Publish app** to move status to **In production**. Because
     `drive.file` is non-sensitive this is just a confirmation click — no review, no
     waiting. Skipping this step means your refresh token expires every 7 days instead of
     lasting indefinitely.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app**
   - Copy the **Client ID** and **Client Secret**
5. Run the one-time authorization script locally (opens your browser):
   ```bash
   pip install google-auth-oauthlib
   python authorize_drive.py
   ```
   Paste in the Client ID/Secret when asked, approve access in the browser, and it prints
   a `GOOGLE_REFRESH_TOKEN` — save that along with the client ID/secret.

## Local testing

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in every value (PUBLISH_MODE=drive by default)
python main.py --dry-run  # generates content + saves images to generated/, no upload
python main.py            # generates + uploads a real post folder to Drive
```

## Going fully automatic

1. Push this repo to GitHub.
2. Repo → **Settings → Secrets and variables → Actions**, add as **secrets**:
   `GROQ_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`.
3. Same page, add as **variables** (not secrets — these aren't sensitive):
   `PUBLISH_MODE` = `drive`, `GROQ_MODEL` (e.g. `openai/gpt-oss-120b`), `IG_HANDLE`
   (e.g. `@your.handle`), and optionally `GOOGLE_DRIVE_FOLDER_ID` if you want post-folders
   nested inside an existing Drive folder.
4. `GITHUB_TOKEN` is provided automatically by Actions — no setup needed for it.
5. Edit the `cron:` line in `.github/workflows/daily_post.yml` to your preferred posting
   time (it's in UTC).
6. Trigger it once manually from the **Actions** tab (`Run workflow`) to confirm it works,
   then check Drive for the folder before trusting the schedule.

Each run drops a folder named like `2026-07-15 - How Attention Actually Works` into your
Drive with the image(s) and `caption.txt` — open it, download, post to Instagram normally.

## Switching to instagram mode later

Once your Instagram Business account is linked (see previous conversation for that
walkthrough) and you've completed the Meta app / token steps below, switching over is just:

1. Add secrets: `IG_ACCESS_TOKEN`, `IG_USER_ID`.
2. Change the `PUBLISH_MODE` repo **variable** from `drive` to `instagram`.

No code edits needed — `main.py` already branches on `PUBLISH_MODE`.

### Meta / Instagram Graph API setup (do this when you're ready)

### 1. Convert Instagram to a Professional account
Instagram app → Settings → Account type → switch to **Business** or **Creator**, and link
it to a **Facebook Page** you control (create a free one if you don't have one — it can be
private/unpublished).

### 2. Create a Meta developer app
1. Go to [developers.facebook.com](https://developers.facebook.com) → **My Apps** → **Create App** → type **Business**.
2. Add the **Instagram Graph API** product to the app.

### 3. Add yourself as an Instagram Tester (skips the multi-week App Review)
Since you're only posting to *your own* account, you don't need full Meta App Review —
that's only required to publish on behalf of other people's accounts.
1. In the app dashboard → **App roles** → **Roles**, add your Facebook account as an Admin.
2. Under **Instagram** product settings, add your Instagram account as a **Tester**.
3. Open the Instagram app → Settings → **Apps and websites** → **Tester invites** → accept it.
The app stays in Development Mode, which is fine — Development Mode already allows testers
(you) to use every permission.

### 4. Generate a long-lived access token
1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer), select your app.
2. Request a User Access Token with these permissions: `instagram_business_basic`,
   `instagram_business_content_publish`, `pages_show_list`, `pages_read_engagement`.
3. Exchange it for a **long-lived token** (~60 days):
   ```
   GET https://graph.facebook.com/v21.0/oauth/access_token
       ?grant_type=fb_exchange_token
       &client_id={app-id}
       &client_secret={app-secret}
       &fb_exchange_token={short-lived-token}
   ```

### 5. Get your Instagram Business Account ID
```
GET https://graph.facebook.com/v21.0/me/accounts?access_token={token}
```
Find your Page in the results, copy its `id`, then:
```
GET https://graph.facebook.com/v21.0/{page-id}?fields=instagram_business_account&access_token={token}
```
That `instagram_business_account.id` is your `IG_USER_ID`.

Once you have `IG_ACCESS_TOKEN` + `IG_USER_ID`, jump back up to "Switching to instagram
mode later" — that's the whole remaining step.

## Notes & gotchas

- **Drive OAuth publishing status:** must be "In production" (see setup step 3) or your
  refresh token expires every 7 days and the daily run starts failing silently until you
  notice and re-run `authorize_drive.py`.
- **Rate limit (instagram mode):** Instagram allows up to 100 published posts per rolling
  24-hour window — a daily post is nowhere close to that.
- **Token expiry (instagram mode):** long-lived tokens expire every ~60 days. Set yourself
  a recurring reminder to regenerate it via Graph API Explorer and update the
  `IG_ACCESS_TOKEN` secret.
- **Groq model:** `llama-3.3-70b-versatile` (used in your Ask My Paper stack) was announced
  for deprecation by Groq in June 2026. This project defaults to `openai/gpt-oss-120b`,
  Groq's recommended replacement — swap `GROQ_MODEL` if you'd rather use something else.
- **API version drift (instagram mode):** Meta ships a new Graph API version every quarter.
  If calls start failing, check `GRAPH_API_VERSION` in `.env` / repo variables against
  [developers.facebook.com/docs/graph-api/changelog](https://developers.facebook.com/docs/graph-api/changelog).

## Customizing

- **Topics** — edit the `TOPICS` list in `topics.py`.
- **Look & feel** — colors/fonts/layout live in `image_generator.py` (`BG`, `ACCENT`,
  `ACCENT_2`); swap the `.ttf` files in `assets/fonts/` for a different typeface.
- **Voice/tone** — edit `SYSTEM_PROMPT` in `content_generator.py`.
- **Posting time/frequency** — edit the `cron` schedule in the workflow file.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `invalid_grant` from Google token refresh | Refresh token expired (7-day cap) — check OAuth consent screen is "In production", then re-run `authorize_drive.py` |
| `RuntimeError: Missing required environment variable: GOOGLE_...` | `PUBLISH_MODE=drive` but Google secrets aren't set (locally: `.env`; Actions: repo secrets) |
| `Graph API error 190` (instagram mode) | Access token expired — regenerate |
| `Graph API error 100, code 33` (instagram mode) | Wrong `IG_USER_ID`, or account isn't a Business/Creator account |
| Image container fails / IG can't fetch image (instagram mode) | GitHub CDN propagation delay — the code already waits a few seconds, but you can increase the `time.sleep()` in `github_host.py` |
| `json.decoder.JSONDecodeError` from content_generator | Rare model hiccup — `generate_with_retry` already retries once; increase `attempts` if it persists |
