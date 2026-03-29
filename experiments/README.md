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
                                              