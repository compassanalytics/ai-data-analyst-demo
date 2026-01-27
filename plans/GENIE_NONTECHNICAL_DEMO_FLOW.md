# Genie Non-Technical Demo Flow

**Duration:** ~18-20 minutes
**Audience:** Business users, executives, non-technical stakeholders
**Goal:** Show why data engineering matters for AI/BI tools

---

## Demo Overview

| Phase | Time | What | Why |
|-------|------|------|-----|
| **1. Hook** | 1 min | Why most AI projects fail | Grab attention |
| **2. Setup & Context** | 2 min | Show Genie interface | Orient audience |
| **3. The Failure Demo** | 5 min | Bad data → bad results | Create the "aha" moment |
| **4. The Success Demo** | 5 min | Good data → great results | Show the solution |
| **5. Knowledge Store** | 2 min | Quick look at the config | Show what makes it work |
| **6. Limitations & Transition** | 2 min | What Genie can't do | Bridge to technical demo |
| **7. Wrap-up & Compass** | 2 min | Benchmarks + value prop | Land the message |

---

## Phase 1: The Hook (1 min)

### Opening Statement

> "Everyone's buying AI tools. Gartner says 80% of AI projects fail. Let me show you why—and it's not what you think."

### Set the Stakes

> "I'm going to ask the same questions to two AI systems. Same technology. Same vendor. Same questions. Completely different results. Watch what happens."

### Why This Matters

> "By the end of this demo, you'll understand why your PoC worked great but production is struggling."

---

## Phase 2: Setup & Context (2 min)

### What to Show

1. **Open Databricks workspace**
   - Navigate to Genie in sidebar
   - Show the simple chat interface

2. **Connect to Data Source**
   - Show Unity Catalog → select tables
   - Point out the 25 table limit
   - Explain: "This is where AI meets your data"

### Key Message
> "Genie lets anyone ask questions in plain English. No SQL required. But here's the thing—the quality of answers depends entirely on the quality of your data."

---

## Phase 2: The Failure Demo - "Super Table" (5 min)

### Setup
- Use the **super_table** Genie Space (139 columns, anti-patterns)
- No SQL expressions configured
- No system prompt

### Demo Questions (Show Each Failure)

| # | Question | What Happens | Why It Fails |
|---|----------|--------------|--------------|
| 1 | "What was total revenue last month?" | Genie hesitates or picks wrong column | 7 revenue columns: `revenue`, `REV`, `net_amt`, etc. |
| 2 | "Show sales by customer segment" | Returns cryptic codes: `ENT`, `MID`, `SMB` | No documentation, meaningless to executives |
| 3 | "What was Q1 revenue?" | Returns **WRONG number** | Uses calendar Q1, not fiscal Q1 (Feb-Apr) |
| 4 | "Show only seasonal products" | Error or inconsistent results | `is_seasonal` has: 0, 1, 'Y', 'N', True, False |

### Live Demo Script

```markdown
[Open Super Table Genie Space]

"Let me show you what happens with typical enterprise data.
This is a real-world scenario - one big table with everything."

Q1: "What was total revenue last month?"

[Wait for response - likely asks for clarification or picks arbitrarily]

"See the problem? The AI found 7 columns that could be 'revenue'.
It doesn't know which one your finance team actually uses."

---

Q2: "Show sales by customer segment"

[Shows ENT, MID, SMB, IND]

"Great, the query worked! But what does 'ENT' mean?
Enterprise? Entertainment? Your CFO won't know either."

---

Q3: "What was Q1 revenue?"

[Returns a number - but it's WRONG]

"This is the dangerous failure. It confidently returned a number.
But it used January-March. Your company uses fiscal Q1: February-April.
This number is WRONG for your business context."
```

### Key Message
> "The AI isn't broken. Your data is ambiguous. And ambiguous data = wrong answers."

---

## Phase 3: The Success Demo - "Star Schema" (5 min)

### Setup
- Switch to **star_schema** Genie Space (6 clean tables)
- Proper naming, fiscal calendar in dim_date
- SQL expressions configured

### Demo Questions (Same Questions, Now Work)

| # | Question | What Happens | Why It Works |
|---|----------|--------------|--------------|
| 1 | "What was total revenue last month?" | Correct answer immediately | Single `net_amount` column |
| 2 | "Show sales by customer segment" | Enterprise, Mid-Market, Small Business | Clear labels in dim_customer |
| 3 | "What was Q1 revenue?" | Correct fiscal Q1 number | `fiscal_quarter` in dim_date |
| 4 | "Show top products by gross margin" | Works with proper calculation | SQL expression defined |

### Live Demo Script

```markdown
[Switch to Star Schema Genie Space]

"Now let's try the same questions with properly engineered data."

Q1: "What was total revenue last month?"

[Returns correct number immediately]

"One column. One source of truth. No confusion."

---

Q2: "Show sales by customer segment"

[Returns Enterprise, Mid-Market, Small Business, Independent]

"Now your CFO knows exactly what they're looking at.
Same data, but organized for human understanding."

---

Q3: "What was Q1 revenue?"

[Returns correct FISCAL Q1 number]

"This time it used fiscal Q1—February through April.
The right answer for your business reports."
```

### The Killer Question

```markdown
"Let me show you something more complex."

"Show me gross margin by product category, comparing this fiscal quarter
to the same quarter last year, for enterprise customers only"

[Watch it work with proper SQL expressions]

"That query would take an analyst 30 minutes to write.
Genie did it in 5 seconds—because the data was ready."
```

### Key Message
> "Same AI. Same questions. Completely different experience. The difference? Data engineering."

---

## Phase 5: Knowledge Store - Quick Look (2 min)

### What Made It Work? (Show Don't Explain)

Navigate to **Configure** and quickly show:

#### 1. System Prompt (30 sec)
```
"Fiscal year starts February 1st. Q1 = Feb-Apr."
"Use net_amount for all revenue questions."
```
> "We told the AI our business rules. That's why Q1 was correct."

#### 2. One SQL Expression (30 sec)
```sql
gross_margin_pct = (SUM(net_amount) - SUM(cost_amount)) / SUM(net_amount) * 100
```
> "Finance team's exact formula. Not the AI guessing."

#### 3. Sample Questions (30 sec)
> "We trained it on common question patterns. That's the engineering layer."

### The Point (30 sec)
> "This configuration took about 2 hours. Without it? You saw what happens. This is the invisible work that makes AI actually useful."

---

## Phase 6: Genie Limitations & Transition (2 min)

### What Genie Can't Do (Quick List)

> "Genie is great for what we just showed. But it can't:"

- Query across systems (Salesforce + warehouse + APIs together)
- Take actions (send emails, update records, trigger workflows)
- Multi-step reasoning ("analyze this, then alert me if X")
- Remember yesterday's conversation
- Handle 25+ tables

### The Transition (30 sec)

> "For that, you need agentic AI—AI that can use tools, take actions, and orchestrate workflows. Let me show you what that looks like..."

---

## Phase 7: Wrap-up & Compass Value Prop (2 min)

### The Numbers (Softened)

| Metric | Value | Context |
|--------|-------|---------|
| **Benchmark Accuracy** | 86-91% | Clean academic datasets (Spider 1.0) |
| **Real-World Accuracy** | Single digits | Typical enterprise data without engineering |
| **The Gap** | **80+ points** | This is the data engineering deficit |

### The Quote to Land

> "The gap between benchmark accuracy and real-world accuracy isn't about AI capability—it's about data engineering. The AI is ready. Your data usually isn't."

### Compass Value Prop

> "This is what Compass does. In 8-10 weeks, we take you from 'the demo worked' to 'production is reliable.' We build the data layer, the knowledge store, the governance—everything you just saw that made the difference."

### Close

> "Questions on Genie? [Pause] Alright, now let me show you what happens when we go deeper—custom AI agents that can do things Genie can't..."

---

## Pre-Demo Checklist

### Data Setup
- [ ] Super table uploaded to Unity Catalog
- [ ] Star schema tables uploaded to Unity Catalog
- [ ] Column descriptions added (for star schema)

### Genie Spaces
- [ ] "Super Table Demo" space created (no config)
- [ ] "Star Schema Demo" space created (fully configured)
- [ ] SQL warehouse assigned to both

### Star Schema Configuration
- [ ] System prompt written
- [ ] SQL expressions added (5-10)
- [ ] Sample questions configured
- [ ] All demo questions tested 3+ times

### Backup Plan (CRITICAL - AI Can Surprise You)
- [ ] Screenshots of all expected results saved locally
- [ ] Screen recording of successful dry-run as fallback
- [ ] Alternative questions tested and documented
- [ ] Network connectivity verified (have mobile hotspot ready)
- [ ] Test exact demo questions 10+ times before live
- [ ] Know which failures are "good" (shows the point) vs "bad" (breaks demo)

---

## Troubleshooting Tips

| Issue | Quick Fix |
|-------|-----------|
| Genie asks for clarification | This is actually good for the demo—shows the ambiguity problem |
| Query takes too long | Reduce data size, use serverless warehouse |
| Wrong answer on star schema | Check SQL expressions, verify column names |
| "I don't have access to that data" | Verify Unity Catalog permissions |

---

## Demo Risk Mitigation

### "Good" Failures (Actually Help Your Point)
- Genie asks "which revenue column?" → Perfect, shows ambiguity
- Returns cryptic codes → Shows documentation gap
- Takes a while to respond → "Even AI struggles with messy data"

### "Bad" Failures (Break the Demo)
- Complete error/crash → Switch to screenshots
- Star schema also fails → SQL expressions misconfigured, fix live or use backup
- Network issues → Mobile hotspot or pre-recorded video

### Recovery Phrases
- If something unexpected happens: "This actually proves my point—AI is unpredictable on unprepared data"
- If star schema fails: "Let me show you what this should look like" [switch to screenshots]
- If running long: Skip Knowledge Store deep dive, go straight to limitations

---

## Appendix: Key Files

| File | Location | Purpose |
|------|----------|---------|
| Star Schema Generator | `dataset_generators/star_schema_generator.py` | Creates good data |
| Super Table Generator | `dataset_generators/super_table_generator.py` | Creates bad data |
| Failure Scenarios | `dataset_generators/genie_failure_scenarios.py` | Demo script details |
| Generated Data | `dataset_generators/data/` | Parquet files to upload |

---

## Post-Demo Notes

After each demo run, note:
- Questions that worked well
- Questions that needed adjustment
- Audience reactions/questions
- Timing (actual vs planned)

This helps refine the demo for future workshops.
