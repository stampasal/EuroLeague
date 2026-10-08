\# core/ — Κοινός Πυρήνας



Όλα τα shared modules. Κανένα script δεν έχει hardcoded paths — όλα περνάνε από εδώ.



\## Δομή



\- \_\_init\_\_.py — Version

\- paths.py — Όλα τα paths

\- config.py — Constants (ports, seasons, budget)

\- logger.py — Logging setup

\- loaders.py — JSON/JS helpers

\- team\_mapping.py — Full <-> short team codes (20 ομάδες)

\- optimize/ — MILP optimizer

&#x20;   - constraints.py — Player, Coach, CurrentTeam

&#x20;   - best\_team.py — solve\_scenario, \_solve\_once



\## core/paths.py



Όλα τα paths σε ένα σημείο.



&#x20;   from core.paths import (

&#x20;       ROOT,              # ...\\07. Euroleague Standing

&#x20;       DATA\_RAW,          # ...\\data\\raw

&#x20;       DATA\_PROC,         # ...\\data\\processed

&#x20;       APP,               # ...\\app

&#x20;       APP\_JS\_DATA,       # ...\\app\\js\\data

&#x20;       CONTROL,           # ...\\control

&#x20;       LOGS,              # ...\\logs

&#x20;       OUTPUT,            # ...\\output

&#x20;   )



Files:



&#x20;   from core.paths import F\_FANTASY\_DATA, F\_PREDICTIONS, F\_COACH\_STATS



Helper:



&#x20;   from core.paths import ensure\_dirs

&#x20;   ensure\_dirs()   # δημιουργεί όλους τους φακέλους αν λείπουν



\## core/config.py



Constants:



&#x20;   from core.config import (

&#x20;       EUROLEAGUE\_SEASON,     # "2026"

&#x20;       BUDGET\_START,          # 100.0

&#x20;       TOTAL\_G, TOTAL\_F, TOTAL\_C,  # 3, 4, 3

&#x20;       DEFAULT\_MAX\_TRANSFERS, # 3

&#x20;       SERVER\_PORT\_APP,       # 5000

&#x20;       SERVER\_PORT\_CONTROL,   # 5001

&#x20;   )



\## core/logger.py



Logging setup:



&#x20;   from core.logger import get\_logger



&#x20;   log = get\_logger("my\_script", category="fetch")

&#x20;   log.info("Ξεκίνησε")

&#x20;   log.warning("Κάτι ύποπτο")

&#x20;   log.error("Σφάλμα!")



Γράφει σε:



\- logs/<category>/<name>.log (rotation: 5MB, 3 backups)

\- Console (stdout)



Κατηγορίες: fetch, train, convert, server, general



\## core/loaders.py



JSON/JS helpers:



&#x20;   from core.loaders import load\_json, save\_json, load\_js\_data, save\_js\_data



&#x20;   # JSON

&#x20;   data = load\_json(DATA\_RAW / "injuries.json")

&#x20;   save\_json(DATA\_PROC / "out.json", data)



&#x20;   # JS data files (const X = {...};)

&#x20;   var\_name, data = load\_js\_data(APP\_JS\_DATA / "player\_predictions.js")

&#x20;   save\_js\_data(APP\_JS\_DATA / "out.js", "PLAYER\_DATA", data)



\## core/team\_mapping.py



Hardcoded mapping 20 ομάδων:



&#x20;   from core.team\_mapping import FULL\_TO\_SHORT, HISTORICAL, ALIASES



&#x20;   FULL\_TO\_SHORT\["PANATHINAIKOS AKTOR ATHENS"]  # -> "PAN"



Τρέξε το για να γράψεις data/raw/team\_mapping.json:



&#x20;   py core/team\_mapping.py



\## core/optimize/



MILP Optimizer (PuLP).



&#x20;   from core.optimize import (

&#x20;       Player, Coach, CurrentTeam, OptimizerInput,

&#x20;       build\_players, build\_coaches,

&#x20;       solve\_scenario, SolveResult,

&#x20;   )



&#x20;   players = build\_players()

&#x20;   coaches = build\_coaches()



&#x20;   input\_ = OptimizerInput(

&#x20;       current\_team=current,

&#x20;       max\_transfers=3,

&#x20;       scenarios=\["A", "B"],

&#x20;   )

&#x20;   results = \[]

&#x20;   for sc in input\_.scenarios:

&#x20;       results.extend(solve\_scenario(input\_, sc))



Scoring:



\- Starter: x1.0

\- Captain: x2.0

\- 6th: x1.0

\- Bench: x0.5

\- Coach: x1.0



Formation: 4G / 4F / 2C



\## Γιατί Ξεχωριστά



\- Single source of truth

\- Ανεξαρτησία: scripts τρέχουν από παντού

\- Testability

\- Καθαρή δομή



\## Σημειώσεις



\- Ποτέ hardcoded paths σε scripts

\- Πάντα from core.paths import ...

\- Logs: logs/<category>/<script>.log

\- Version: core.\_\_version\_\_ = "1.0.0"

