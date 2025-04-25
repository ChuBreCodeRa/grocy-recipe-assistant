
# AI Evaluation Strategy

This document outlines how AI-powered components of the Grocy AI Recipe Assistant will be evaluated for accuracy, consistency, and trustworthiness.

**Current Status: Evaluation strategy defined; system not yet implemented.**

---

## Goals

- Ensure ingredient classification is accurate and reproducible.
- Validate review parsing produces correct effort/flavor/sentiment labels.
- Maintain user trust through reliable suggestions and learning behavior.

---

## Evaluation Targets

### 1. Ingredient Classification

| Metric         | Method |
|----------------|--------|
| Accuracy       | Manually label 10–20 recipes and compare AI output. |
| Confidence Correlation | Check if high-confidence predictions are more accurate. |
| Consistency    | Re-test same prompt over time, confirm output stability. |
| Format Correctness | Ensure valid JSON format per prompt spec. |

### 2. Review Parsing

| Metric         | Method |
|----------------|--------|
| Effort Tag Accuracy | Manually score 25 mini-reviews and compare GPT output. |
| Flavor Tag Relevance | Human evaluate if tags match user text (e.g. “too spicy” → “spicy”). |
| Sentiment Alignment | Compare AI sentiment vs user rating. |
| Fallback Detection | Log and review any malformed or empty responses. |

### 3. Preference Model Learning

| Metric              | Method |
|---------------------|--------|
| Preference Drift Quality | After 10 reviews, observe if preferences move in expected direction. |
| Undesired Bias      | Ensure user profile doesn't overfit on one-off meals. |
| Profile Decay Test  | Observe if stale preferences decay naturally over 30-day simulation. |

---

## Test Dataset (Planned)

- 10–20 example recipes across categories (easy, moderate, spicy, bland, etc.)
- 25–50 synthetic mini-reviews seeded with clear flavor and effort signals
- Manual labels created by developer during testing

---

## Evaluation Plan

- Store evaluation set in `/tests/data/ai_evaluation_set.json`
- Create notebook or script to run batch evaluations and compare output to ground truth
- Log errors to structured file for future prompt tuning

---

## Related Docs

- [[PROMPTS]]
- [[USER_REQUIREMENTS]]
- [[DECISIONS]]
- [[DB_SCHEMA]]
