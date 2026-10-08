# app/ — EuroLeague App

Flask server + static frontend.

## Τι κάνει

- Σερβίρει το `EuroLeague.html` + assets (css, js, logos)
- **Optimizer API** (`/api/optimize`, `/api/players`, `/api/coaches`)

**ΔΕΝ** έχει script runner (αυτό είναι στο `control/`).

## Δομή

- `server.py` — Flask (port 5000)
- `html/EuroLeague.html` — Single-page app
- `css/style.css` + `css/fantasy-team-v2.css`
- `js/config/` — config.js, data.js (GAMES_RAW, LOGOS, TEAMS)
- `js/core/` — engine, state, team-helpers
- `js/data/` — auto-generated (player_predictions, etc.)
- `js/ui/` — app.js, header.js
- `js/utils/` — autocomplete, konfetti
- `js/views/` — games, standings, dashboard, fantasy, κλπ
- `logos/EL/` — EuroLeague logos
- `logos/teams/` — 20 ομάδες

## Εκκίνηση
py app/server.py

text

Ή διπλό κλικ στο `EuroLeague.bat` στη ρίζα.

URL: http://127.0.0.1:5000/

## Endpoints

| Endpoint | Method | Τι κάνει |
|---|---|---|
| `/` | GET | EuroLeague.html |
| `/<path>` | GET | Static files |
| `/api/players` | GET | Λίστα παικτών |
| `/api/coaches` | GET | Λίστα coaches |
| `/api/optimize/test` | GET | Dummy team + 3 λύσεις |
| `/api/optimize` | POST | Optimize από current team |

## Optimizer API

POST /api/optimize:

```json
{
  "player_ids": ["001255", "003958"],
  "coach_id": "PAN",
  "cash": 10.0,
  "max_transfers": 4
}
Response:

json
{
  "ok": true,
  "current_team": {},
  "results": [
    { "rank": 1, "score": 134.22, "formation": "1-2-2" }
  ]
}
Dependencies
core.paths — paths

core.config — ports, constants

core.optimize — optimizer (MILP)

Σημειώσεις
Static paths: σερβίρει από app/ (root = app/)

JS data: auto-generated από scripts/convert/ — μην τα πειράζεις manually

Port: 5000 (config: core/config.py:SERVER_PORT_APP)
