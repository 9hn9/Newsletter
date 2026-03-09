# Weekly AI/ML/DS Newsletter - Complete Setup Guide
Python script that generates a weekly AI / ML / GenAI newsletter from curated RSS feeds,
scores and summarizes articles using an LLM, and outputs HTML for email + archives.

Supports multiple LLM backends: **Groq**, **Ollama**, and **On-Premises LLM**.

---

## 1. Prerequisites
- Python 3.10+ installed with **"Add Python to PATH"** checked during install
- Git installed
- Access to an LLM endpoint (Groq API, Ollama API, or on-prem endpoint)
- Excel file: `Feeds_list.xlsx` with sheet `Sheet1` and columns:
  - `FeedName`
  - `FeedURL`
  - `Include` (`Yes` / `No`)
- To verify Python and pip:
    ```
    python --version
    pip --version
    ```

---

## 2. Clone the repository
In PowerShell or Command Prompt:
```
cd C:\path\to\your\project
git clone https://github.com/hrshtnr/Newsletter
cd (new Newsletter repo)
```

---

## 3. Create and activate virtual environment (Windows)
From the repo folder (`Newsletter`):
```
python -m venv .venv
.venv\Scripts\activate
```

You should see `(.venv)` at the start of the prompt.  
To deactivate later:
```
deactivate
```

---

## 4. Install dependencies
With the venv active:
```
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- `feedparser`, `requests`, `beautifulsoup4`
- `python-dotenv`, `pandas`, `openpyxl`
- `groq` (for Groq API backend)

For archival features (optional):
```
pip install beautifulsoup4 requests
```

---

## 5. Configure environment (.env)
1. Copy the example env file:
    ```
    copy .env.example .env
    ```
2. Open `.env` in your editor (VS Code, Notepad, etc.) and set the appropriate section below.

### Option A: Groq API (Default)
```
API_KEY=<your-api-key>
MODEL=<copy from the model card>
DAYS_BACK=n
FEEDS_EXCEL_PATH=Feeds_list.xlsx
FEEDS_SHEET_NAME=Sheet1
```

### Option B: Ollama (Local or Remote)
```
API_BASE=http://localhost:11434/v1
API_KEY=<optional-api-key>
MODEL=<copy from the model card>
DAYS_BACK=n
FEEDS_EXCEL_PATH=Feeds_list.xlsx
FEEDS_SHEET_NAME=Sheet1
```

Then uncomment the `OLLAMA API HELPER` section in `newsletter.py` and comment out the Groq client section.

### Option C: On-Premises LLM
```
LLM_API_URL=<your-local-api-endpoint>
API_KEY=<optional-api-key>
MODEL=<copy from the model card>
DAYS_BACK=n
FEEDS_EXCEL_PATH=Feeds_list.xlsx
FEEDS_SHEET_NAME=Sheet1
```

Then uncomment the `ON-PREM LLM` section in `newsletter.py` and comment out the Groq client section.

### Optional: Email Configuration
To enable email sending (currently commented out):
```
SMTP_HOST=<smtp-server>
SMTP_PORT=587
SMTP_USERNAME=<your-email>
SMTP_PASSWORD=<app-password>
EMAIL_FROM=<sender-email>
EMAIL_TO=recipient1@example.com,recipient2@example.com
EMAIL_SUBJECT_PREFIX=[The AI Ledger]
```

Keep `.env` **out of Git**; `.gitignore` already ignores it.

---

## 6. Place the feeds Excel file
- Put `Feeds_list.xlsx` in the repo root (`...Newsletter\Feeds_list.xlsx`)
- Ensure it has columns: `FeedName`, `FeedURL`, `Include`
- Update `FEEDS_EXCEL_PATH` in `.env` if using a different location:
  ```
  FEEDS_EXCEL_PATH=C:\path\to\Feeds list.xlsx
  ```

---

## 7. Run the newsletter script (Windows)
From the repo folder, with venv active:
```
python newsletter.py
```

On success, you should see console logs and:
- Newsletter HTML output:
    ```
    Outputs\<Month>\<YYYY-MM-DD_HH-MM-SS>.html
    ```

Open this file in a browser to review the generated newsletter.

---

## 8. Optional Archival Feature

The script can archive individual article pages with full HTML content. This is **currently disabled** but can be enabled.

### Enable Article Archival

1. Uncomment the following in `newsletter.py`:
   - `import requests` (top of file)
   - `from bs4 import BeautifulSoup` (top of file)
   - `fetch_full_article_html()` function
   - `extract_main_content()` function
   - `build_article_archive_html()` function
   - Article archival loop in `main()` (after step 7)

2. Run the script. On success, article archives will be saved:
    ```
    Archive\<Month>\<YYYY-MM-DD>\<HHMMSS>_<index>_<slug>.html
    ```

Each archive file includes:
- Original article metadata (title, source, date, AI score)
- Full article HTML content (extracted from the source URL)
- LLM-generated summary
- Key takeaway (one-liner)

---

## 9. Optional Email Feature

The script can send the generated newsletter via email. This is **currently disabled** but can be enabled.

### Enable Email Sending

1. Configure email variables in `.env`:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   EMAIL_FROM=your-email@gmail.com
   EMAIL_TO=recipient1@example.com,recipient2@example.com
   EMAIL_SUBJECT_PREFIX=[The AI Ledger]
   ```

2. Uncomment in `newsletter.py`:
   - `import smtplib` (top of file)
   - `from email.mime.text import MIMEText`
   - `from email.mime.multipart import MIMEMultipart`
   - `send_email()` function (around line 850)
   - `send_email(html)` call in `main()` (after step 7)

3. Run the script. The newsletter will be sent to all addresses in `EMAIL_TO`.

**Notes:**
- For Gmail: Use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password
- Corporate systems may require SMTP/ proxy configuration; check with IT
- Always test with a small distribution list first

---

## 10. LLM Backend Comparison

| Feature | Groq | Ollama | On-Prem |
|---------|------|--------|---------|
| **Setup** | API key only | Local/remote server | Deploy your own |
| **Cost** | Free tier available | Free (self-hosted) | Free (self-hosted) |
| **Speed** | Fast (cloud) | Depends on hardware | Depends on hardware |
| **Models** | Limited selection | Large selection | Your choice |
| **Internet** | Required | Optional | Required |
| **Privacy** | Data sent to Groq | Local only | Your control |

### Switching Backends

In `newsletter.py`, the API client is defined around line 180. To switch:

1. **Keep active:** Groq client initialization
   ```python
   client = Groq(api_key=API_KEY)
   ```

2. **Comment corresponding sections:**
   - If using Ollama: comment out Groq section, uncomment Ollama `api_call()`
   - If using On-Prem: comment out Groq section, uncomment On-Prem `api_call()`

3. Update `.env` with appropriate credentials for your chosen backend

---

## 11. Common Windows Issues

- **`python` not found**  
    Reinstall Python from python.org and ensure "Add Python to PATH" is checked. Then reopen PowerShell.

- **`pip` not found**  
    Usually fixed by reinstalling Python with PATH; or run:
        ```
        py -m pip install --upgrade pip
        ```

- **`activate` not recognized**  
    Ensure you use the Windows path:
        ```
        .venv\Scripts\activate
        ```

- **SSL or proxy issues calling LLM API**  
    Check API endpoint, corporate proxy settings, and firewall rules.

- **"Excel file not found"**  
    Verify `FEEDS_EXCEL_PATH` in `.env` matches the actual file location and name.

- **"Empty response from LLM"**  
    Check API key, model name, and LLM endpoint availability.

---

## 12. Running on a Schedule

Automate weekly runs using **Task Scheduler** (Windows):

1. Open Task Scheduler (search "Task Scheduler")
2. Create Basic Task → Name: "AI Newsletter"
3. Set trigger (weekly, specific day/time)
4. Set action:
   - Program: `C:\path\to\python.exe` (or path to your venv Python)
   - Arguments: `newsletter.py`
   - Start in: `C:\path\to\Newsletter`
5. Ensure the task user has access to:
   - The repo folder
   - The `.env` file
   - The LLM endpoint (network access)

---

## 13. Project Structure

```
Newsletter/
├── newsletter.py           # Main script
├── requirements.txt        # Dependencies
├── req2.txt               # Alternative dependencies (with groq)
├── README.md              # Original quick-start
├── read_me.md             # This file (comprehensive guide)
├── .env                   # Configuration (not in Git)
├── .env.example           # Example env file
├── Feeds list.xlsx        # RSS feed configuration
├── logo.png               # Newsletter logo (optional)
├── .venv/                 # Virtual environment
├── Outputs/               # Generated newsletters
│   ├── January/
│   ├── February/
│   └── ...
└── Archive/               # Article archives (if enabled)
    ├── January/
    ├── February/
    └── ...
```

---

## 14. Troubleshooting

### Newsletter generated but looks blank
- Check that RSS feeds are returning articles
- Verify `DAYS_BACK` setting in `.env` (increase if no recent articles)
- Run with `python newsletter.py 2>&1 | Tee-Object -FilePath debug.log` to capture full logs

### LLM API calls fail
- Verify `API_KEY` is correct
- Test endpoint with curl or Postman
- Check rate limiting (if using free tier)
- Ensure network can reach the endpoint

### Email not sending
- Verify `SMTP_HOST` and `SMTP_PORT` are correct
- Test credentials with a mail client first
- Check firewall/proxy rules
- Enable "Less secure app access" for Gmail (if applicable)

### Articles not being scored/summarized
- Increase `DAYS_BACK` in `.env` to fetch more articles
- Check RSS feed URLs are valid and returning content
- Review LLM model selection (`MODEL` in `.env`)

---

## 15. Next Steps

1. **Test the basic flow:** Run with Groq or Ollama to verify output
2. **Customize categories:** Edit `CATEGORIES` dict in `newsletter.py` to match your interests
3. **Enable archival:** Uncomment archival functions for full-content archives
4. **Configure email:** Set up SMTP and enable `send_email()` for distribution
5. **Schedule automation:** Use Task Scheduler for weekly runs
6. **Monitor performance:** Track API usage, newsletter quality, and user feedback