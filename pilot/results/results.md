# Keyword-search pilot results

55 SWE-bench issues (psf/requests, pallets/flask). Hit@k = a file the real fix touched is in the top k.

| Method | Hit@1 | Hit@3 | Hit@5 | Recall@5 | Mean lines opened (top 5) |
|---|---|---|---|---|---|
| B0 random | 9% | 24% | 35% | 27% | 1,225 |
| B1 BM25 (whole files) | 58% | 91% | 95% | 89% | 2,999 |
| K0 keyword search, no def bonus | 65% | 91% | 98% | 93% | 1,082 |
| K1 keyword search | 69% | 91% | 98% | 93% | 1,079 |
| K1 + retry clues | 69% | 96% | 98% | 94% | 1,402 |
| K2 Gemma 12B keywords only | 80% | 93% | 96% | 90% | 1,030 |
| K1 + K2 Gemma 12B keywords | 73% | 91% | 95% | 89% | 1,212 |
| K2 Gemma E4B keywords only | 69% | 85% | 93% | 88% | 795 |
| K1 + K2 Gemma E4B keywords | 71% | 91% | 96% | 91% | 1,084 |
| K2 Gemma E2B keywords only | 71% | 80% | 93% | 87% | 887 |
| K1 + K2 Gemma E2B keywords | 69% | 87% | 98% | 92% | 1,151 |

Gemma call cost per issue (time and tokens only for replies cached with timing).

| Model | Replies with no usable keywords | Mean keywords | Mean seconds | Mean output tokens |
|---|---|---|---|---|
| 12B | 0/55 | 12.4 | n/a | n/a |
| E4B | 0/55 | 9.2 | 1.1 | 88.0 |
| E2B | 0/55 | 9.8 | 0.4 | 93.1 |
