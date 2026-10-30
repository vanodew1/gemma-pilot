# Keyword-search pilot results

55 SWE-bench issues (psf/requests, pallets/flask). Hit@k = a file the real fix touched is in the top k.

| Method | Hit@1 | Hit@3 | Hit@5 | Recall@5 | Mean lines opened (top 5) |
|---|---|---|---|---|---|
| B0 random | 9% | 24% | 35% | 27% | 1,225 |
| B1 BM25 (whole files) | 58% | 91% | 95% | 89% | 2,999 |
| K0 keyword search, no def bonus | 65% | 91% | 98% | 93% | 1,082 |
| K1 keyword search | 69% | 91% | 98% | 93% | 1,079 |
| K1 + retry clues | 69% | 96% | 98% | 94% | 1,402 |
