# Report Analisi Benchmark (Auto-generato)

Generato: 2026-04-19 16:19:04

## Sintesi Modello

| Model | Tasks | Ctrl F1 | DNA F1 | Delta | 95% CI Delta | Wins/Losses/Ties | Wilcoxon p exact | Wilcoxon p approx* |
|---|---:|---:|---:|---:|---|---:|---:|
| claude-haiku-4-5 | 1 | 0.333 | 0.714 | +0.381 | [+0.381, +0.381] | 1/0/0 | 0.500 | 0.159 |
| deepseek-chat | 6 | 0.420 | 0.497 | +0.077 | [-0.018, +0.198] | 4/1/1 | 0.156 | 0.112 |
| gemini-2.5-flash | 5 | 0.597 | 0.724 | +0.127 | [+0.049, +0.190] | 4/1/0 | 0.062 | 0.040 |
| gemini-2.5-pro | 5 | 0.596 | 0.690 | +0.094 | [-0.020, +0.207] | 3/2/0 | 0.156 | 0.112 |

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
| claude-haiku-4-5 | django__django-14480 | +0.381 | 0.333 | 0.714 |
| deepseek-chat | django__django-11808 | +0.346 | 0.203 | 0.549 |
| gemini-2.5-pro | django__django-14480 | +0.277 | 0.477 | 0.755 |
| gemini-2.5-flash | django__django-13495 | +0.215 | 0.524 | 0.738 |
| gemini-2.5-pro | django__django-11991 | +0.189 | 0.538 | 0.727 |
| gemini-2.5-flash | django__django-14480 | +0.176 | 0.547 | 0.723 |
| gemini-2.5-flash | django__django-11991 | +0.167 | 0.489 | 0.656 |
| deepseek-chat | django__django-14480 | +0.138 | 0.548 | 0.686 |
| gemini-2.5-pro | django__django-12508 | +0.105 | 0.783 | 0.888 |
| gemini-2.5-flash | django__django-12508 | +0.091 | 0.842 | 0.933 |

## Task con regressione

| Model | Task | Delta F1 | Ctrl | DNA |
|---|---|---:|---:|---:|
| deepseek-chat | django__django-13495 | -0.084 | 0.448 | 0.363 |
| gemini-2.5-pro | django__django-13495 | -0.082 | 0.914 | 0.832 |
| gemini-2.5-pro | django__django-11808 | -0.021 | 0.268 | 0.247 |
| gemini-2.5-flash | django__django-11808 | -0.015 | 0.584 | 0.569 |
