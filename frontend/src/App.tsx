import React, { useState } from 'react';
import MapComponent from './components/MapComponent';
import './App.css'; // Usaremos para alguns estilos customizados

import VehicleList from './components/VehicleList';

function App() {
  // No futuro, o ID do veículo selecionado será guardado aqui
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | null>(null);

  return (
    <div className="container-fluid vh-100 d-flex flex-column">
      <header className="bg-dark text-white text-center p-2">
        <h4>AITrack - Monitoramento em Tempo Real</h4>
      </header>
      <div className="row flex-grow-1 g-0">
        {/* Coluna da Barra Lateral */}
        <div className="col-md-3 bg-light border-end overflow-auto">
          <div className="p-3">
            <h5>Veículos Online</h5>
            <VehicleList selectedVehicleId={selectedVehicleId} onVehicleSelect={setSelectedVehicleId} />
          </div>
        </div>

        {/* Coluna do Mapa */}
        <div className="col-md-9">
          <MapComponent selectedVehicleId={selectedVehicleId} />
        </div>
      </div>
    </div>
  );
}

export default App;
