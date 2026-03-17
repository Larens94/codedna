# CodeDNA Benchmark — Annotation Levels

## Livelli applicati

| Livello | Applicato | Dove |
|---------|-----------|------|
| **L1** — Module Header | ✅ Sì | Tutti i 41 file ground truth + 12 extra navigazione |
| **L2** — Method Docstring | ✅ Sì | 8 file (task con navigazione intra-file critica) |
| **L3** — Semantic Naming | ❌ No | Vedi nota sotto |

## Nota su L3 (Semantic Naming)

L3 non è applicato in questo benchmark perché:

1. **Codice di terze parti** — I file annotati sono codice sorgente Django. Rinominare le variabili (`data` → `list_dict_users_from_db`) altererebbe il codice e romperebbe le patch SWE-bench che verificano nomi specifici.

2. **Scope del benchmark** — Il benchmark misura la capacità di navigazione multi-file (trovare i file giusti), non la comprensione intra-funzione delle variabili. L1 e L2 coprono completamente questo scope.

3. **Difendibilità accademica** — Un rename massivo di variabili Django sarebbe indifendibile in peer review.

## Lavoro futuro: Benchmark L3

Un test interessante sarebbe fare **migration code con L3** applicato:
- Forkare i file Django GT
- Applicare semantic naming alle variabili critiche
- Rieseguire il benchmark con L1+L2+L3 vs L1+L2
- Misurare se L3 migliora la velocità/accuratezza di comprensione del codice

Questo richiede un benchmark separato e un setup specifico per non rompere le patch SWE-bench.

## Copertura per task

| Task | GT files | L1 | L2 | Copertura |
|------|----------|----|----|-----------|
| T14480 XOR | 7 | 7 | 3 | 100% |
| T13495 Trunc | 7 | 7 | 3 | 100% |
| T12508 dbshell | 8 | 8 | 1 | 100% |
| T11991 INCLUDE | 9 | 9 | 1 | 100% |
| T11808 __eq__ | 10 | 10 | 0 | 100% |
| **Totale** | **41** | **41** | **8** | **100%** |
