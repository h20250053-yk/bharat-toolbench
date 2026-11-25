"""Gujarati (gu) for the 20-tool batch T101-T200. Merged into benchmark/batch_gujarati.py (same conventions as there).

Exception to 'the only place where Gujarati text lives': for this batch the Gujarati drafts were written in the same table as the
other four languages (benchmark/batch_t101_t200.py, column `gu`) so every marker is defined once for all five languages; this module
only re-exports them under the Gujarati batch interface (IDS, QUERIES, MARKERS, FLAGS).
PNRs, train ids, class codes, amounts and times use ASCII digits / Latin letters, separated from Gujarati suffixes by a space; passenger
names stay Latin; station names use the frozen Gujarati aliases. Loan words used every day by Gujarati railway users are kept
(તત્કાલ, બોર્ડિંગ સ્ટેશન, પ્લેટફોર્મ, TDR, લોઅર બર્થ, વેઇટિંગ લિસ્ટ, કેન્સલ).
"""
from __future__ import annotations

from .batch_t06_t15 import F, OK  # noqa: F401  (OK kept for the shared batch interface)
from .batch_t101_t200 import BATCH_IDS, GU_MARKERS, GU_QUERIES, RISK

IDS = list(BATCH_IDS)
QUERIES: dict[str, str] = dict(GU_QUERIES)
MARKERS: dict[str, dict[str, list[str]]] = {t: dict(m) for t, m in GU_MARKERS.items()}
_KEEP = ("PNRs, passenger names, train ids, class codes, amounts and times use ASCII digits / Latin letters, separated from Gujarati "
         "suffixes by a space; station names use the frozen Gujarati aliases.")
_NOTE = "Polite imperatives (કરો / નોંધાવો / જણાવો); railway loan words kept as users say them; the speaker stays gender-neutral."
FLAGS: dict[tuple[str, str], dict[str, dict]] = {
    (t, "gu"): dict(potential_ambiguity=F(True, RISK[t]), unnatural_wording=F(True, _NOTE),
                    constraint_risk=F(True, "Reviewer must confirm: " + RISK[t]), notes=F(False, _KEEP))
    for t in IDS
}
