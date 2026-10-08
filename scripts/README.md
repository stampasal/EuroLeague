\# scripts/ — Όλα τα Python Scripts



\## Δομή



\- fetch/ — Κατεβάζουν δεδομένα (από web/API)

\- train/ — Εκπαιδεύουν μοντέλα (ML)

\- compute/ — Υπολογισμοί (χωρίς fetch/train)

\- convert/ — JSON -> JS (auto-generated για frontend)

\- validate/ — Έλεγχοι ποιότητας



\## fetch/ (5)



\- fetch\_euroleague.py — Game logs 2022-2026 (\~15λ) -> data/raw/fantasy\_data.json

\- fetch\_credits.py — Credits παικτών (\~2λ) -> data/raw/basketstories\_credits.json

\- fetch\_player\_stats.py — FR/BLA/FTA stats (\~5λ) -> data/raw/basketstories\_player\_stats.json

\- fetch\_injuries.py — Injury report (\~5δ) -> data/raw/injuries.json

\- fetch\_scores.py — Scores + boxscores (\~3λ) -> app/js/data/game-boxscores.js



\## train/ (2)



\- train\_model.py — Model v4.2 ensemble (\~10λ) -> data/processed/player\_predictions.json + model\_metrics.json

\- build\_defense.py — Defensive profiles (\~1λ) -> data/processed/defensive\_profiles.json



\## compute/ (2)



\- compute\_coach\_stats.py — Coach xp + adj (\~10δ) -> data/processed/coach\_stats.json

\- compute\_trend\_confidence.py — Trend + confidence (\~10δ) -> app/js/data/player-trend-confidence.js



\## convert/ (5)



\- convert\_predictions.py -> app/js/data/player\_predictions.js

\- convert\_gamelogs.py -> app/js/data/player-gamelogs.js

\- convert\_stats.py -> app/js/data/player-stats-2026.js

\- convert\_coaches.py -> app/js/data/coaches.js + coach\_stats.js

\- apply\_injuries.py -> app/js/data/player\_injuries.js



\## validate/ (5)



\- validate\_all.py — Data integrity, prediction sanity, model quality

\- validate\_optimizer.py — MILP vs brute-force (diff < 0.01)

\- validate\_sanity.py — 7 checks σε full dataset

\- analyze\_predictions.py — MAE, RMSE, calibration

\- log\_predictions.py — Snapshot predictions



\## Τρέξιμο



Όλα τα scripts τρέχουν ανεξάρτητα:



&#x20;   cd "C:\\Users\\spasa\\OneDrive\\5. Python \& Codes\\07. Euroleague Standing"

&#x20;   py scripts/fetch/fetch\_injuries.py

&#x20;   py scripts/train/train\_model.py

&#x20;   py scripts/convert/convert\_stats.py

&#x20;   py scripts/validate/validate\_optimizer.py



Από το Control Panel (5001): επιλέγεις scripts ή workflows.



\## Κοινοί Κανόνες



Όλα τα scripts:



\- Import core.paths, core.config, core.logger

\- ΔΕΝ έχουν hardcoded paths

\- ΔΕΝ χρειάζεται να τρέξουν από συγκεκριμένο directory

\- Χρησιμοποιούν sys.path.insert για να βρουν το core/



Template:



&#x20;   #!/usr/bin/env python3

&#x20;   import sys

&#x20;   from pathlib import Path



&#x20;   sys.path.insert(0, str(Path(\_\_file\_\_).resolve().parents\[2]))



&#x20;   from core.paths import DATA\_RAW, DATA\_PROC, APP\_JS\_DATA

&#x20;   from core.logger import get\_logger



&#x20;   log = get\_logger("my\_script", category="fetch")



&#x20;   def main():

&#x20;       log.info("Ξεκίνησε...")



&#x20;   if \_\_name\_\_ == "\_\_main\_\_":

&#x20;       main()



\## Pipeline



&#x20;   fetch/    -> data/raw/

&#x20;   train/    -> data/processed/

&#x20;   convert/  -> app/js/data/

&#x20;   validate/ -> output/reports/



\## Σημειώσεις



\- Logs: κάθε script γράφει σε logs/<category>/<name>.log

\- Auto-install: κάποια scripts (fetch) κάνουν auto-install dependencies

\- Injuries: πάντα τελευταίο βήμα (μετά το train)



