\# data/ — Δεδομένα



Όλα τα δεδομένα: raw (κατεβασμένα), processed (επεξεργασμένα), models (trained).



\## Δομή



\- raw/ — Input (κατεβασμένα από web/API)

\- processed/ — Μετά από train/compute

\- models/ — Trained models (.pkl, .joblib)



\## data/raw/



\- fantasy\_data.json — EuroLeague API — fetch\_euroleague.py

\- injuries.json — BasketNews — fetch\_injuries.py

\- coaches.json — Manual/curated

\- basketstories\_credits.json — BasketStories — fetch\_credits.py

\- basketstories\_player\_stats.json — BasketStories — fetch\_player\_stats.py

\- player\_bios.json — EuroLeague API — fetch\_euroleague.py

\- player\_heights.json — Manual

\- team\_mapping.json — Hardcoded — core/team\_mapping.py

\- .cache/ — Cache — fetch\_euroleague.py



\## data/processed/



\- player\_predictions.json — train\_model.py — Predictions για convert

\- model\_metrics.json — train\_model.py — MAE, features

\- coach\_stats.json — compute\_coach\_stats.py — Coach xp + adj

\- defensive\_profiles.json — build\_defense.py — Team defense

\- backtest\_results.json — (analysis) — Backtest

\- feature\_analysis.json — (analysis) — Feature importance

\- feature\_analysis\_v2.json — (analysis) — v2

\- height\_analysis.json — (analysis) — Height analysis



\## data/models/



Trained models (.pkl):



\- model.pkl — Ensemble (Ridge + GB + MA)

\- model\_gb.pkl — GradientBoosting

\- model\_ridge.pkl — Ridge



\## Pipeline



&#x20;   1. FETCH

&#x20;      fetch\_euroleague.py    -> data/raw/fantasy\_data.json

&#x20;      fetch\_credits.py       -> data/raw/basketstories\_credits.json

&#x20;      fetch\_player\_stats.py  -> data/raw/basketstories\_player\_stats.json

&#x20;      fetch\_injuries.py      -> data/raw/injuries.json

&#x20;      fetch\_scores.py        -> app/js/data/game-boxscores.js



&#x20;   2. TRAIN

&#x20;      train\_model.py         -> data/processed/player\_predictions.json

&#x20;      build\_defense.py       -> data/processed/defensive\_profiles.json



&#x20;   3. COMPUTE

&#x20;      compute\_coach\_stats.py -> data/processed/coach\_stats.json

&#x20;      compute\_trend\_confidence.py -> app/js/data/player-trend-confidence.js



&#x20;   4. CONVERT

&#x20;      (όλα -> app/js/data/)



\## Σύμβαση Ονομάτων



\- RAW: όπως τα κατεβάζει το API

\- PROCESSED: καθαρά ονόματα χωρίς version:

&#x20;   - player\_predictions.json (όχι \_v4\_2)

&#x20;   - model\_metrics.json (όχι \_v4\_2)

&#x20;   - defensive\_profiles.json (όχι \_v2)



\## Σημειώσεις



\- Backup: κρατάς εξωτερικό (git history όταν μπει)

\- Μέγεθος: το fantasy\_data.json είναι \~18MB

\- Cache: το data/raw/.cache/ μπορεί να διαγραφεί

\- OneDrive sync: μεγάλα JSON αρχεία, sync delays πιθανά



\## ΜΗΝ



\- ΜΗΝ επεξεργάζεσαι data/raw/\* manually

\- ΜΗΝ αλλάζεις ονόματα

\- ΜΗΝ κάνεις commit το fantasy\_data.json (>18MB)

