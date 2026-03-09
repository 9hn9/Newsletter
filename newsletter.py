"""
AI newsletter generator optimized for any free tier API provider with integrated task scheduling.

Constraints:
- 30 requests per minute (RPM)
- 1,000 requests per day (RPD)
- 8,000 tokens per minute (TPM)
- 200,000 tokens per day (TPD)

Strategy:
- Aggressive keyword pre-filtering (no LLM needed)
- Single-pass categorization + scoring
- Batch summaries efficiently
- Minimize total LLM calls to <15 per run
- Optional: Automated scheduling, per-article archival, mass e-mailing
"""

import os # Read environment variables and work with system paths
import json  # Parse and generate JSON for LLM requests and responses
import re  # Clean and normalize text using Regular Expressions
import time
# import schedule  # Task scheduling library
from datetime import datetime, timedelta, timezone # Handle timestamps, lookback windows, and UTC times
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode  # Normalize and clean URLs for deduplication
import feedparser  # Parse RSS feeds into structured entries
from dotenv import load_dotenv # Load configuration values from a .env file into environment variables
import pandas as pd # Read the RSS feed configuration from an Excel file
from groq import Groq
# import requests  # Make HTTP requests to fetch web pages or article content/ LLM API (required to call Ollama API)
# from bs4 import BeautifulSoup  # Parse and manipulate HTML content (required for archival)
# import smtplib  # Connect to SMTP servers and send emails

load_dotenv()

# ================== CONFIG ==================

API_KEY = os.getenv("API_KEY")
# API_BASE = os.getenv("API_BASE", "https://ollama.com/v1") #OLLAMA
# LLM_API_URL = os.getenv("LLM_API_URL") #ON-PREM LLM
MODEL = os.getenv("MODEL")

# Output directories
NEWSLETTER_OUTPUT_DIR = "Outputs"
# ARTICLE_ARCHIVE_ROOT = "Archive"

DAYS_BACK = int(os.getenv("DAYS_BACK"))
ARTICLES_PER_CATEGORY = 3  # Top 3 per category = 15 total articles

# Excel feed configuration
FEEDS_EXCEL_PATH = os.getenv("FEEDS_EXCEL_PATH", "Feeds_list.xlsx")
FEEDS_SHEET_NAME = os.getenv("FEEDS_SHEET_NAME", "Sheet1")

# Rate limiting
REQUEST_DELAY = 2.1  # 2.1 seconds = ~28 requests/min (safe margin)
daily_request_count = 0
MAX_DAILY_REQUESTS = 1000  # Leave buffer

# # ================== SCHEDULER CONFIGURATION ==================
# SCHEDULE_ENABLED = os.getenv("SCHEDULE_ENABLED", "false").lower() == "true"
# SCHEDULE_DAY = os.getenv("SCHEDULE_DAY", "Friday")  # monday, tuesday, etc. or "daily"
# SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "10:00")  # HH:MM format
# SCHEDULE_TIMEZONE = os.getenv("SCHEDULE_TIMEZONE", "IST")

# Categories with keywords for pre-filtering
CATEGORIES = {
    "Model Releases": [
        # Core generic terms
        "model", "ai model", "foundation model", "frontier model",
        "large language model", "llm", "vision-language model",
        "multimodal model", "checkpoint", "weights",
        "release", "launched", "launch", "rolled out",
        "new version", "v2", "v3", "v4", "v5", "update", "preview",
        "general availability", "ga", "beta release", "early access",
        # OpenAI
        "gpt", "chatgpt", "gpt-4", "gpt-4.1", "gpt-5", "o1",
        "openai", "chatgpt enterprise",
        # Anthropic
        "claude", "claude 3", "claude 3.5", "claude 4", "anthropic",
        # Google / Alphabet
        "gemini", "gemini 1.5", "gemini ultra", "gemini pro",
        "google ai", "google deepmind", "deepmind",
        # Meta
        "llama", "llama 3", "llama 3.1", "llama-2", "llama-3.1",
        "meta ai",
        # Mistral, Cohere, etc.
        "mistral", "mixtral", "mistral large", "mistral small",
        "cohere", "command-r", "command-r+", "command model",
        "stability", "stable diffusion", "sd 3", "sdxl",
        "hugging face", "hf model", "falcon", "phi-3", "phi-4",
        # Deployment / serving
        "model card", "model zoo", "model hub", "weights release",
        "inference api", "model serving", "open weights", "open-source model"
    ],
    "Physical AI Advances": [
        "robot", "robots", "robotic", "robotics",
        "humanoid", "android",
        "autonomous", "self-driving", "self driving",
        "driverless", "autopilot", "full self-driving", "fsd",
        "drone", "uav", "quadrotor",
        "embodied", "embodied ai", "embodied agent",
        "manipulator", "robot arm", "cobot", "cobots",
        "warehouse automation", "logistics robot",
        "delivery robot", "last-mile robot",
        "manufacturing", "factory automation", "industrial robot",
        "service robot", "social robot",
        # Flagship projects / companies
        "tesla bot", "optimus", "figure ai", "figure 01",
        "boston dynamics", "atlas robot", "spot robot",
        "agility robotics", "digit robot",
        # Mobility & physical platforms
        "autonomous vehicle", "robotaxi", "av fleet",
        "autonomous truck", "autonomous drone",
        "surgical robot", "medical robot",
        # General phrasing
        "physical ai", "embodied intelligence", "real-world robot",
        "robot learning", "sim-to-real", "sim2real"
    ],
    "Research": [
        "paper", "preprint", "manuscript", "journal article",
        "research", "study", "experiment", "experiments",
        "benchmark", "leaderboard", "sota", "state-of-the-art",
        "dataset", "corpus", "data set",
        "arxiv", "openreview", "iclr", "neurips", "icml", "iccv",
        "acl", "emnlp", "kdd", "ai",
        "algorithm", "training method", "optimization",
        "neural network", "deep network", "deep learning",
        "transformer", "attention mechanism",
        "mamba", "state space model", "ssm",
        "mixture of experts", "moe",
        "rl", "reinforcement learning", "rlhf",
        "rlaif", "alignment", "safety research",
        "interpretability", "mechanistic interpretability",
        "reasoning", "chain-of-thought", "cot",
        "multimodal", "multimodal model", "vision-language", "vision",
        "representation learning", "self-supervised",
        "ablation", "evaluation", "probe", "probing",
        "zero-shot", "few-shot", "fine-tuning", "finetuning",
        "distillation", "quantization", "pruning"
    ],
    "Funding and Business": [
        "funding", "investment", "invests in", "backed by",
        "raised", "raise", "secures funding",
        "seed round", "pre-seed", "series a", "series b",
        "series c", "series d", "growth round",
        "venture round", "bridge round",
        "valuation", "valued at", "post-money", "pre-money",
        "unicorn",
        "ipo", "public offering", "direct listing", "spac",
        "merger", "acquisition", "m&a", "acquires",
        "buyout", "takeover",
        "revenue", "arr", "mrr", "profit", "earnings",
        "run rate", "cash flow",
        "billion", "million", "bn", "mn" , "m usd", "m eur", "m dollar", "m dollars", "m gbp", "m yen",
        "fund", "vc", "venture capital", "private equity", "venture capital firm", 
        "investor", "angel", "seed investor",
        "startup", "scaleup", "ai startup", "ai company",
        "spin-out", "spinoff", "spin-off",
        "partnership deal", "commercial agreement",
        "licensing deal", "distribution agreement",
        "business model", "go-to-market", "gtm",
        "enterprise adoption", "customer wins", "contract signed"
    ],
    "Partnerships and Ethics": [
        # Partnerships / collaborations
        "partnership", "partners with", "strategic partnership",
        "collaboration", "collaborates with",
        "joint venture", "alliance", "mou",
        "co-develop", "co-develops", "co-founder agreement",
        # Ethics, safety, policy
        "ethics", "ethical ai", "ai ethics",
        "responsible ai", "trustworthy ai",
        "safety", "ai safety", "model safety",
        "alignment", "governance", "ai governance",
        "oversight", "audit", "auditing",
        "risk management", "risk framework",
        "regulation", "regulations", "regulatory",
        "policy", "policies", "guidelines",
        "standards body", "iso", "nist ai",
        "compliance", "mandatory rules",
        # Laws, rights, copyright, privacy
        "eu ai act", "ai act", "ai bill", "executive order on ai",
        "copyright", "training data disclosure",
        "data protection", "gdpr",
        "privacy", "data privacy", "surveillance",
        "transparency", "disclosure", "watermarking",
        "content provenance", "deepfake", "synthetic media",
        "lawsuit", "sues", "sued", "legal challenge",
        "class action", "injunction", "settlement",
        # Org / governance actors
        "regulator", "watchdog", "commission",
        "policy paper", "white paper", "consultation",
        "public comment", "code of conduct"
    ]
}

# ================== GROQ API CLIENT ==================

client = Groq(api_key=API_KEY)

def api_call(messages, temperature=0.1, max_tokens=2000):
    """Rate-limited API call with better error handling"""
    global daily_request_count
    
    if daily_request_count >= MAX_DAILY_REQUESTS:
        raise RuntimeError("Daily request limit reached")
    
    time.sleep(REQUEST_DELAY)  # Rate limiting
    
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        daily_request_count += 1
        response = completion.choices[0].message.content
        
        if not response or not response.strip():
            raise ValueError("Empty response from LLM")
        
        return response
        
    except Exception as e:
        print(f"  ! API error: {e}")
        raise

# # ================== SCHEDULER HELPER FUNCTIONS ==================

# def log_schedule_event(message: str):
#     """Log scheduler events with timestamp"""
#     timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
#     print(f"[SCHEDULER] {timestamp} - {message}")

# def schedule_daily(job_func, time_str: str):
#     """
#     Schedule a job to run daily at a specific time.
    
#     Args:
#         job_func: The function to schedule
#         time_str: Time in HH:MM format (e.g., "09:00")
#     """
#     parts = time_str.split(":")
#     if len(parts) != 2:
#         raise ValueError(f"Invalid time format '{time_str}'. Use HH:MM format.")
    
#     return schedule.every().day.at(time_str).do(job_func)

# def schedule_weekly(job_func, day: str, time_str: str):
#     """
#     Schedule a job to run weekly on a specific day and time.
    
#     Args:
#         job_func: The function to schedule
#         day: Day of week ('monday', 'tuesday', 'wednesday', etc.)
#         time_str: Time in HH:MM format (e.g., "09:00")
#     """
#     day_lower = day.lower()
#     valid_days = [
#         "monday", "tuesday", "wednesday", "thursday", 
#         "friday", "saturday", "sunday"
#     ]
    
#     if day_lower not in valid_days:
#         raise ValueError(f"Invalid day '{day}'. Must be one of {valid_days}")
    
#     # Map day names to schedule methods
#     day_methods = {
#         "Monday": lambda: schedule.every().monday,
#         "Tuesday": lambda: schedule.every().tuesday,
#         "Wednesday": lambda: schedule.every().wednesday,
#         "Thursday": lambda: schedule.every().thursday,
#         "Friday": lambda: schedule.every().friday,
#         "Saturday": lambda: schedule.every().saturday,
#         "Sunday": lambda: schedule.every().sunday,
#     }
    
#     return day_methods[day_lower]().at(time_str).do(job_func)

# def setup_scheduler():
#     """
#     Initialize the scheduler based on environment configuration.
    
#     Returns:
#         bool: True if scheduler is enabled and configured, False otherwise
#     """
#     if not SCHEDULE_ENABLED:
#         log_schedule_event("Scheduler is disabled (SCHEDULE_ENABLED=false)")
#         return False
    
#     try:
#         log_schedule_event("Setting up scheduler...")
        
#         # Determine schedule type
#         if SCHEDULE_DAY.lower() == "daily":
#             schedule_daily(generate_newsletter, SCHEDULE_TIME)
#             log_schedule_event(f"Scheduled to run DAILY at {SCHEDULE_TIME}")
#         else:
#             schedule_weekly(generate_newsletter, SCHEDULE_DAY, SCHEDULE_TIME)
#             log_schedule_event(f"Scheduled to run every {SCHEDULE_DAY.upper()} at {SCHEDULE_TIME}")
        
#         return True
        
#     except Exception as e:
#         log_schedule_event(f"ERROR: Failed to setup scheduler: {e}")
#         return False

# def run_scheduler(run_once: bool = False):
#     """
#     Start the scheduler loop.
    
#     This function blocks and runs indefinitely, checking for scheduled jobs
#     and executing them at their specified times.
    
#     Args:
#         run_once: If True, run pending jobs once and return.
#                  If False, run indefinitely (default).
#     """
#     if not SCHEDULE_ENABLED:
#         log_schedule_event("Scheduler not enabled. Skipping scheduler loop.")
#         return
    
#     log_schedule_event("Starting scheduler loop...")
    
#     try:
#         if run_once:
#             # Run pending jobs once and return
#             schedule.run_pending()
#             log_schedule_event("Run-once mode: Executed pending jobs and exiting")
#             return
        
#         # Infinite loop: check every minute for scheduled jobs
#         while True:
#             schedule.run_pending()
#             time.sleep(60)  # Check every 60 seconds
            
#     except KeyboardInterrupt:
#         log_schedule_event("Scheduler interrupted by user")
#     except Exception as e:
#         log_schedule_event(f"ERROR: Scheduler encountered exception: {e}")
#         raise

# def print_scheduled_jobs():
#     """Print all currently scheduled jobs for debugging"""
#     jobs = schedule.get_jobs()
    
#     if not jobs:
#         print("\nNo jobs scheduled.")
#         return
    
#     print("\n" + "=" * 60)
#     print("SCHEDULED JOBS")
#     print("=" * 60)
#     for idx, job in enumerate(jobs, 1):
#         print(f"{idx}. {job}")
#     print("=" * 60 + "\n")

# ================== UTILITIES ==================

def extract_json(raw_response, expected_type="object"):
    """Extract JSON from LLM response"""
    content = (raw_response or "").strip()
    
    # Remove markdown fences
    fence = "```"
    if content.startswith(fence + "json"):
        content = content[7:]
    elif content.startswith(fence):
        content = content[3:]
    if content.endswith(fence):
        content = content[:-3]
    content = content.strip()
    
    # Find JSON boundaries
    if expected_type == "array":
        start = content.find("[")
        end = content.rfind("]") + 1
    else:
        start = content.find("{")
        end = content.rfind("}") + 1
    
    if start != -1 and end > start:
        content = content[start:end]
    
    # Clean control characters
    content = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", content)
    
    try:
        return json.loads(content, strict=False)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}") from e

def normalize_url(url: str) -> str:
    """Normalize URL for deduplication"""
    try:
        parsed = urlparse(url)
        query_pairs = [
            (k, v) for k, v in parse_qsl(parsed.query)
            if not k.lower().startswith(("utm_", "ref", "source"))
        ]
        new_query = urlencode(query_pairs, doseq=True)
        normalized = parsed._replace(query=new_query, fragment="")
        path = normalized.path.rstrip("/")
        normalized = normalized._replace(path=path)
        return urlunparse(normalized)
    except Exception:
        return url

def parse_rss_datetime(entry):
    """Convert RSS entry time to timezone-aware datetime"""
    dt_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if dt_struct:
        return datetime(*dt_struct[:6], tzinfo=timezone.utc)
    return None

def load_feeds_from_excel(path=FEEDS_EXCEL_PATH, sheet_name=FEEDS_SHEET_NAME):
    """Load RSS feed URLs from Excel"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Excel file not found: {path}")
    
    df = pd.read_excel(path, sheet_name=sheet_name)
    required_cols = {"FeedName", "FeedURL", "Include"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Excel missing columns: {missing}")
    
    include_col = df["Include"].astype(str).str.strip().str.lower()
    df = df[include_col.isin(["yes", "y", "true", "1"])]
    feeds = df["FeedURL"].astype(str).str.strip()
    return [f for f in feeds if f]

def normalize_title_for_filename(title: str, max_length=150):
    """Create safe filename from title"""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower())
    slug = slug.strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "article"

# ================== STEP 1: FETCH & SMART PRE-FILTER ==================

def keyword_relevance_score(article, category_keywords):
    """Fast keyword-based relevance check (no LLM)"""
    text = f"{article['title']} {article['summary']}".lower()
    matches = sum(1 for keyword in category_keywords if keyword in text)
    return matches

def fetch_and_prefilter_articles(feeds, days_back=DAYS_BACK):
    """Fetch articles and pre-filter with keywords"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    categorized = {cat: [] for cat in CATEGORIES}
    seen_urls = set()
    
    print(f"Fetching articles from last {days_back} days...")
    
    for feed_url in feeds:
        print(f"  → {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                pub_dt = parse_rss_datetime(entry)
                if pub_dt and pub_dt < cutoff:
                    continue
                
                title = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                if not link or not title:
                    continue
                
                normalized_link = normalize_url(link)
                if normalized_link in seen_urls:
                    continue
                seen_urls.add(normalized_link)
                
                summary = (entry.get("summary") or "").strip()
                source = feed.feed.get("title", "Unknown Source").strip()
                date_str = pub_dt.strftime("%Y-%m-%d") if pub_dt else "Unknown"
                
                article = {
                    "title": title,
                    "link": link,
                    "normalized_link": normalized_link,
                    "pub_dt": pub_dt,
                    "date_str": date_str,
                    "source": source,
                    "summary": summary
                }
                
                # Check which category fits best
                best_category = None
                best_score = 0
                
                for category, keywords in CATEGORIES.items():
                    score = keyword_relevance_score(article, keywords)
                    if score > best_score:
                        best_score = score
                        best_category = category
                
                # Only keep if at least 2 keyword matches
                if best_score >= 2:
                    article["keyword_score"] = best_score
                    categorized[best_category].append(article)
        
        except Exception as e:
            print(f"    ! Error: {e}")
    
    # Sort each category by keyword score and date
    for category in categorized:
        categorized[category].sort(
            key=lambda x: (x["keyword_score"], x["pub_dt"] or datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True
        )
    
    total = sum(len(articles) for articles in categorized.values())
    print(f"\nPre-filtered to {total} articles across {len(CATEGORIES)} categories")
    for cat, articles in categorized.items():
        print(f"  {cat}: {len(articles)} articles")
    
    return categorized

# ================== STEP 2: LLM SCORING & REFINEMENT (SINGLE PASS) ==================

def score_and_select_articles(categorized_articles):
    """
    Single LLM call per category to:
    1. Validate relevance
    2. Score articles
    3. Select top N
    
    Total LLM calls for scoring = 5 (one per category)
    """
    selected_by_category = {}
    
    for category, articles in categorized_articles.items():
        if not articles:
            selected_by_category[category] = []
            continue
        
        # Take top 10 by keyword score as candidates
        candidates = articles[:10]
        
        print(f"\nScoring {category} ({len(candidates)} candidates)...")
        
        # Build a compact prompt
        articles_json = []
        for idx, art in enumerate(candidates):
            articles_json.append({
                "id": idx,
                "title": art["title"],
                "summary": art["summary"][:200],  # Truncate to save tokens
                "source": art["source"]
            })
        
        prompt = f"""You are scoring {category} articles for an AI newsletter.

TASK: Score each article bet 0-100 based on:
- Relevance to "{category}" = (50%)
- Business importance = (30%)
- Newsworthiness = (20%)

Return ONLY JSON array:
[
  {{"id": 0, "score": 85, "relevant": true}},
  {{"id": 1, "score": 42, "relevant": false}}
]

ARTICLES:
{json.dumps(articles_json, indent=2)}"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = api_call(messages, temperature=0.2, max_tokens=500)
            scores = extract_json(response, expected_type="array")
            
            # Apply scores
            for item in scores:
                idx = item.get("id")
                if isinstance(idx, int) and 0 <= idx < len(candidates):
                    candidates[idx]["ai_score"] = item.get("score", 0)
                    candidates[idx]["relevant"] = item.get("relevant", True)
            
            # Filter and sort
            relevant = [a for a in candidates if a.get("relevant", True)]
            relevant.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
            
            selected_by_category[category] = relevant[:ARTICLES_PER_CATEGORY]
            print(f"  Selected {len(selected_by_category[category])} articles")
            
        except Exception as e:
            print(f"  ! Error scoring {category}: {e}")
            # Fallback: use keyword scores
            selected_by_category[category] = candidates[:ARTICLES_PER_CATEGORY]
    
    return selected_by_category

# ================== STEP 3: BATCH SUMMARIZATION ==================

def batch_summarize_articles(selected_by_category):
    """
    Summarize all articles in one category per LLM call.
    Total calls for summarization = 5 (one per category)
    """
    enriched_by_category = {}
    
    for category, articles in selected_by_category.items():
        if not articles:
            enriched_by_category[category] = []
            continue
        
        print(f"\nSummarizing {category} articles...")
        
        # Build prompt with all articles in category
        articles_text = []
        for idx, art in enumerate(articles):
            articles_text.append(f"""
ARTICLE {idx}:
Title: {art['title']}
Source: {art['source']}
Date: {art['date_str']}
Summary: {art['summary'][:300]}
Link: {art['link']}
---""")
        
        prompt = f"""Create summaries for {category} articles.

For EACH article, provide:
1. "summary": 60-100 word paragraph explaining what happened and why it matters
2. "key_point": One sentence highlighting the main takeaway

Return ONLY JSON:
{{
  "articles": [
    {{
      "id": 0,
      "summary": "...",
      "key_point": "..."
    }}
  ]
}}

ARTICLES:
{"".join(articles_text)}"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = api_call(messages, temperature=0.3, max_tokens=1500)
            data = extract_json(response, expected_type="object")
            
            # Apply summaries
            summaries_by_id = {item["id"]: item for item in data.get("articles", [])}
            
            enriched = []
            for idx, art in enumerate(articles):
                summary_data = summaries_by_id.get(idx, {})
                enriched.append({
                    **art,
                    "llm_summary": summary_data.get("summary", art["summary"][:200]),
                    "key_point": summary_data.get("key_point", "")
                })
            
            enriched_by_category[category] = enriched
            print(f"  Summarized {len(enriched)} articles")
            
        except Exception as e:
            print(f"  ! Error summarizing {category}: {e}")
            enriched_by_category[category] = articles
    
    return enriched_by_category

# ================== STEP 4: WEEKLY OVERVIEW ==================

def generate_weekly_overview(enriched_by_category):
    """
    Single LLM call to create newsletter intro.
    Total calls for the weekly overview = 1
    """
    print("\nGenerating weekly overview...")
    
    # Compact representation of all articles
    overview_data = {}
    for category, articles in enriched_by_category.items():
        if articles:
            overview_data[category] = [
                {
                    "title": art["title"][:100],
                    "key_point": art.get("key_point", "")[:100],
                }
                for art in articles
            ]
    
    # Skip if no articles
    if not any(overview_data.values()):
        return "No articles available for this week.", []
    
    prompt = f"""Write a newsletter intro for this week's AI news.

Create:
1. intro: 2-3 paragraphs (120-180 words) highlighting main themes
2. key_themes: 3-5 short sentences (one-liners) across categories

Return ONLY this JSON:
{{"intro":"...","key_themes":["...","..."]}}

Articles this week:
{json.dumps(overview_data)}

Rules:
- Return ONLY the JSON object
- No markdown, no explanation
- Executive-focused, business implications"""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = api_call(messages, temperature=0.3, max_tokens=800)
        
        # Debug
        print(f"  Response preview: {response[:200]}")
        
        data = extract_json(response, expected_type="object")
        
        return (
            data.get("intro", "Weekly AI developments across key areas."),
            data.get("key_themes", [])
        )
    except Exception as e:
        print(f"  ! Error generating overview: {e}")
        print(f"  ! Raw response: {response[:500] if 'response' in locals() else 'No response'}")
        return "This week's AI developments across key areas.", []

# ================== STEP 5: BUILD HTML ==================

def build_html_newsletter(enriched_by_category, intro, key_themes):
    """Generate the final HTML newsletter"""
    import base64
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Embed logo as base64
    logo_base64 = ""
    try:
        with open("logo.png", "rb") as img_file:
            logo_base64 = base64.b64encode(img_file.read()).decode('utf-8')
    except FileNotFoundError:
        print("  ! Warning: Logo not found, will not be displayed")
    
    # Key themes section
    themes_html = "".join(f"<li>{theme}</li>" for theme in key_themes)
    
    # Category sections
    category_sections = []
    for category, articles in enriched_by_category.items():
        if not articles:
            continue
        
        article_blocks = []
        for art in articles:
            # Safely get summary - use llm_summary if available, otherwise original summary
            summary = art.get('llm_summary') or art.get('summary', 'No summary available')[:300]
            key_point = art.get('key_point', '')
            
            block = f"""
            <div style="margin-bottom: 20px; padding-left: 16px; border-left: 3px solid #0066cc;">
              <h4 style="margin: 0 0 4px 0; font-size: 16px;">
                <a href="{art['link']}" style="color:#0056b3; text-decoration:none;">
                  {art['title']}
                </a>
              </h4>
              <div style="font-size: 11px; color: #666; margin-bottom: 6px;">
                {art['source']} • {art['date_str']}
              </div>
              <p style="font-size: 13px; line-height: 1.5; margin: 0;">
                {summary}
              </p>
              {f'<p style="font-size: 12px; margin: 6px 0 0 0; font-style: italic;">→ {key_point}</p>' if key_point else ''}
            </div>
            """
            article_blocks.append(block)
        
        section = f"""
        <div style="margin-top: 32px;">
          <h2 style="font-size: 20px; color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 4px;">
            {category}
          </h2>
          {"".join(article_blocks)}
        </div>
        """
        category_sections.append(section)
    
    disclaimer = (
        "Generated by AI • Verify critical information • " + 
        f"{daily_request_count} API calls used"
    )
    
    # Logo img tag - uses base64 if available, otherwise empty
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height: 60px; width: auto; margin-bottom: 16px; background-color: #0056A7; padding: 10px; border-radius: 4px;">' if logo_base64 else ''
    
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>AI Newsletter - {today_str}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; color: #222; line-height: 1.6; margin: 0; padding: 0; background: #f5f5f5;">
  <div style="max-width: 700px; margin: 0 auto; background: white; padding: 32px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    
    <div style="margin-bottom: 32px;">
      {logo_html}
      <div style="text-align: center;">
        <h1 style="font-size: 28px; margin: 0 0 8px 0; color: #0066cc;">The AI Ledger</h1>
        <div style="font-size: 13px; color: #666;">Week ending {today_str}</div>
      </div>
    </div>
    
    <div style="background: #f8f9fa; padding: 20px; border-radius: 6px; margin-bottom: 32px;">
      <h2 style="font-size: 18px; margin: 0 0 12px 0;">This Week in AI</h2>
      <div style="font-size: 14px; line-height: 1.6;">
        {intro}
      </div>
      {f'<div style="margin-top: 16px;"><strong style="font-size: 13px;">Key Themes:</strong><ul style="margin: 8px 0 0 0; font-size: 13px;">{themes_html}</ul></div>' if themes_html else ''}
    </div>
    
    {"".join(category_sections)}
    
    <hr style="margin: 40px 0 16px 0; border: none; border-top: 1px solid #ddd;">
    <p style="font-size: 11px; color: #888; text-align: center;">
      {disclaimer}
    </p>
  </div>
</body>
</html>"""
    return html

# # ================== STEP 6: ARTICLE ARCHIVE HELPERS ==================

# def fetch_full_article_html(url: str) -> str:
#     """Fetch the full HTML of the article URL."""
#     try:
#         resp = requests.get(url, timeout=30.0)
#         resp.raise_for_status()
#         return resp.text
#     except Exception as e:
#         print(f"  ! Failed to fetch full article HTML for {url}: {e}")
#         return ""


# def extract_main_content(html: str) -> str:
#     """
#     Extract the main article content (text + images) from raw HTML
#     using simple BeautifulSoup heuristics.
#     """
#     if not html:
#         return "<p>Full article content could not be retrieved.</p>"

#     soup = BeautifulSoup(html, "html.parser")

#     candidate = soup.find("article")
#     if not candidate:
#         divs = soup.find_all("div")
#         best_div = None
#         best_count = 0
#         for d in divs:
#             p_count = len(d.find_all("p"))
#             if p_count > best_count:
#                 best_count = p_count
#                 best_div = d
#         candidate = best_div

#     if not candidate:
#         return "<p>Full article content could not be identified.</p>"

#     for tag in candidate.find_all(["script", "style", "noscript", "iframe"]):
#         tag.decompose()

#     return str(candidate)


# def build_article_archive_html(article: dict, body_html: str) -> str:
#     """
#     Build a clean archive HTML page for a single article, using fields
#     produced by this Groq-optimized pipeline.
#     """
#     title = article.get("title", "Untitled")
#     link = article.get("link", "#")
#     source = article.get("source", "Unknown Source")
#     date_str = article.get("date_str", "Unknown")
#     score = article.get("ai_score", 0)
#     original_summary = article.get("summary", "").strip() or "No summary available."
#     llm_summary = article.get("llm_summary", "").strip()
#     key_point = article.get("key_point", "").strip()

#     score_html = f" | Score: {score}" if score else ""
#     key_point_html = (
#         f'<p style="font-size: 14px; font-style: italic;">Key takeaway: {key_point}</p>'
#         if key_point
#         else ""
#     )

#     html = f"""
# <!DOCTYPE html>
# <html>
# <head>
#   <meta charset="utf-8" />
#   <title>{title}</title>
# </head>
# <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; color: #222; line-height: 1.5; margin: 0; padding: 0;">
#   <div style="max-width: 800px; margin: 0 auto; padding: 24px;">
#     <h1 style="font-size: 24px; margin-bottom: 8px;">
#       <a href="{link}" style="color:#0056b3; text-decoration:none;">{title}</a>
#     </h1>
#     <div style="font-size: 12px; color: #666; margin-bottom: 16px;">
#       Published: {date_str} | Source: {source}{score_html}
#     </div>

#     <h2 style="font-size: 18px; margin-top: 16px;">Original Summary</h2>
#     <p style="font-size: 14px; line-height: 1.5;">
#       {original_summary}
#     </p>

#     <h2 style="font-size: 18px; margin-top: 24px;">Article Content</h2>
#     <div style="font-size: 14px; line-height: 1.6;">
#       {body_html}
#     </div>

#     <h2 style="font-size: 18px; margin-top: 24px;">AI Summary</h2>
#     <p style="font-size: 14px; line-height: 1.5;">
#       {llm_summary or original_summary}
#     </p>

#     {key_point_html}
#   </div>
# </body>
# </html>
# """
#     return html

# # ================== STEP 7: SEND E-MAIL ==================


# def send_email(html_content, subject_suffix=""):
#     """Send the HTML newsletter via SMTP email."""
#     if not (SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and EMAIL_FROM and EMAIL_TO):
#         print("Email configuration incomplete; skipping send.")
#         return

#     today_str = datetime.now().strftime("%Y-%m-%d")
#     subject = f"{EMAIL_SUBJECT_PREFIX} {today_str}"
#     if subject_suffix:
#         subject = f"{subject} - {subject_suffix}"

#     msg = MIMEMultipart("alternative")
#     msg["Subject"] = subject
#     msg["From"] = EMAIL_FROM
#     msg["To"] = ", ".join(EMAIL_TO)

#     part_html = MIMEText(html_content, "html")
#     msg.attach(part_html)

#     print(f"Sending email to {msg['To']} via {SMTP_HOST}:{SMTP_PORT}...")
#     with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
#         server.starttls()
#         server.login(SMTP_USERNAME, SMTP_PASSWORD)
#         server.send_message(msg)
#     print("Email sent.")


# ================== NEWSLETTER GENERATION FUNCTION ==================

def generate_newsletter():
    """
    Core newsletter generation logic. Can be called directly or via scheduler.
    """
    # 1. Load feeds
    try:
        feeds = load_feeds_from_excel()
        print(f"\nLoaded {len(feeds)} RSS feeds")
    except Exception as e:
        print(f"Failed to load feeds: {e}")
        return
    
    # 2. Fetch and pre-filter (NO LLM)
    categorized = fetch_and_prefilter_articles(feeds)
    
    # 3. Score and select top articles (5 LLM calls)
    selected = score_and_select_articles(categorized)
    total_selected = sum(len(arts) for arts in selected.values())
    print(f"\nTotal selected: {total_selected} articles")
    
    # 4. Batch summarization (5 LLM calls)
    enriched = batch_summarize_articles(selected)
    
    # 5. Weekly overview (1 LLM call)
    intro, themes = generate_weekly_overview(enriched)
    
    # 6. Build HTML
    html = build_html_newsletter(enriched, intro, themes)
    
    # 7. Save
    run_dt = datetime.now()
    run_ts = run_dt.strftime("%Y-%m-%d_%H-%M-%S")
    month_name = run_dt.strftime("%B")
    
    newsletter_dir = os.path.join(NEWSLETTER_OUTPUT_DIR, month_name)
    os.makedirs(newsletter_dir, exist_ok=True)
    
    newsletter_path = os.path.join(newsletter_dir, f"{run_ts}.html")
    with open(newsletter_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return newsletter_path

# ================== MAIN ==================

def main():
    print("=" * 60)
    print("AI NEWSLETTER GENERATOR WITH SCHEDULER")
    print("=" * 60)
    
    start_time = time.time()
    
    # Generate newsletter once
    newsletter_path = generate_newsletter()
    
    # Final message
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✓ Newsletter saved: {newsletter_path}")
    print(f"✓ API calls used: {daily_request_count}")
    print(f"✓ Time elapsed: {elapsed:.1f}s")
    print("=" * 60)
    
    # # Setup and run scheduler if enabled
    # if setup_scheduler():
    #     print_scheduled_jobs()
    #     print("\nStarting scheduler loop (press Ctrl+C to stop)...")
    #     print("Scheduler will check for jobs every 60 seconds.\n")
    #     run_scheduler()
    # else:
    #     print("\nScheduler is disabled. Newsletter generation complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        raise
