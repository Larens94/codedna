Come usarlo:                                                                                        
                                                                                                      
  # Terminale 1 — avvia l'esperimento                                                                 
  cd experiments                                                                                      
  python run_experiment.py                                                                            
                                                                                                      
  # Terminale 2 — apri la dashboard MENTRE l'esperimento gira                                         
  python visualizer/dashboard.py                                                                      
                                                                                                      
  Reset:                                                                                              
  python run_experiment.py --reset           # cancella tutto
  python run_experiment.py --clean-run run_20260329_153000  # solo un run
  python run_experiment.py --list-runs       # lista tutti i run
                                                                                                      
  Cosa mostra la dashboard:
  - Colonna cyan [A] = team con annotation protocol                                                   
  - Colonna yellow [B] = team con standard practices                                                  
  - Per ciascuna: file creati + coverage, agent: entries timeline, message: channel, session events
  - Stats bar in cima con coverage % in tempo reale                                                   
                                                                                                      
  Differenza tra A e B: solo le istruzioni degli agenti — zero menzione del protocollo di annotazioni 
  nel branch B.                                                                                       
                                              



Condition A ancora in corso (17 file, B non ancora partita). Ecco i comandi per monitorare tu:

  Terminale 1 — log live:
  tail -f /Users/fabriziocorpora/Desktop/automation-lab/dynamic-bi-factory/codedna/experiments/runs/run_20260329_171502/run.log

  Terminale 2 — dashboard:
  cd /Users/fabriziocorpora/Desktop/automation-lab/dynamic-bi-factory/codedna/experiments
  python3.11 visualizer/dashboard.py --run run_20260329_171502

  Terminale 3 — conteggio file in tempo reale (opzionale):
  watch -n 5 'echo "A: $(find .../runs/run_20260329_171502/a -name "*.py" | wc -l) | B: $(find
  .../runs/run_20260329_171502/b -name "*.py" | wc -l)"'

  Il run attivo è run_20260329_171502. Quando A finisce vedrai nel log [A] Task completed e B parte
  subito dopo.