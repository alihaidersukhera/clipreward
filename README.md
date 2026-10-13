# 💰 ClipReward — pay-per-view clipping campaigns

By **JONNY PRODUCTIONS**. A Whop-Content-Rewards-style demo: brands post
clipping campaigns with a rate per 1,000 views, clippers submit their posted
clip links, brands verify the views, and earnings are calculated automatically.

## How it works
1. **Brand** creates a campaign: name, rate per 1,000 views, minimum views,
   cap per clip, budget, rules, source-material link.
2. **Clipper** browses live campaigns, posts a clip on TikTok / Shorts / Reels,
   then submits the link with its current views.
3. **Brand** opens each link, enters the verified view count, and approves —
   earnings = verified views ÷ 1,000 × rate (floored at min views, capped).
4. **Leaderboard** ranks clippers by earnings.

## Run locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Notes
- Demo build: data lives in a local SQLite file (`clipreward.db`); views are
  verified by brands manually. A production version would use social-platform
  APIs for automatic view checks and a real payment provider for payouts.
