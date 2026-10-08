# control/ — EuroLeague Control Panel

Flask server για script running + workflows.

## Τι κάνει

- Σερβίρει το control-center.html
- Script runner: τρέχει scripts από το scripts/
- Workflows: προκαθορισμένες ακολουθίες scripts

ΔΕΝ έχει optimizer (αυτό είναι στο app/).

## Δομή

- server.py — Flask (port 5001)
- html/control-center.html — UI

## Εκκίνηση

    py control/server.py

Ή διπλό κλικ στο Control Panel.bat στη ρίζα.

URL: http://127.0.0.1:5001/

## Endpoints

- GET / — control-center.html
- GET /<path> — Static files
- GET /api/scripts — Λίστα scripts + workflows
- POST /api/run — Ξεκίνα script/workflow
- GET /api/run-status/<id> — Status + output

## Scripts Catalog

Κατηγορίες:

- FETCH (5): fetch_euroleague, fetch_credits, fetch_player_stats, fetch_injuries, fetch_scores
- COMPUTE (2): compute_coach_stats, compute_trend_confidence
- TRAIN (2): train_model, build_defense
- CONVERT (5): convert_predictions, convert_gamelogs, convert_stats, convert_coaches, apply_injuries
- VALIDATE (5): validate_all, validate_optimizer, validate_sanity, analyze_predictions, log_predictions

## Workflows

- update_all — 14 scripts (~30λ)
- fetch_convert — 11 scripts (~20λ)
- convert_only — 7 scripts (~1λ)
- injuries_only — 2 scripts (~10δ)

## Πώς Τρέχει Scripts

POST /api/run με workflow:

    { "workflow": "injuries_only" }

ή με λίστα scripts:

    { "scripts": ["fetch_injuries", "apply_injuries"] }

Response: { "ok": true, "run_id": "abc123" }

GET /api/run-status/abc123:

    {
      "ok": true,
      "status": "running",
      "current_script": "Fetch injuries",
      "output": ["..."],
      "elapsed": 3.2
    }

## Σημειώσεις

- Port: 5001
- Run state: in-memory (χάνεται σε restart)
- cwd: πάντα ROOT
- Concurrency: threaded=True