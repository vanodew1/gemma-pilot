# Selector and memory-probe check (55 pilot issues; code check only)

Gold in pool = a gold file is among the 5 candidates, the ceiling for S1/S2.

K1/K2 = keyword ranking alone. N = K2 with files the model named itself moved first (no extra call). S1/S2 = Gemma orders the top 5 of K1/K2 from file outlines. P = file named from the issue alone.

| Model | K1@1 | S1@1 | S1@3 | S1 gold in pool | K2@1 | N@1 | S2@1 | S2@3 | S2 gold in pool | P | unparsed picks | mean s per pick |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E2B | 69% | 78% | 89% | 98% | 71% | 69% | 78% | 89% | 93% | 38% | 0/110 | 0.7 |
| E4B | 69% | 80% | 96% | 98% | 69% | 67% | 76% | 89% | 93% | 64% | 0/110 | 0.4 |
| 12B | 69% | 85% | 96% | 98% | 80% | 76% | 78% | 93% | 96% | 64% | 0/110 | 1.0 |
