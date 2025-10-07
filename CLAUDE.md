# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AITrack is a vehicle tracking and monitoring system with AI-powered analytics. The system receives GPS data from multiple tracker protocols (Maxtrack, Suntech, Queclink), stores it in a MySQL database, and displays real-time vehicle positions on a web interface. The long-term vision includes intelligent agents for route analysis, theft detection, predictive maintenance, and fleet optimization (see ESPECIFICACAO_AITRACK.md).

## Architecture

**Three-tier system:**
1. **Socket Server** (`server/socket_server.py`): TCP server listening on port 9000, receives raw GPS packets from trackers
2. **Protocol Layer** (`server/protocol_parsers.py`): Parses Maxtrack, Suntech, and Queclink protocols into standardized JSON
3. **Database Layer** (`server/db_handler.py`): Saves parsed data to MySQL with connection pooling
4. **REST API** (`server/api.py`): Flask API on port 5000 serving vehicle positions to frontend
5. **Frontend** (`frontend/`): React + TypeScript app with Leaflet maps for real-time vehicle visualization

**Data Flow:**
```
Trackers → Socket Server (port 9000) → Protocol Parsers → DB Handler → MySQL
                                                                          ↑
Frontend (React) ← REST API (Flask, port 5000) ←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

## Common Commands

### Running the System

```bash
# Start both socket server and API simultaneously
python run.py

# Run simulator to generate test data (10 vehicles, 3 protocols)
python simulator.py

# Frontend development
cd frontend
npm start          # Development server on http://localhost:3000
npm test           # Run tests
npm run build      # Production build
```

### Development

```bash
# Frontend only
cd frontend && npm start

# Backend API only (without socket server)
python -c "from server.api import app; app.run(host='0.0.0.0', port=5000, debug=True)"

# Socket server only
python -c "from server.socket_server import start_server; start_server()"
```

## Database Schema

**MySQL database `tracker` on `camerascasas.no-ip.info:3307`**

Key tables:
- `veiculos`: (VEICOD, VEIPLACA, VEI_DEVICE_ID)
- `localizacao`: (FK_VEICOD, LOCLATLONG GEOMETRY, DATAHORA, VELATU, ALTITUDE, ORIENT)

The system uses **MySQL Spatial Extensions** (ST_PointFromText, ST_X, ST_Y) for geographic data.

## Protocol Parser Architecture

Each tracker protocol has its own parser function that returns standardized data:
```python
{
    'protocol': 'maxtrack'|'suntech'|'queclink',
    'device_id': str or None,
    'timestamp': ISO format,
    'latitude': float,
    'longitude': float,
    'speed': float,
    'heading': float,
    'ignition': bool,
    'battery_voltage': float,
    'altitude': float or None
}
```

**Maxtrack caveat**: Protocol doesn't include device_id, so the parser uses client IP:port as identifier.

## Frontend Architecture

- **App.tsx**: Main component managing selected vehicle state
- **VehicleList**: Sidebar listing all vehicles
- **MapComponent**: Leaflet map displaying vehicle positions
- **MapViewUpdater**: Component to auto-center map on selected vehicle

The frontend polls the API for position updates and displays vehicles with custom icons based on heading/status.

## Key Implementation Notes

1. **Connection pooling**: DB handler uses MySQL connection pool (15 connections) to handle concurrent tracker connections
2. **Auto-vehicle creation**: If a tracker sends data for an unknown device_id, a new vehicle record is automatically created
3. **Concurrent handling**: Socket server uses ThreadPoolExecutor (20 workers) to handle multiple simultaneous tracker connections
4. **CORS enabled**: API allows cross-origin requests from any origin for development
5. **Process management**: `run.py` uses multiprocessing to run socket server and API in parallel processes with automatic restart on failure

## Testing

Use `simulator.py` to generate realistic test data:
- Creates 10 simulated vehicles (cycling through all 3 protocols)
- Sends position updates every 10 seconds
- Vehicles move randomly around São Paulo coordinates (-23.4 to -23.6 lat, -46.5 to -46.7 lon)
