# Report Analisi Benchmark (Auto-generato)

Generato: 2026-04-21 11:38:09

## Sintesi Modello

| Model | Tasks | Ctrl F1 | DNA F1 | Delta | 95% CI Delta | Wins/Losses/Ties | Wilcoxon p exact | Wilcoxon p approx* |
|---|---:|---:|---:|---:|---|---:|---:|
| deepseek-chat | 10 | 0.509 | 0.680 | +0.171 | [+0.105, +0.245] | 10/0/0 | 0.001 | 0.003 |

## Insight Operativi

- `delta_f1_mean > 0` indica vantaggio medio CodeDNA.
- `wins/losses` misura robustezza per-task (non solo media).
- CI bootstrap aiuta a comunicare incertezza su campioni piccoli.
- Wilcoxon one-tailed segue ipotesi H1: CodeDNA > Control.
- `p approx` e calcolato con normal approximation (allineato allo script benchmark del repo).
- `p exact` e il valore combinatorio esatto (piu conservativo con N piccoli).
- Per modelli/task con N molto piccolo (es. n=1), il p-value va interpretato solo come indicazione preliminare.

## Top Task Delta (positivi)

| Model | Task | Delta F1 | Ctrl | DNA |
|---|---|---:|---:|---:|
| deepseek-chat | django__django-16263 | +0.409 | 0.281 | 0.690 |
| deepseek-chat | django__django-13121 | +0.283 | 0.606 | 0.889 |
| deepseek-chat | django__django-11808 | +0.255 | 0.316 | 0.571 |
| deepseek-chat | django__django-11400 | +0.199 | 0.456 | 0.656 |
| deepseek-chat | django__django-15629 | +0.199 | 0.172 | 0.370 |
| deepseek-chat | django__django-11532 | +0.110 | 0.456 | 0.565 |
| deepseek-chat | django__django-11138 | +0.107 | 0.766 | 0.873 |
| deepseek-chat | django__django-13495 | +0.066 | 0.857 | 0.923 |
| deepseek-chat | django__django-11883 | +0.064 | 0.841 | 0.905 |
| deepseek-chat | django__django-14480 | +0.022 | 0.336 | 0.357 |

## Task con regressione

| Model | Task | Delta F1 | Ctrl | DNA |
|---|---|---:|---:|---:|
