## Symbolica Benchmark Suite for Database Performance Troubleshooting

### 🎯 Goal

Demonstrate that Symbolica improves reasoning accuracy, traceability, and speed of diagnosis over LLM-only agents in realistic, domain-specialized incident scenarios.

### 📂 Scope of Troubleshooting Scenarios

This benchmark suite includes a diverse set of performance-related incidents drawn from real-world infrastructure logs and expert postmortems.

| Scenario Type           | Example Question                        | Symbolica Role                                             |
| :--------------------- | :-------------------------------------- | :--------------------------------------------------------- |
| High CPU Usage         | “Why is my CPU at 98%?”                 | Trace symbolic rules over metrics and plans                |
| Query Slowness         | “Why is this query taking 5 minutes?”    | Combine metric triggers and explain plan logic             |
| Lock Contention        | “Why is the application hanging?”        | Symbolic diagnosis based on lock/latch data                |
| Buffer Pool Bottlenecks| “Why is IO spiking?”                     | Detect page churn, dirty pages, prefetch lags              |
| Disk IO Saturation     | “Why is disk write time increasing?”     | Trace cause via spill patterns, temp tables                |
| Config Missteps        | “Why is memory pressure so high?”        | Detect misconfigured limits, overallocated pools           |

Each case includes:

- Raw metric dumps (JSON)
- Logs (optional)
- Explain plans (if applicable)
- Ground truth cause (annotated by SMEs)

### 🧪 Agent Comparisons

We compare:

| System             | Description                                                                 |
| :----------------- | :-------------------------------------------------------------------------- |
| Baseline LLM Agent | ReAct-style agent using only prompt-based reasoning and tool outputs         |
| Symbolica Agent    | Same LLM stack plus symbolic rule evaluation layer with human-readable traces|

### ✅ Evaluation Criteria

| Metric             | Definition                                             | Target Improvement                 |
| :----------------- | :----------------------------------------------------- | :--------------------------------- |
| RCA Accuracy       | Correct root cause classification vs. SME ground truth | ≥ 25% improvement                  |
| Hallucination Rate | Number of unsupported claims in final answer           | ≤ 50% of baseline agent            |
| Trace Audibility   | Can a human verify reasoning path in <30 s?            | ≥ 90% of Symbolica outputs         |
| Rule Authorability | Avg time for SME to author/modify rules                | ≤ 15 min per rule                  |

**Bonus (optional):**

- User Trust Score (Likert scale feedback from SMEs)
- Inference Latency (+X ms from rule engine)

### 🧪 Dataset Plan

| Component   | Detail                                                        |
| :---------- | :------------------------------------------------------------ |
| Size        | ≥ 100 real-world, anonymized incident samples                 |
| Labeling    | Ground truth RCAs labeled by 3+ SMEs (with inter-annotator agreement) |
| Licensing   | Open-sourced under Apache 2.0 or similar                      |
| Availability| Bundled with Symbolica repo and benchmark harness             |

### 💬 Example Evaluation Prompt

“Your CPU was at 98% from 3pm to 3:30pm. Given the metrics and logs, explain why this happened.”

- **LLM-only agent:** Responds based on prompt memory and RAG.
- **Symbolica agent:** Runs rule inference on fact store → returns JSON trace → LLM reformulates into natural answer.

## Works Cited

1. Symbolica Benchmark Suite for Database Performance Troubleshooting.