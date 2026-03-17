import React, { useState } from 'react';
import MapComponent from './components/MapComponent';
import './App.css'; // Usaremos para alguns estilos customizados

import VehicleListUnified from './components/VehicleListUnified';

function App() {
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | null>(null);
  const [selectedPlaca, setSelectedPlaca] = useState<string | null>(null);

  const handleVehicleSelect = (id: number, placa: string) => {
    setSelectedVehicleId(id);
    setSelectedPlaca(placa);
  };

  return (
    <div className="container-fluid vh-100 d-flex flex-column">
      <header className="bg-dark text-white text-center p-2">
        <h4>AITrack - Monitoramento em Tempo Real</h4>
      </header>
      <div className="row flex-grow-1 g-0">
        {/* Coluna da Barra Lateral */}
        <div className="col-md-3 bg-light border-end overflow-auto">
          <div className="p-2 border-bottom">
            <h6 className="mb-0">Veículos</h6>
          </div>
          <VehicleListUnified selectedVehicleId={selectedVehicleId} onVehicleSelect={handleVehicleSelect} />
        </div>

        {/* Coluna do Mapa */}
        <div className="col-md-9">
          <MapComponent selectedVehicleId={selectedVehicleId} selectedPlaca={selectedPlaca} />
        </div>
      </div>
    </div>
  );
}

export default App;
