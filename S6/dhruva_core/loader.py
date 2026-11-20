import csv
from pathlib import Path

HERE = Path(__file__).parent


def load(path=None):
    path = path or HERE / "data" / "applications.csv"
    apps = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            row = {k.strip(): v for k, v in row.items()}
            apps.append({
                "id": row["id"],
                "name": row["name"],
                "stage": row["stage"],
                "sector": row["sector"],
                "hq": row["hq"],
                "founders": row["founders"],
                "model": row["model"],
                "round_size_cr": row["round_size_cr"],
                "deck": (HERE / "decks" / (row["id"] + ".txt")).read_text(),
            })
    return apps
