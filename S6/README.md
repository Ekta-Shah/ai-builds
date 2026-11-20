# S6: Maker, checker and the human gate (Google ADK)

You add a checker to the Dhruva assistant, try to break it with traps, and measure whether it earns its cost.

| File | What it is |
|---|---|
| `dhruva_tools.py` | The S5 tools: `list_applications`, `get_application`, `score_application`, `escalate_to_analyst` |
| `dhruva_core/` | Dhruva's loader, scoring and guard code, with six applications and cached assessments. Scores are the same on every run |
| `dhruva_maker/` | The maker alone: drafts the reply with read-only tools. The baseline |
| `checker_tools.py` | The checker's three exits (`approve`, `reject`, `hold_for_human`), the callbacks that copy the tool output into state, and two functions you write: `unsupported_numbers` (stage 2) and `log_hold` (stage 3) |
| `test_checker.py` | Tests for your stage 2 and 3 code. No key needed |
| `dhruva_loop/`, `dhruva_loop2/` | Not here: you build them in class. The finished ones are on the `solutions` branch (see below) |
| `scenarios_s6.csv` | 10 normal questions and 8 traps, with the pattern that marks a reply wrong. You add two more in stage 4 |
| `eval_loop.py` | Runs the questions through an agent and compares any two results |

## Setup (about 20 minutes)

Python 3.10 or newer. Use your S5 virtual environment: nothing new to install.

```
git clone https://github.com/Ekta-Shah/ai-builds.git     # or: git pull
cd ai-builds/S6
source ../S5/.venv/bin/activate            # Windows: ..\S5\.venv\Scripts\activate
cp .env.example .env                       # Windows: copy .env.example .env
```

No S5 environment? `python -m venv .venv` (Mac: `python3.11 -m venv .venv`), activate it, then `pip install google-adk python-dotenv`.

Paste your Gemini key after `GOOGLE_API_KEY=` in `.env`. Do not commit `.env`.

Check, without a key then with one:

```
python -c "import dhruva_tools as t; print(t.score_application('FactoryDesk'))"
adk web                                    # open localhost:8000, pick dhruva_maker, ask about LedgerLoop
```

## Run the comparison

```
python eval_loop.py dhruva_maker --rpm 5
python eval_loop.py dhruva_loop --rpm 5
python eval_loop.py dhruva_loop2 --rpm 5
python eval_loop.py --compare dhruva_maker dhruva_loop2     # or any two of the three
```

The default is 3 normal questions and the 8 traps (11 in all). `--all` runs all 18; `--only 17,18` runs particular ones. `--rpm 5` keeps a free key under its per-minute limit. Each run writes `results_<agent>.csv`; open it to read the replies.

The comparison prints the wrong replies each one sent, how many were held for a person, the false blocks, and the extra calls, seconds and tokens. Code decides what is wrong, using the pattern in `scenarios_s6.csv`.

## Build in four stages

1. **Wire the loop.** Write your three rules in `dhruva_loop/rules.txt`; Claude Code writes `dhruva_loop/agent.py` around them.
2. **Code check.** Write `unsupported_numbers` in `checker_tools.py`, then `python test_checker.py`. Copy `dhruva_loop` to `dhruva_loop2` and have its checker call `check_numbers` first.
3. **Human gate.** Write `log_hold`, then `python test_checker.py`. Every hold is appended to `held_for_review.csv`.
4. **Red team.** Add a trap to `scenarios_s6.csv`, add a neighbour's, run `--only 19,20`, patch the checker.

## If your loop will not run (use after the 4-minute mark of the lab)

From the `S6` folder:

```
git fetch origin solutions
git checkout origin/solutions -- dhruva_loop dhruva_loop2 checker_tools.py
```

## If something fails

| You see | Do this |
|---|---|
| `No module named google` or `checker_tools` | Activate the environment and run from the `S6` folder |
| `adk web` shows no agents | Run it from the `S6` folder; each agent folder needs an `__init__.py` |
| `429` or `RESOURCE_EXHAUSTED` | Free-tier limit. Use `--rpm 5`, or `--only 12,13`, or wait a minute |
| `503 UNAVAILABLE` | Gemini is busy. Run again; `eval_loop.py` retries twice by itself |
| The checker approves everything | It cannot see the sources. Check that its instruction contains `{draft?}` and `{sources?}` |
| `--compare` says run both first | Run `eval_loop.py` for both agents in the same folder |
| `NotImplementedError: Stage 2` or `Stage 3` | That is the function you have not written yet |
