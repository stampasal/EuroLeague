# EuroLeague Fantasy Tracker

Εργαλείο για EuroLeague Fantasy: predictions, optimizer, injuries, coach stats.

## 🚀 Γρήγορη Εκκίνηση

**Διπλό κλικ σε ένα από τα 2 shortcuts:**

| Shortcut | Τι κάνει | URL |
|---|---|---|
| `EuroLeague.bat` | Ανοίγει το app (server + browser) | http://127.0.0.1:5000/ |
| `Control Panel.bat` | Ανοίγει το control panel (scripts + workflows) | http://127.0.0.1:5001/ |

**Απαιτήσεις:** Python 3.14+, `pip install -r requirements.txt`

## 📁 Δομή
Euroleague Standing/
├── EuroLeague.bat # Shortcut #1 (app)
├── Control Panel.bat # Shortcut #2 (control)
├── README.md # Αυτό το αρχείο
├── requirements.txt
├── .gitignore
│
├── app/ # Το app (server + static)
│ ├── server.py # Flask (port 5000) + optimizer API
│ ├── html/ # EuroLeague.html
│ ├── css/ # style.css, fantasy-team-v2.css
│ ├── js/ # config/, core/, data/, ui/, utils/, views/
│ └── logos/ # EL/, teams/
│
├── control/ # Το control panel
│ ├── server.py # Flask (port 5001) + script runner
│ └── html/ # control-center.html
│
├── scripts/ # Όλα τα Python scripts
│ ├── fetch/ # Κατεβάζουν δεδομένα
│ ├── train/ # Εκπαιδεύουν μοντέλα
│ ├── compute/ # Υπολογισμοί
│ ├── convert/ # JSON/JS generation
│ └── validate/ # Έλεγχοι
│
├── core/ # Κοινός πυρήνας
│ ├── paths.py # Όλα τα paths
│ ├── config.py # Constants
│ ├── logger.py # Logging setup
│ ├── loaders.py # JSON/JS helpers
│ ├── team_mapping.py # Full↔short team codes
│ └── optimize/ # MILP optimizer
│
├── data/ # Δεδομένα
│ ├── raw/ # Κατεβασμένα (JSON)
│ ├── processed/ # Μετά από επεξεργασία
│ └── models/ # Trained models (.pkl)
│
├── logs/ # Logs ανά κατηγορία
├── output/ # Reports, exports
│ └── reports/ # Validation, predictions log
│
└── requirements.txt

## 🔄 Workflows

Από το **Control Panel** (5001):

| Workflow | Τι κάνει | Χρόνος |
|---|---|---|
| **Update ALL** | Fetch + Train + Convert | ~30λ |
| **Fetch + Convert** | Fetch + JS generation (χωρίς train) | ~20λ |
| **Only Convert** | JS generation από υπάρχοντα data | ~1λ |
| **Only Injuries** | Fetch + apply injuries | ~10δ |

## 🧠 Πώς Δουλεύει

**Pipeline:**
FETCH → data/raw/*.json (κατεβάζει από EuroLeague/BasketNews)

TRAIN → data/processed/*.json (μοντέλο v4.2, 17 features)

CONVERT → app/js/data/*.js (για το frontend)

VALIDATE → output/reports/* (checks)

**Optimizer:**
- Χρησιμοποιεί **MILP** (PuLP) για να βρει την καλύτερη ομάδα
- Constraints: 4G + 4F + 2C, budget 100, max transfers
- Διαβάζει `app/js/data/*.js` (predictions, stats, coaches, injuries)

## 📊 Scripts ανά Κατηγορία

### Fetch
- `fetch_euroleague.py` — Game logs 2022-2026 (~15λ)
- `fetch_credits.py` — BasketStories credits (~2λ)
- `fetch_player_stats.py` — FR/BLA/FTA stats (~5λ)
- `fetch_injuries.py` — BasketNews injury report (~5δ)
- `fetch_scores.py` — Scores + boxscores (~3λ)

### Train
- `train_model.py` — Model v4.2 ensemble (~10λ)
- `build_defense.py` — Defensive profiles (~1λ)

### Compute
- `compute_coach_stats.py` — Coach xp + adj (~10δ)
- `compute_trend_confidence.py` — Trend/confidence (~10δ)

### Convert
- `convert_predictions.py` — player_predictions.js
- `convert_gamelogs.py` — player-gamelogs.js
- `convert_stats.py` — player-stats-2026.js
- `convert_coaches.py` — coaches.js + coach_stats.js
- `apply_injuries.py` — player_injuries.js

### Validate
- `validate_all.py` — Data integrity
- `validate_optimizer.py` — MILP vs brute-force
- `validate_sanity.py` — Full dataset checks
- `analyze_predictions.py` — Prediction analysis
- `log_predictions.py` — Αποθήκευση snapshot

## 🛠️ Τρέξιμο Scripts μεμονωμένα

```bash
cd "C:\Users\spasa\OneDrive\5. Python & Codes\07. Euroleague Standing"

py scripts/fetch/fetch_injuries.py
py scripts/validate/validate_optimizer.py
py scripts/convert/convert_stats.py
Όλα τα scripts:

Τρέχουν ανεξάρτητα (δεν χρειάζεται να είσαι στο σωστό directory)

Χρησιμοποιούν core.paths για paths (όχι relative)

Γράφουν logs σε logs/<category>/

📝 Σημειώσεις
Backups: έξω από το project (git history)

OneDrive: το project είναι σε OneDrive — sync delays πιθανά

Python: 3.14

Model: v4.2, 17 features, ensemble (Ridge + GB + MA)

📚 Περισσότερα
app/README.md — το app

control/README.md — το control panel

scripts/README.md — scripts

core/README.md — core modules

data/README.md — data folders