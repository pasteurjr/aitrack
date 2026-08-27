---                                               
  Terminal 1 — Backend (Flask API + Socket Server + Dirijabem)                                                                                                                          
                                                                                                                                                                                        
  cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr                                                                                                                                 
  python run.py                                                                                                                                                                         
  Sobe 3 serviços em threads:                                                                                                                                                           
  - Socket TCP na porta 9000 (recebe trackers)                                                                                                                                          
  - API Flask na porta 5009 (serve frontend)                                                                                                                                            
  - Replay manager do Dirijabem                                                                                                                                                         
                                                                                                                                                                                      
  ---                                                                                                                                                                                   
  Terminal 2 — Frontend AITrack (mapa + lista unificada)                                                                                                                                
                                                                                                                                                                                        
  cd /home/pasteurjr/progreact/aitrack/frontend                                                                                                                                         
  npm start                                                                                                                                                                             
  React dev server na porta 3000.                                                                                                                                                     
                                                                                                                                                                                        
  ---
  Terminal 3 — Simulador Tracker (GPS contínuo)                                                                                                                                         
                                                                                                                                                                                      
  cd /home/pasteurjr/progreact/aitrack                                                                                                                                                
  python simulator.py                                                                                                                                                                   
  Envia pacotes Maxtrack/Suntech/Queclink para porta 9000 a cada 10s.
                                                                                                                                                                                        
  ---                                                                                                                                                                                 
  Terminal 4 — Simulador Dirijabem (motoristas virtuais contínuos)                                                                                                                      
                                                                                                                                                                                      
  cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr                                                                                                                               
  python dirijabem_continuous_simulator.py --drivers 5 --speed 10                                                                                                                       
  5 motoristas virtuais gerando viagens com métricas comportamentais.                                                                                                                   
                                                                                                                                                                                        
  ---                                                                                                                                                                                   
  Terminal 5 (opcional) — Insurance Web (datadrivr)                                                                                                                                     
                                                                                                                                                                                      
  cd /home/pasteurjr/progreact/datadrivr/insurance-web                                                                                                                                  
  npm start                                                                                                                                                                             
  React separado, em outra porta (provavelmente 3001 se o 3000 já estiver ocupado — o react-scripts pergunta).                                                                        

3. mobile-app (app Expo/React Native)                                                                                                                                               
                                                                                                                                                                                        
  cd /home/pasteurjr/progreact/datadrivr/mobile-app
  npm start              # padrão (LAN, escaneia QR)                                                                                                                                    
  # ou:                                                                                                                                                                                 
  npm run web            # roda no browser                                                                                                                                              
  npm run android        # roda no emulador Android                                                                                                                                     
  npm run ios            # roda no emulador iOS                                                                                                                                                                                 
  ---            

  ### 3. Frontend (Terminal 3)

```bash
cd /home/pasteurjr/progreact/aitrack/aitrackdatadrivr/frontend
npm start                                                                                                                                                                     
  Dica: Você pode rodar em background no mesmo terminal usando & ou abrir tabs com tmux/Terminator. Se quiser, eu monto um script start_all.sh para subir tudo de uma vez.        