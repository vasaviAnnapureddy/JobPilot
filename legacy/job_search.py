# -*- coding: utf-8 -*-
"""
===========================================================
VASAVI'S JOB SEARCH AUTOMATION  — MODULE 1
===========================================================
Portals covered:
  - LinkedIn     (via JobSpy — WITH login for full JDs)
  - Indeed India (via JobSpy)
  - Glassdoor    (via JobSpy — salary + reviews)
  - Naukri.com   (via Naukri public API)
  - Internshala  (via public API — best fresher portal)

OUTPUT:
  E:/DataSciiecne/JobAutomation/vasavi_jobs.xlsx
  Sheets:
    [1] Apply Today   — best matches, apply these first
    [2] Good Matches  — strong but not perfect
    [3] All Jobs      — full tracker with status column
    [4] Summary       — stats of this search run

HOW TO RUN:
  python vasavi_job_search.py
===========================================================
"""

import sys, os, time, json, warnings
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
warnings.filterwarnings("ignore")

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from jobspy import scrape_jobs

# Load credentials
load_dotenv(Path(__file__).parent / ".env")
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
LINKEDIN_LOGIN_OK = bool(LINKEDIN_EMAIL and LINKEDIN_PASSWORD
                         and "YOUR_LINKEDIN_PASSWORD_HERE" not in LINKEDIN_PASSWORD)

# ─────────────────────────────────────────────────────────
# VASAVI'S PROFILE
# ─────────────────────────────────────────────────────────
PROFILE = {
    "name": "Vasavi Annapureddy",
    "skills": [
        "python", "sql", "machine learning", "xgboost", "lightgbm",
        "scikit-learn", "random forest", "deep learning", "tensorflow",
        "pytorch", "pandas", "numpy", "nlp", "natural language processing",
        "sentiment analysis", "vader", "nltk", "hugging face", "transformers",
        "llm", "large language model", "generative ai", "genai", "gemini",
        "gpt", "llama", "prompt engineering", "rag", "langchain",
        "streamlit", "flask", "django", "tableau", "power bi",
        "data visualization", "shap", "optuna", "feature engineering",
        "ensemble", "stacking", "regression", "classification",
        "computer vision", "git", "github", "data science", "ai", "ml",
        "artificial intelligence", "opencv", "kotlin", "android",
        "api", "rest", "json", "html", "css", "javascript",
        "agile", "scrum", "jupyter", "colab", "matplotlib", "seaborn",
    ],
    "target_roles": [
        "data scientist", "machine learning engineer", "ml engineer",
        "ai engineer", "data analyst", "nlp engineer", "genai engineer",
        "generative ai engineer", "llm engineer", "junior data scientist",
        "associate data scientist", "research analyst", "ai analyst",
        "data science intern", "ml intern", "ai intern",
        "software engineer", "python developer",
    ]
}

ANTI_KEYWORDS = [
    # Experience thresholds — Vasavi is a fresher (0 years)
    "2+ years", "3+ years", "4+ years", "5+ years",
    "6+ years", "7+ years", "8+ years", "10+ years",
    "2 years experience", "3 years experience", "4 years experience",
    "minimum 2 years", "minimum 3 years", "minimum 4 years", "minimum 5 years",
    "2+ years experience", "3+ years experience", "4+ years experience",
    "at least 2 years", "at least 3 years",
    "2-3 years", "3-5 years", "4-6 years", "5-7 years",
    # Seniority titles
    "senior", "lead", "principal", "manager", "director", "head of",
    "staff engineer", "vp of", "vice president", "architect",
]

FRESHER_BOOST = [
    "fresher", "0-1", "0 to 1", "entry level", "entry-level",
    "junior", "associate", "trainee", "graduate", "new grad",
    "2024 batch", "2025 batch", "2026 batch", "0-2 years", "no experience",
    "recent graduate", "campus hire", "off-campus",
]

OUTPUT_PATH = "E:/DataSciiecne/JobAutomation/vasavi_jobs.xlsx"

# ─────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────
def score_job(title, description, location, company):
    score = 0
    text = f"{title} {description} {company}".lower()

    # Skill matches
    for skill in PROFILE["skills"]:
        if skill in text:
            score += 2

    # Role title match
    for role in PROFILE["target_roles"]:
        if role in title.lower():
            score += 20
            break

    # Fresher-friendly bonus
    for kw in FRESHER_BOOST:
        if kw in text:
            score += 15
            break

    # Senior/experienced penalty
    for anti in ANTI_KEYWORDS:
        if anti in text:
            score -= 50
            break

    # Bangalore/remote bonus
    loc = location.lower() if location else ""
    if "bangalore" in loc or "bengaluru" in loc:
        score += 10
    elif "remote" in loc or "work from home" in loc or "wfh" in loc:
        score += 8
    elif "hyderabad" in loc or "chennai" in loc or "pune" in loc:
        score += 5

    return max(0, min(score, 100))


def match_label(score):
    if score >= 65:   return "Apply Today"
    elif score >= 40: return "Good Match"
    elif score >= 20: return "Maybe"
    else:             return "Skip"


# ─────────────────────────────────────────────────────────
# MODULE A — LinkedIn + Indeed + Glassdoor via JobSpy
# ─────────────────────────────────────────────────────────
JOBSPY_SEARCHES = [
    ("data scientist fresher",               "Bangalore, India"),
    ("machine learning engineer entry level","Bangalore, India"),
    ("generative AI engineer junior",        "Bangalore, India"),
    ("LLM engineer python fresher",          "India"),
    ("data analyst fresher python sql",      "Bangalore, India"),
    ("NLP engineer junior",                  "India"),
    ("AI engineer 0 years experience",       "Bangalore, India"),
    ("junior data scientist remote",         "India"),
    ("python developer fresher",             "Bangalore, India"),
    ("data science associate",               "Bangalore, India"),
    ("deep learning engineer fresher",       "India"),
    ("AI ML fresher 2025",                   "Bangalore, India"),
]

def fetch_jobspy_jobs():
    login_msg = "WITH LinkedIn login (full JDs)" if LINKEDIN_LOGIN_OK else "PUBLIC only (add LinkedIn password for full JDs)"
    print(f"\n[LinkedIn + Indeed] Searching... {login_msg}")

    all_dfs = []

    # Glassdoor doesn't support Indian city locations reliably — use linkedin + indeed
    sites = ["linkedin", "indeed"]

    # Suppress JobSpy internal error logs (Glassdoor 400s etc.) — we handle errors ourselves
    import logging
    logging.getLogger("JobSpy").setLevel(logging.CRITICAL)
    logging.getLogger("jobspy").setLevel(logging.CRITICAL)

    for i, (query, location) in enumerate(JOBSPY_SEARCHES, 1):
        print(f"  [{i}/{len(JOBSPY_SEARCHES)}] {query} — {location}")
        try:
            kwargs = dict(
                site_name       = sites,
                search_term     = query,
                location        = location,
                results_wanted  = 15,
                hours_old       = 72,
                country_indeed  = "India",
            )
            # Add LinkedIn login if credentials are set — gives full JDs
            if LINKEDIN_LOGIN_OK:
                kwargs["linkedin_fetch_description"] = True
                kwargs["linkedin_username"]          = LINKEDIN_EMAIL
                kwargs["linkedin_password"]          = LINKEDIN_PASSWORD

            df = scrape_jobs(**kwargs)
            if df is not None and len(df) > 0:
                df["source_query"] = query
                all_dfs.append(df)
                print(f"     Found {len(df)} jobs")
            else:
                print(f"     No results")
        except Exception as e:
            err = str(e)
            if "CHALLENGE" in err.upper() or "captcha" in err.lower():
                print(f"     LinkedIn challenge detected — retrying without login")
                try:
                    kwargs.pop("linkedin_fetch_description", None)
                    kwargs.pop("linkedin_username", None)
                    kwargs.pop("linkedin_password", None)
                    df = scrape_jobs(**kwargs)
                    if df is not None and len(df) > 0:
                        df["source_query"] = query
                        all_dfs.append(df)
                        print(f"     Retry OK: {len(df)} jobs")
                except Exception as e2:
                    print(f"     Retry also failed: {str(e2)[:80]}")
            else:
                print(f"     Error: {err[:100]}")
        time.sleep(2)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["title", "company"], keep="first")

    # Standardise columns
    rows = []
    for _, r in combined.iterrows():
        title    = str(r.get("title", ""))
        company  = str(r.get("company", ""))
        location = str(r.get("location", ""))
        desc     = str(r.get("description", ""))
        url      = str(r.get("job_url", ""))
        posted   = str(r.get("date_posted", ""))
        portal   = str(r.get("site", ""))
        salary   = str(r.get("min_amount", "")) or str(r.get("salary", ""))

        sc = score_job(title, desc, location, company)
        rows.append({
            "Portal":          portal.title() if portal else "LinkedIn/Indeed",
            "Job Title":       title,
            "Company":         company,
            "Location":        location,
            "Salary":          salary if salary not in ("", "None", "nan") else "",
            "Score":           sc,
            "Match":           match_label(sc),
            "Date Posted":     posted,
            "Apply Link":      url,
            "Job Description": desc[:3000] + "..." if len(desc) > 3000 else desc,
            "Status":          "Not Applied",
            "Notes":           "",
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────
# MODULE B — Naukri via Playwright response interception
#
# Naukri blocks direct API calls with reCAPTCHA.
# BUT when the actual Naukri page loads, it makes the same
# API call internally with proper tokens.
# We intercept that response — reCAPTCHA never fires.
# ─────────────────────────────────────────────────────────

# Each tuple: (page_url_slug, fallback_location_label)
# Naukri URL format: /{keyword}-jobs-in-{location}?experience=0
NAUKRI_SEARCHES = [
    ("data-scientist-fresher",           "bangalore"),
    ("machine-learning-engineer",        "bangalore"),
    ("generative-ai-engineer",           "bangalore"),
    ("python-data-scientist",            "bangalore"),
    ("nlp-engineer-fresher",             "india"),
    ("data-analyst-fresher",             "bangalore"),
    ("junior-data-scientist",            "india"),
    ("ai-ml-engineer-fresher",           "bangalore"),
    ("deep-learning-engineer-fresher",   "india"),
    ("python-developer-fresher",         "bangalore"),
]


def _parse_naukri_jobs(api_data, fallback_loc):
    """Parse job listings from Naukri API v3 response."""
    rows = []
    jobs = api_data.get("jobDetails", [])
    for job in jobs:
        title    = job.get("title", "")
        company  = job.get("companyName", "")
        loc_list = job.get("placeholders", [])
        loc      = next((p.get("label", "") for p in loc_list
                         if p.get("type", "") == "location"), fallback_loc)
        exp_tags = job.get("tagsAndSkills", "")
        desc     = (job.get("jobDescription", "")
                    or job.get("snippets", {}).get("shortJobDescription", ""))
        job_id   = job.get("jobId", "")
        apply_url = (f"https://www.naukri.com/job-listings-{job_id}"
                     if job_id else "https://www.naukri.com")
        posted   = job.get("footerPlaceholderLabel", "")
        salary   = next((p.get("label", "") for p in loc_list
                         if p.get("type", "") == "salary"), "")

        sc = score_job(title, str(desc) + " " + str(exp_tags), loc, company)
        rows.append({
            "Portal":          "Naukri",
            "Job Title":       title,
            "Company":         company,
            "Location":        loc,
            "Salary":          salary,
            "Score":           sc,
            "Match":           match_label(sc),
            "Date Posted":     posted,
            "Apply Link":      apply_url,
            "Job Description": (str(desc)[:3000] + "..."
                                if len(str(desc)) > 3000 else str(desc)),
            "Status":          "Not Applied",
            "Notes":           "",
        })
    return rows


def fetch_naukri_jobs():
    """
    Navigate to Naukri search pages and intercept their own internal API
    responses.  No direct API call needed — we just listen to what the
    browser receives, so reCAPTCHA never triggers.
    """
    print("\n[Naukri.com] Searching via browser interception...")
    rows = []

    try:
        import asyncio as _asyncio
        import json as _json
        from playwright.async_api import async_playwright

        COOKIES_F = Path(__file__).parent / "data" / "naukri_session.json"
        if not COOKIES_F.exists():
            print("  No saved Naukri session. Run: python naukri_updater.py --setup")
            return pd.DataFrame()

        async def _scrape():
            all_rows = []
            async with async_playwright() as pw:
                try:
                    browser = await pw.chromium.launch(
                        channel="msedge", headless=True,
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                except Exception:
                    browser = await pw.chromium.launch(headless=True)

                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                )
                cookies = _json.loads(COOKIES_F.read_text(encoding="utf-8"))
                await context.add_cookies(cookies)

                page = await context.new_page()

                for i, (slug, loc_label) in enumerate(NAUKRI_SEARCHES, 1):
                    print(f"  [{i}/{len(NAUKRI_SEARCHES)}] {slug} — {loc_label}")
                    captured_jobs = []

                    async def handle_response(response,
                                              _loc=loc_label,
                                              _cap=captured_jobs):
                        is_v3 = ("jobapi/v3/search" in response.url
                                 and "recom" not in response.url)
                        is_v2_jobs = ("jobapi/v2/search" in response.url
                                      and "recom-jobs" not in response.url)
                        if (is_v3 or is_v2_jobs) and response.status == 200:
                            try:
                                body = await response.json()
                                jobs = body.get("jobDetails", [])
                                if jobs:
                                    _cap.extend(jobs)
                            except Exception:
                                pass

                    page.on("response", handle_response)

                    try:
                        if loc_label == "india":
                            naukri_url = (
                                f"https://www.naukri.com/{slug}-jobs"
                                f"?experience=0&jobAge=7"
                            )
                        else:
                            naukri_url = (
                                f"https://www.naukri.com/{slug}-jobs-in-{loc_label}"
                                f"?experience=0&jobAge=7"
                            )

                        await page.goto(naukri_url, timeout=25_000,
                                        wait_until="domcontentloaded")
                        # Wait for async API calls to complete
                        await _asyncio.sleep(7)

                        print(f"     Intercepted {len(captured_jobs)} jobs")
                        for job in captured_jobs:
                            all_rows.extend(
                                _parse_naukri_jobs({"jobDetails": [job]}, loc_label)
                            )

                    except Exception as e:
                        print(f"     Error: {str(e)[:80]}")

                    # Remove handler before next page
                    page.remove_listener("response", handle_response)
                    await _asyncio.sleep(1)

                await browser.close()
            return all_rows

        rows = _asyncio.run(_scrape())

    except ImportError:
        print("  Playwright not installed — skipping Naukri")
    except Exception as e:
        print(f"  Naukri scraper error: {str(e)[:120]}")

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["Job Title", "Company"], keep="first")
    return df


# ─────────────────────────────────────────────────────────
# MODULE C — Internshala (best fresher portal in India)
# ─────────────────────────────────────────────────────────
INTERNSHALA_SEARCHES = [
    "data-science",
    "machine-learning",
    "artificial-intelligence",
    "python",
    "data-analyst",
    "nlp",
    "deep-learning",
]

INTERNSHALA_HEADERS = {
    "User-Agent":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept":      "application/json, text/plain, */*",
    "Referer":     "https://internshala.com/jobs/",
    "x-requested-with": "XMLHttpRequest",
}

def fetch_internshala_jobs():
    print("\n[Internshala] Searching...")
    rows = []

    for i, category in enumerate(INTERNSHALA_SEARCHES, 1):
        print(f"  [{i}/{len(INTERNSHALA_SEARCHES)}] {category}")
        try:
            url = f"https://internshala.com/jobs/{category}-jobs"
            resp = requests.get(url, headers=INTERNSHALA_HEADERS, timeout=15)

            if resp.status_code != 200:
                print(f"     HTTP {resp.status_code} — skipping")
                time.sleep(2)
                continue

            # Parse HTML to extract jobs — Internshala is HTML-rendered
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            # Job cards
            cards = soup.select(".individual_internship")
            if not cards:
                # Try alternate selector
                cards = soup.select("[id^='job_']")

            if not cards:
                print(f"     No job cards found (may need JavaScript) — skipping")
                time.sleep(2)
                continue

            found = 0
            for card in cards[:15]:
                try:
                    title_el   = card.select_one(".profile") or card.select_one("h3")
                    company_el = card.select_one(".company_name") or card.select_one(".company-name")
                    loc_el     = card.select_one(".location_link") or card.select_one(".locations span")
                    link_el    = card.select_one("a[href*='/jobs/']") or card.select_one("a")

                    title   = title_el.get_text(strip=True) if title_el else category.replace("-", " ").title()
                    company = company_el.get_text(strip=True) if company_el else ""
                    loc     = loc_el.get_text(strip=True) if loc_el else "India"
                    href    = link_el.get("href", "") if link_el else ""
                    link    = f"https://internshala.com{href}" if href.startswith("/") else href

                    if not title or not company:
                        continue

                    sc = score_job(title, category, loc, company)
                    rows.append({
                        "Portal":          "Internshala",
                        "Job Title":       title,
                        "Company":         company,
                        "Location":        loc,
                        "Salary":          "",
                        "Score":           sc,
                        "Match":           match_label(sc),
                        "Date Posted":     "",
                        "Apply Link":      link,
                        "Job Description": f"{category.replace('-', ' ').title()} role at {company}",
                        "Status":          "Not Applied",
                        "Notes":           "",
                    })
                    found += 1
                except Exception:
                    continue

            print(f"     Found {found} jobs")

        except ImportError:
            print("     beautifulsoup4 not installed — run: pip install beautifulsoup4")
            break
        except Exception as e:
            print(f"     Error: {str(e)[:80]}")

        time.sleep(2)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["Job Title", "Company"], keep="first")
    return df


# ─────────────────────────────────────────────────────────
# WRITE EXCEL
# ─────────────────────────────────────────────────────────
def write_excel(df):
    if df.empty:
        print("\nNo jobs found to save.")
        return

    df = df.sort_values("Score", ascending=False).reset_index(drop=True)

    apply_today = df[df["Match"] == "Apply Today"]
    good        = df[df["Match"] == "Good Match"]
    maybe       = df[df["Match"] == "Maybe"]

    # Portal breakdown
    portal_counts = df.groupby("Portal").size().reset_index(name="Count")
    portal_str = " | ".join(f"{r['Portal']}: {r['Count']}" for _, r in portal_counts.iterrows())

    summary = pd.DataFrame({
        "Metric": [
            "Run Date & Time",
            "Total Jobs Found",
            "Apply Today (Best Matches)",
            "Good Matches",
            "Maybe",
            "LinkedIn Login",
            "Portals Searched",
            "Jobs by Portal",
            "Your Name",
            "Next Step",
        ],
        "Value": [
            datetime.now().strftime("%d %b %Y  %H:%M"),
            len(df),
            len(apply_today),
            len(good),
            len(maybe),
            "YES (full JDs)" if LINKEDIN_LOGIN_OK else "NO (add password to .env for full JDs)",
            "LinkedIn, Indeed, Naukri, Internshala",
            portal_str,
            "Vasavi Annapureddy",
            "Open 'Apply Today' sheet — start from row 1 and apply",
        ]
    })

    print(f"\nSaving to Excel: {OUTPUT_PATH}")

    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        if not apply_today.empty:
            apply_today.to_excel(writer, sheet_name="Apply Today", index=False)
        if not good.empty:
            good.to_excel(writer, sheet_name="Good Matches", index=False)
        if not maybe.empty:
            maybe.to_excel(writer, sheet_name="Maybe", index=False)
        df.to_excel(writer, sheet_name="All Jobs Tracker", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)

        # Auto-widen columns in each sheet
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max(
                    (len(str(cell.value)) for cell in col if cell.value), default=10
                )
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    print(f"Saved OK: {OUTPUT_PATH}")


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  VASAVI JOB SEARCH — LinkedIn + Indeed + Naukri + Internshala")
    print("  Profile: AI & ML Engineer | Fresher | Bangalore")
    if LINKEDIN_LOGIN_OK:
        print("  LinkedIn: LOGGED IN (full JDs enabled)")
    else:
        print("  LinkedIn: PUBLIC MODE (add password to .env for full JDs)")
    print("=" * 60)

    frames = []

    # LinkedIn + Indeed + Glassdoor
    df_jobspy = fetch_jobspy_jobs()
    if not df_jobspy.empty:
        frames.append(df_jobspy)
        print(f"\nLinkedIn + Indeed + Glassdoor: {len(df_jobspy)} unique jobs found")

    # Naukri
    df_naukri = fetch_naukri_jobs()
    if not df_naukri.empty:
        frames.append(df_naukri)
        print(f"Naukri: {len(df_naukri)} unique jobs found")

    # Internshala
    df_internshala = fetch_internshala_jobs()
    if not df_internshala.empty:
        frames.append(df_internshala)
        print(f"Internshala: {len(df_internshala)} unique jobs found")

    if not frames:
        print("\nNo jobs found from any portal. Check internet and try again.")
        return

    all_jobs = pd.concat(frames, ignore_index=True)
    all_jobs = all_jobs.drop_duplicates(subset=["Job Title", "Company"], keep="first")
    all_jobs = all_jobs.sort_values("Score", ascending=False).reset_index(drop=True)

    write_excel(all_jobs)

    # Print summary
    apply_today = all_jobs[all_jobs["Match"] == "Apply Today"]
    good        = all_jobs[all_jobs["Match"] == "Good Match"]

    print("\n" + "=" * 60)
    print("  DONE!")
    print("=" * 60)
    print(f"  Total jobs found  : {len(all_jobs)}")
    print(f"  Apply Today       : {len(apply_today)}")
    print(f"  Good Matches      : {len(good)}")
    print(f"\n  File saved at:")
    print(f"  {OUTPUT_PATH}")
    print(f"\n  NEXT STEP:")
    print(f"  Open vasavi_jobs.xlsx")
    print(f"  Go to the 'Apply Today' sheet")
    print(f"  Start applying from row 1 down")
    print("=" * 60)

    # Show top 5 jobs in terminal
    if not apply_today.empty:
        print(f"\n  TOP {min(5, len(apply_today))} JOBS FOR YOU RIGHT NOW:")
        print("-" * 60)
        for i, row in apply_today.head(5).iterrows():
            print(f"  {i+1}. {row['Job Title']}")
            print(f"     Company  : {row['Company']}")
            print(f"     Location : {row['Location']}")
            print(f"     Portal   : {row['Portal']}")
            print(f"     Score    : {row['Score']}/100")
            if row.get("Salary"):
                print(f"     Salary   : {row['Salary']}")
            print(f"     Link     : {row['Apply Link']}")
            print()


if __name__ == "__main__":
    main()
