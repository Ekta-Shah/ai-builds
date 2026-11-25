# Build Day pre-work: get the folder working before class

MESA PGP Cohort 4 | Term 2: Advanced AI | Build Day | about 30 minutes

Build Day is three hours. We start from one sentence, write the requirements and the architecture, and then build the product with a coding agent. The setup below must work before you arrive, or you will lose the first hour. If a step fails, bring the error message to class.

## Step 1: Get the folder (5 minutes)

```
git clone https://github.com/Ekta-Shah/ai-builds.git
cd ai-builds/BuildDay
```

Already cloned it? Run `git pull` in the `ai-builds` folder, then `cd BuildDay`.

## Step 2: Python environment (10 minutes)

You need Python 3.10 or newer (`python --version`). On a Mac, use `python3.11` if `python` is older.

```
python -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install google-genai pydantic
```

## Step 3: Your Gemini key (5 minutes)

Copy the example file and paste your key after `GOOGLE_API_KEY=`, with no quotes or spaces. Get a free key at https://aistudio.google.com/apikey.

```
cp .env.example .env                  # Windows: copy .env.example .env
```

The key lives only in `.env`. Never paste it in a chat, a note, or a commit.

## Step 4: Build the database (2 minutes)

```
python make_data.py
```

You should see: `223702 sales lines`. It creates `retail.db`, which is not uploaded to git.

## Step 5: Install a coding agent (5 minutes)

Install Claude Code (or the agent you use) and check that it starts in the `BuildDay` folder. We use it to write the code in class. You are the engineer: you decide, it types.

## Step 6: Think about the problem (5 minutes)

On paper, answer these. There are no right answers:

1. A store manager asks an AI "how were sales last month?" What could go wrong with the answer?
2. What should an AI never be allowed to do with a database?
3. How would you check that the AI's numbers are right?

## Do not do

- Do not build anything before class. We build together, and the discussion is the point.
- Do not read the solutions branch.
- Do not share or paste your key.

## Bring to class

A laptop with the `BuildDay` folder working, your key in `.env`, and your answers to step 6.
