"""ClipReward core logic — campaigns, submissions, earnings. SQLite via stdlib."""
import os
import sqlite3
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clipreward.db")


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                rate_per_1k REAL NOT NULL,
                min_views INTEGER NOT NULL DEFAULT 1000,
                cap_per_clip INTEGER NOT NULL DEFAULT 0,
                budget REAL NOT NULL DEFAULT 0,
                rules TEXT DEFAULT '',
                materials_url TEXT DEFAULT '',
                status TEXT DEFAULT 'live',
                created_at REAL
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                clipper_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                post_url TEXT NOT NULL,
                reported_views INTEGER NOT NULL DEFAULT 0,
                verified_views INTEGER NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                earnings REAL DEFAULT 0,
                submitted_at REAL,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
            )""")


# ---------------------------------------------------------------- campaigns --
def create_campaign(name, brand_name, rate_per_1k, min_views, cap_per_clip,
                    budget, rules="", materials_url=""):
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO campaigns
               (name, brand_name, rate_per_1k, min_views, cap_per_clip, budget,
                rules, materials_url, status, created_at)
               VALUES (?,?,?,?,?,?,?,?, 'live', ?)""",
            (name, brand_name, float(rate_per_1k), int(min_views),
             int(cap_per_clip), float(budget), rules, materials_url,
             time.time()))
        return cur.lastrowid


def list_campaigns(status=None):
    with _db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM campaigns WHERE status=? ORDER BY id DESC",
                (status,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM campaigns ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def get_campaign(campaign_id):
    with _db() as conn:
        row = conn.execute("SELECT * FROM campaigns WHERE id=?",
                           (campaign_id,)).fetchone()
    return dict(row) if row else None


def set_campaign_status(campaign_id, status):
    with _db() as conn:
        conn.execute("UPDATE campaigns SET status=? WHERE id=?",
                     (status, campaign_id))


# --------------------------------------------------------------- submissions --
def submit_clip(campaign_id, clipper_name, platform, post_url, reported_views):
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO submissions
               (campaign_id, clipper_name, platform, post_url, reported_views,
                verified_views, status, earnings, submitted_at)
               VALUES (?, ?, ?, ?, ?, 0, 'pending', 0, ?)""",
            (campaign_id, clipper_name, platform, post_url,
             int(reported_views), time.time()))
        return cur.lastrowid


def list_submissions(campaign_id=None, status=None):
    with _db() as conn:
        q = "SELECT * FROM submissions"
        clauses, params = [], []
        if campaign_id:
            clauses.append("campaign_id=?")
            params.append(campaign_id)
        if status:
            clauses.append("status=?")
            params.append(status)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY id DESC"
        rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def calc_earnings(campaign, verified_views):
    """views/1000 x rate, floored at min_views, capped at cap_per_clip."""
    if verified_views < campaign["min_views"]:
        return 0.0
    views = verified_views
    if campaign["cap_per_clip"] and views > campaign["cap_per_clip"]:
        views = campaign["cap_per_clip"]
    return round(views / 1000.0 * campaign["rate_per_1k"], 2)


def review_submission(submission_id, verified_views, approve=True):
    with _db() as conn:
        sub = conn.execute("SELECT * FROM submissions WHERE id=?",
                           (submission_id,)).fetchone()
        if not sub:
            raise ValueError("Submission not found")
        campaign = get_campaign(sub["campaign_id"])
        earnings = calc_earnings(campaign, int(verified_views)) if approve else 0.0
        status = "approved" if approve else "rejected"
        conn.execute(
            """UPDATE submissions SET verified_views=?, status=?, earnings=?
               WHERE id=?""",
            (int(verified_views), status, earnings, submission_id))
        return earnings


# ------------------------------------------------------------------- stats ---
def campaign_stats(campaign_id):
    subs = list_submissions(campaign_id=campaign_id)
    approved = [s for s in subs if s["status"] == "approved"]
    pending = [s for s in subs if s["status"] == "pending"]
    total_views = sum(s["verified_views"] for s in approved)
    spent = round(sum(s["earnings"] for s in approved), 2)
    campaign = get_campaign(campaign_id)
    remaining = (round(campaign["budget"] - spent, 2)
                 if campaign and campaign["budget"] else None)
    return {"submissions": len(subs), "approved": len(approved),
            "pending": len(pending), "total_views": total_views,
            "spent": spent, "remaining": remaining}


def leaderboard():
    with _db() as conn:
        rows = conn.execute("""
            SELECT clipper_name,
                   COUNT(*) AS clips,
                   SUM(verified_views) AS views,
                   SUM(earnings) AS earnings
            FROM submissions
            WHERE status='approved'
            GROUP BY clipper_name
            ORDER BY earnings DESC
            LIMIT 20""").fetchall()
    return [dict(r) for r in rows]


def load_demo_data():
    """Clearly-labelled sample content so the app never looks empty."""
    c1 = create_campaign(
        "Demo: TechGadget Launch Clips", "DemoBrand", rate_per_1k=1.0,
        min_views=2000, cap_per_clip=1000000, budget=500,
        rules=("1. Clip must be from the source video linked below.\n"
               "2. Minimum 8 seconds long.\n"
               "3. No botted views — organic only.\n"
               "4. Mention the brand name in the caption."),
        materials_url="https://example.com/source-video")
    submit_clip(c1, "demo_clipper_1", "TikTok",
                "https://tiktok.com/@demo/video/1", 12500)
    submit_clip(c1, "demo_clipper_2", "YouTube Shorts",
                "https://youtube.com/shorts/demo2", 8300)
    review_submission(1, 12000, approve=True)
    review_submission(2, 8000, approve=True)
    c2 = create_campaign(
        "Demo: Fitness App Promo", "FitBrand", rate_per_1k=2.0,
        min_views=1000, cap_per_clip=500000, budget=300,
        rules="1. Use the provided clips only.\n2. Add #fitbrand in the caption.",
        materials_url="https://example.com/fit-video")
    submit_clip(c2, "demo_clipper_1", "Instagram Reels",
                "https://instagram.com/reel/demo3", 4200)
    return [c1, c2]
