# Day 9 — RAG Evaluation Harness

**Date:** 2026-11-11
**Focus:** Build a golden dataset and evaluation script to measure retrieval and generation quality.

## What was built
- `eval_dataset.json` — A curated dataset of 10 questions with expected facts and expected chunk IDs.
- `evaluate.py` — A script that loops through the dataset, runs the RAG pipeline, and measures:
  - **Retrieval Accuracy:** Did the retriever find at least one of the expected chunks?
  - **Answer Accuracy:** Did the LLM's answer contain all the expected key facts?
  - **Latency:** How long did each pipeline call take?
- Added a 30-second `http_options` timeout to the generator to prevent infinite hangs.
- Improved fact-matching by normalizing text (lowercase, remove punctuation).

## The Results
| Metric | Score |
|--------|-------|
| Total Questions | 10 |
| Retrieval Accuracy (Hit Rate) | 70.0% (7/10) |
| Answer Accuracy (Fact Match) | 60.0% (6/10) |
| Average Latency | 24.69s |

### Failure Analysis
1. **API Instability (Q8, Q9):** Both questions failed because Google's API returned `504 DEADLINE_EXCEEDED` on 3.8-flash and `503 UNAVAILABLE` on 3.5-flash. The fallback chain tried every model and failed gracefully.
2. **Strict Matching (Q1, Q7):** The LLM provided correct answers, but the exact string-matching eval missed them (e.g., LLM said "Angular 2, 4, and 12+" instead of "angular 2/4/12+").
3. **Hallucination Defense (Q10):** The "favorite color" trick question successfully returned a refusal, proving the grounding prompt works.

## What was proven
- The fallback chain successfully handled several `504` errors from the primary model, saving 7/10 queries.
- The evaluation harness proved the retrieval works well (70% hit rate even with API failures).
- We now have a measurable baseline to improve against (e.g., we can improve chunking to fix missing chunks).

## Tomorrow
Day 10: Move from RAG to Agents. Build an agent that can call tools (e.g., a database query or API) to answer complex requests.