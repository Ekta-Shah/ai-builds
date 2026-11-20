"""No key needed. Run: python test_checker.py   Checks your stage 2 and stage 3 code."""
import csv
import os
import tempfile
from pathlib import Path

import checker_tools as c

SRC = "score_application('FactoryDesk') -> {fit: 7.5, recommendation: ADVANCE TO CALL} A03"

# Stage 2: numbers in the draft that the sources do not contain
assert c.unsupported_numbers("FactoryDesk: fit 7.5, ADVANCE TO CALL (A03)", SRC) == [], "a clean draft should return []"
assert c.unsupported_numbers("FactoryDesk fit 7.50", SRC) == [], "7.50 and 7.5 are the same number"
assert c.unsupported_numbers("Fit 9.5 and 100%", SRC) == ["9.5", "100"], "should return the unsupported numbers, sorted"
assert c.unsupported_numbers("1. FactoryDesk fit 7.5\n2. ok", SRC) == [], "list markers at the start of a line are not numbers"
print("stage 2 ok")

# Stage 3: a hold is written to held_for_review.csv
os.chdir(tempfile.mkdtemp())
c.HELD_LOG = Path("held_for_review.csv")
c.log_hold("promise", "We will invest 2 crore")
c.log_hold("hardship", "Agreed\nto extend")
rows = list(csv.reader(open("held_for_review.csv")))
assert rows[0] == ["time", "reason", "draft"], "write the header once, when the file is new"
assert len(rows) == 3 and rows[1][1] == "promise" and "\n" not in rows[2][2], "one row per hold; no line breaks in the draft"
print("stage 3 ok")
