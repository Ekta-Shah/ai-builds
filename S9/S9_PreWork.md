# S9 pre-work: get the production folder working

MESA PGP Cohort 4 | Term 2: Advanced AI | Session 9 | about 40 minutes

In S8 you built a store analytics assistant. In S9 you make it safe to run for real managers: a spend cap, a release switch, a monitoring report and a defence you have tested by attacking it. This page has two parts: what you need to know (15 minutes) and the setup (25 minutes). If a step fails, bring the error message to class.

## Part A: What you need to know

### 1. Cost depends on tokens, and tokens add up
A token is a word-piece. A model charges for tokens in (what you send) and tokens out (what it writes), at different prices, per million tokens. Cost per question = tokens in times price in, plus tokens out times price out. Monthly cost = cost per question times questions per day times 30. At 5 times and 50 times the volume the bill multiplies, and some things make it grow faster: retries, longer conversations, and more context in every call.

### 2. A ceiling is a decision you make before you look at the bill
A cost ceiling is the most you are willing to spend a month. The flip point is the volume at which the bill reaches it. Past that point you must change something: send less, cache, use a cheaper model, or move the ceiling.

### 3. Shipping an agent is changing a setting, not copying a website
The model name, the prompt and the limits live in a config file, so a change needs no new code. Secrets such as your API key live in environment variables, never in the file or in git. A release sends the new version to a small share of users (say 10%), chosen by a hash of the user id so each person always sees the same version. A rollback sets that share back to 0.

### 4. You monitor four things, and each needs an owner
Usage (are people using it?), cost (rupees per question), reliability (errors and slow replies) and quality (how often it could not answer). A metric with a threshold and no named person is a number nobody reads. A log must never hold personal data or the text of what people typed.

### 5. Security means the tool cannot do more than its user should
Least privilege: it only reads, and only the user's own stores. A prompt can be argued with; a database connection that cannot see the rows cannot. Prompt injection is text that tries to give the model new orders, from the user or hidden inside data.

### 6. A little SQL
You will read a log with SQL: `SELECT col FROM table WHERE ... GROUP BY ...`. If it is rusty, run S3's SQL warm-up or ask in class.

## Part B: Setup

### Step 1: The S8 folder must work (5 minutes)
Check `python make_data.py` was run in `ai-builds/S8` and that `retail.db` exists there. If you did not finish S8, pull the folder and run it now: it takes a few seconds.

### Step 2: Get the S9 folder (5 minutes)
```
git clone https://github.com/Ekta-Shah/ai-builds.git       # or: git pull inside ai-builds
cd ai-builds/S9
```

### Step 3: Environment and key (10 minutes)
```
source ../S8/.venv/bin/activate        # Windows: ..\S8\.venv\Scripts\activate
pip install google-genai pydantic
cp .env.example .env                   # Windows: copy .env.example .env
```
Paste your key after `GOOGLE_API_KEY=`, with no quotes or spaces. `.env` is not uploaded to git.

### Step 4: Build the usage log and run the tests (5 minutes)
```
python make_usage_log.py
python test_prod.py
```
You should see `stage 1: not written yet` ... `stage 4: not written yet`. That is correct: you write these in class.

## Part C: Self-check

1. Tokens in cost 9 rupees per million, tokens out cost 36. A question uses 650 in and 165 out. What does it cost? (About Rs 0.0118.)
2. At 400 questions a day, what does a month cost? (About Rs 141.)
3. Why hash the user id for a rollout instead of picking at random each time?
4. Name two things that must never go in a log.
5. Why is "the prompt says only show store S03" not enough?

**Answers.** 1: (650 x 9 + 165 x 36) / 1,000,000 = 0.01179. 2: 0.01179 x 400 x 30 = about 141. 3: So each user always sees the same version; you can compare versions fairly and users are not confused. 4: Personal data (phone, email, ID numbers) and the text of what people typed. 5: A prompt is an instruction a model may or may not follow; access has to be enforced by code.

## Do not do

- Do not write the stage functions before class.
- Do not run `attack.py` before class: a free key allows few requests a day and class needs them.
- Do not share or paste your key.

## Bring to class

A laptop with the S9 folder, the environment working and the key in `.env`, your S8 cost per question, and your answers to the self-check.
