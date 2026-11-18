# Voter Tally Console - 175 Kuppam (Cheekatipalle GP)

A high-performance web console for Gram Panchayat voter tallying, candidate status mapping (TDP, YCP, Neutral, Dead, Unknown), and real-time polling turnout tracking.

## Features
- **100% Verified Electoral Roll**: Exactly 593 voter records mapped from `voters-new.pdf` (Pages 1 to 23).
- **Photos & Original Slips**: High-resolution cropped voter photos and tap-to-view original scanned slips.
- **Real-Time Interactive Scoreboard**: Live tracking of TDP, YCP, Neutral, Dead, Unknown, Unmarked, Margin, and Turnout.
- **Mobile-Optimized Dynamic Layout**: Compact ribbon taking $\le 16\%$ screen height, collapsible filter drawer, and sticky bottom real-time tally.
- **Fast Search & Filters**: Search by Name, EPIC ID, House No, GP Serial #, Ward, Gender, and Polled status.
- **Export & Reset**: Instant CSV export and one-click tally reset.

---

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. Open your browser:
   ```
   http://localhost:5000
   ```

---

## Deployment & Database Note (Netlify vs Render)

> [!IMPORTANT]
> **Netlify vs Persistent Backend (SQLite)**
> - **Netlify** is a static & serverless platform. It does not provide a persistent disk or a continuous Python/Flask server. In serverless environments, SQLite disk writes cannot persist across user requests.
> - **Recommended Free Hosting**: **[Render.com](https://render.com)** or **[Railway.app](https://railway.app)**:
>   - Directly runs Flask with `gunicorn app:app` via the included `Procfile`.
>   - Keeps `voters.db` persistent so vote tallies, polled status, and markings are saved.
>   - Automatically connects to this GitHub repository and deploys on push.
