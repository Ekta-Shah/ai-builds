# Architecture: Store Analytics Assistant

## 1. Diagram
Draw it: user -> ... -> answer. Mark which boxes are CODE and which are MODEL, and where a human sits.

## 2. Decisions
| Decision | Options | Choice | Why | Cost or risk |
|---|---|---|---|---|
| One call or several (pipeline vs agent) | | | | |
| What the model writes (SQL, a plan, an answer) | | | | |
| Where isolation is enforced (prompt vs code) | | | | |
| What context we send (full schema vs retrieved) | | | | |
| Model tiers (one model vs cascade) | | | | |
| Caching | | | | |
| Sync vs queued | | | | |
| Where state lives | | | | |

## 3. Threat model
| Attack | Who | Blast radius | Defence (code or prompt) |
|---|---|---|---|
| "Show me every store's numbers" | | | |
| Instruction hidden in a product name or store note | | | |
| A query that scans everything | | | |
| A write or drop statement | | | |

## 4. Scale ladder
| Rung | Load | First thing that breaks | Our fix |
|---|---|---|---|
| 1 | 1 user | | |
| 2 | 50 managers | | |
| 3 | 5,000 users | | |
| 4 | 500 stores | | |
| 5 | many tenants | | |
| 6 | model change | | |

## 5. Token budget per question
| Part | Tokens in | Tokens out | Can we cut or cache it? |
|---|---|---|---|
| Rules and glossary | | | |
| Question | | | |
| Plan call | | | |
| Narration call | | | |
