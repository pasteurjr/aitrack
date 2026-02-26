# Dirijabem Database Analysis

## Overview

The **dirijabem** database is a production vehicle tracking and driver behavior analysis system. It stores GPS telemetry data, trip records, driver scoring metrics, and vehicle/user management information.

**Database Connection:**
- Host: `camerascasas.no-ip.info`
- Port: `3307`
- Database: `dirijabem`
- User: `producao`
- Password: `112358123`

**Data Volume (as of analysis):**
- 5,682 trips recorded
- 3,223,744 GPS data points
- 10+ active vehicles
- Primary vehicle: PUV7890 (2,052 trips with data)

## Database Schema

### Core Tracking Tables

#### `viagem` (Trip Records)
Trip-level aggregated data with scoring metrics.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CODVIA` | int(11) | PK | Unique trip ID (auto-increment) |
| `CODUSU` | int(11) | FK | User ID |
| `PLACA` | varchar(7) | FK | Vehicle license plate |
| `DATAHORINI` | datetime | | Trip start timestamp |
| `DATAHORFIN` | datetime | | Trip end timestamp |
| `DISTANCIA` | double | | Total distance (km) |
| `DURACAO` | double | | Total duration (minutes) |
| `SCORE` | double | | Overall trip score |
| `OST`, `OSA`, `GAA`, `OSP` | float | | Scoring metrics (over-speed, acceleration, etc.) |
| `SAM`, `SAA`, `BRP`, `BRM`, `BRA` | float | | Additional behavior metrics |
| `GAP`, `GAN`, `GAM` | float | | More scoring components |

**Relationships:**
- `CODUSU` → `usuario.CODUSU`
- `PLACA` → `veiculo.PLACA`

**Sample Data:**
```sql
-- Recent trips for PUV7890
SELECT CODVIA, PLACA, DATAHORINI, DATAHORFIN, DISTANCIA, SCORE
FROM viagem
WHERE PLACA = 'PUV7890'
ORDER BY DATAHORINI DESC
LIMIT 5;

-- Example result:
-- CODVIA=6108, PLACA=PUV7890, START=2025-11-14 14:50:35, END=2025-11-14 14:54:42, DIST=1.13km
-- CODVIA=6107, PLACA=PUV7890, START=2025-11-12 15:32:15, END=2025-11-12 15:33:56, DIST=0.65km
```

#### `localizacaodados` (Continuous GPS Data)
High-frequency GPS telemetry during trips (~1 point per second).

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `LOCDADCOD` | int(11) | PK | Unique data point ID |
| `CODVIA` | int(11) | FK | Trip ID reference |
| `DATAHORA` | datetime | | Timestamp of GPS reading |
| `VELATU` | float | | Current velocity (km/h) |
| `ACELLINATU` | float | | Linear acceleration |
| `ACELGPSATU` | float | | GPS-derived acceleration |
| `VARDIRATU` | float | | Heading change rate |
| `coords` | point | | Geographic coordinates (MySQL POINT) |

**Geographic Data:**
- Coordinates stored as MySQL POINT type
- Extract with: `ST_X(coords)` → longitude, `ST_Y(coords)` → latitude
- Typical data: Belo Horizonte area (lat: -19.94 to -19.96, lon: -43.91 to -43.93)

**Relationships:**
- `CODVIA` → `viagem.CODVIA`

**Sample Queries:**
```sql
-- Extract GPS route for a trip
SELECT
    DATAHORA,
    ST_Y(coords) as latitude,
    ST_X(coords) as longitude,
    VELATU as speed_kmh
FROM localizacaodados
WHERE CODVIA = 6103
ORDER BY DATAHORA ASC;

-- Count points per trip
SELECT CODVIA, COUNT(*) as num_points
FROM localizacaodados
GROUP BY CODVIA
HAVING num_points > 50
ORDER BY num_points DESC;
```

#### `localizacao` (Deprecated Location Table)
**Status:** Empty table (0 records) - appears to be legacy/deprecated.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `LOCCOD` | int(11) | PK | Location ID |
| `CODVIA` | int(11) | FK | Trip ID |
| `LAT` | double | | Latitude |
| `LONGI` | double | | Longitude |
| `DATAHORA` | datetime | | Timestamp |
| `coords` | point | | Geographic point |

**Note:** Modern system uses `localizacaodados` instead. This table likely predates the current architecture.

### Vehicle & Model Management

#### `veiculo` (Vehicles)
Vehicle registry with model references.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `PLACA` | varchar(7) | PK | License plate (unique) |
| `CODUSU` | int(11) | FK | Owner user ID |
| `CODMOD` | int(11) | FK | Vehicle model ID |
| `ANO` | int(11) | | Manufacturing year |
| `SEGURO` | varchar(1) | | Insurance flag ('Y'/'N') |
| `VIN` | varchar(17) | | Vehicle Identification Number |

**Relationships:**
- `CODUSU` → `usuario.CODUSU`
- `CODMOD` → `modelo.CODMOD`

**Active Vehicles:**
```sql
-- Top vehicles by trip count
SELECT v.PLACA, COUNT(via.CODVIA) as num_trips
FROM veiculo v
LEFT JOIN viagem via ON v.PLACA = via.PLACA
GROUP BY v.PLACA
ORDER BY num_trips DESC;

-- Result:
-- PUV7890: 2,517 trips
-- pyz8529: 580 trips
-- OGT9079: 176 trips
```

#### `modelo` (Vehicle Models)
Vehicle model catalog with brand references.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CODMOD` | int(11) | PK | Model ID |
| `NOMMOD` | varchar(50) | UNIQUE | Model name |
| `CODMAR` | int(11) | FK | Brand ID |

**Relationships:**
- `CODMAR` → `marca.CODMAR`

#### `marca` (Vehicle Brands)
Vehicle brand/manufacturer catalog.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CODMAR` | int(11) | PK | Brand ID |
| `NOMMAR` | varchar(50) | UNIQUE | Brand name |

### User & Contract Management

#### `usuario` (Users/Drivers)
Driver/user profiles with contact information.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CODUSU` | int(11) | PK | User ID |
| `NOMUSU` | varchar(100) | | Full name |
| `SENUSU` | varchar(100) | | Password (hashed) |
| `USUCPF` | varchar(11) | UNIQUE | Brazilian CPF (tax ID) |
| `USUADATNAS` | date | | Date of birth |
| `USUSEX` | varchar(1) | | Gender |
| `USUTEL` | varchar(16) | | Phone number |
| `USULOG` | varchar(50) | | Street address |
| `USULOGNUM` | varchar(7) | | Address number |
| `USULOGCOMP` | varchar(10) | | Address complement |
| `USUCEP` | int(11) | | ZIP code |
| `USUEMAIL` | varchar(100) | UNIQUE | Email address |
| `NOME_CORR` | varchar(100) | | Emergency contact name |
| `TELCORR` | varchar(16) | | Emergency contact phone |
| `PLACADEFAULT` | varchar(7) | | Default vehicle plate |

#### `contrato` (Contracts)
Service contracts between users and the platform.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CONTNUM` | varchar(10) | PK | Contract number |
| `CONTDATINI` | datetime | | Contract start date |
| `CONTDATFIN` | datetime | | Contract end date (planned) |
| `CONTDATFINEFET` | datetime | | Contract end date (actual) |
| `CODUSU` | int(11) | FK | User ID |

**Relationships:**
- `CODUSU` → `usuario.CODUSU`

#### `contratoveiculo` (Contract-Vehicle Associations)
Many-to-many relationship between contracts and vehicles.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `PLACA` | varchar(7) | PK | Vehicle plate |
| `CONTNUM` | varchar(10) | PK | Contract number |

**Composite Primary Key:** (`PLACA`, `CONTNUM`)

### Incident Management

#### `ocorrencia` (Incidents)
Records of incidents/accidents involving vehicles.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CODOCO` | int(11) | PK | Incident ID |
| `CODUSU` | int(11) | FK | User ID |
| `DESOCO` | varchar(500) | | Incident description |
| `DATAHOROCO` | datetime | | Incident timestamp |
| `PLACATERCEIRO` | varchar(7) | | Third-party vehicle plate |
| `PROPRTERCEIRO` | varchar(50) | | Third-party owner name |
| `CPFCNPJTERC` | varchar(14) | | Third-party tax ID |
| `LOCALOCORR` | point | | Incident location (POINT) |

**Relationships:**
- `CODUSU` → `usuario.CODUSU`

### Scoring & Analytics Tables

#### `variavel` (Scoring Variables)
Defines the scoring metrics used in driver behavior analysis.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CODVAR` | int(11) | PK | Variable ID |
| `NOMVAR` | varchar(50) | UNIQUE | Variable name |

**Examples:** OST (over-speed time), OSA (over-speed amount), GAA (harsh acceleration), BRA (harsh braking), etc.

#### `valor` (Variable Values)
Links scoring variable values to specific location data points.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CODVAR` | int(11) | PK | Variable ID |
| `LOCCOD` | int(11) | PK | Location ID |
| `VALOR` | float | | Measured value |

**Composite Primary Key:** (`CODVAR`, `LOCCOD`)

**Note:** References `localizacao.LOCCOD`, which is empty. May be deprecated alongside the `localizacao` table.

#### `nivelvariavel` (Variable Level Curves)
Defines scoring curves for converting raw measurements to normalized scores.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CODVAR` | int(11) | PK | Variable ID |
| `NIVEL` | int(11) | PK | Level/severity tier |
| `NUMCURVA` | int(11) | PK | Curve point number |
| `X` | float | | Input value |
| `Y` | float | | Output score |

**Composite Primary Key:** (`CODVAR`, `NIVEL`, `NUMCURVA`)

**Purpose:** Enables non-linear scoring (e.g., slight speeding = minor penalty, extreme speeding = major penalty)

#### `rankusuario` (User Rankings)
Aggregated statistics and rankings for all users.

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `USUCPF` | varchar(11) | | User CPF |
| `NOMUSU` | varchar(100) | | User name |
| `SCOREGLOBAL` | double | | Overall driving score |
| `DISTTOTAL` | double | | Total distance driven (km) |
| `DURTOTAL` | double | | Total driving time (minutes) |
| `VELMEDIA` | double | | Average speed (km/h) |
| `NUMVIAGENS` | bigint(21) | | Total number of trips |

**Note:** Likely a materialized view or cached table for leaderboard display.

#### `rankusuariocontrat` (User-Contract Rankings)
Aggregated statistics per user per contract (more granular than `rankusuario`).

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `USUCPF` | varchar(11) | | User CPF |
| `NOMUSU` | varchar(100) | | User name |
| `CONTNUM` | varchar(10) | | Contract number |
| `PLACA` | varchar(7) | | Vehicle plate |
| `SCOREGLOBAL` | double | | Score for this contract |
| `VELMEDIA` | double | | Average speed |
| `DISTTOTAL` | double | | Total distance |
| `DURTOTAL` | double | | Total duration |
| `NUMVIAGENS` | bigint(21) | | Number of trips |

#### `rankingcontratosmapa` (Contract Map Rankings)
Geographic rankings for contracts (possibly for heat maps or regional analysis).

| Field | Type | Key | Description |
|-------|------|-----|-------------|
| `CONTNUM` | varchar(10) | | Contract number |
| `USUCPF` | varchar(11) | | User CPF |
| `PLACA` | varchar(7) | | Vehicle plate |
| `SCORE` | double | | Score |
| `LAT` | double | | Latitude |
| `LONGI` | double | | Longitude |

## Entity Relationship Diagram

```
usuario (CODUSU) ──┬──> viagem (CODUSU)
                   │
                   ├──> contrato (CODUSU)
                   │
                   └──> ocorrencia (CODUSU)

veiculo (PLACA) ───┬──> viagem (PLACA)
                   │
                   └──> contratoveiculo (PLACA)

viagem (CODVIA) ───┬──> localizacaodados (CODVIA)
                   │
                   └──> localizacao (CODVIA) [DEPRECATED]

marca (CODMAR) ────> modelo (CODMAR) ────> veiculo (CODMOD)

variavel (CODVAR) ─┬──> valor (CODVAR)
                   │
                   └──> nivelvariavel (CODVAR)

contrato (CONTNUM) ───> contratoveiculo (CONTNUM)
```

## Key Insights

### Data Quality

**Strong Points:**
- High-frequency GPS data (~1 Hz sampling rate)
- Comprehensive trip metadata (distance, duration, scores)
- Real-world routes from production system
- Multiple vehicles with diverse route patterns

**Considerations:**
- `localizacao` table is empty (deprecated legacy table)
- `valor` table may be unused (references empty `localizacao`)
- Most data concentrated in single vehicle (PUV7890)
- Geographic area limited to Belo Horizonte region

### Trip Statistics

```sql
-- Summary of viable trips for route extraction
SELECT
    COUNT(DISTINCT v.CODVIA) as total_trips,
    COUNT(DISTINCT v.PLACA) as unique_vehicles,
    SUM(v.DISTANCIA) as total_km,
    AVG(ld_count.points) as avg_points_per_trip,
    MIN(v.DATAHORINI) as earliest_trip,
    MAX(v.DATAHORFIN) as latest_trip
FROM viagem v
LEFT JOIN (
    SELECT CODVIA, COUNT(*) as points
    FROM localizacaodados
    GROUP BY CODVIA
) ld_count ON v.CODVIA = ld_count.CODVIA
WHERE ld_count.points > 50;
```

### Geographic Coverage

**Primary Region:** Belo Horizonte, Minas Gerais, Brazil
- Latitude range: -19.94 to -19.96
- Longitude range: -43.91 to -43.93

**Comparison to AITrack Current Routes:**
- AITrack synthetic routes: São Paulo (-23.5 to -23.6 lat, -46.6 to -46.7 lon)
- ~400km geographic separation
- Allows multi-region testing

## Route Extraction Strategy

### Objective
Extract real GPS routes from `dirijabem` to enhance AITrack simulator with authentic vehicle movement patterns.

### Selection Criteria

**Minimum Requirements:**
- At least 50 GPS points per trip
- Complete timestamps (no gaps > 60 seconds)
- Valid geographic coordinates (non-NULL `coords`)
- Reasonable distance (> 0.5 km, < 100 km)

**Prioritization:**
1. Trips with high point density (> 100 points)
2. Diverse vehicles (not just PUV7890)
3. Various distances and durations
4. Recent data (2025 preferred)

### Extraction Query

```sql
-- Get viable trips with metadata
SELECT
    v.CODVIA,
    v.PLACA,
    v.DATAHORINI,
    v.DATAHORFIN,
    v.DISTANCIA,
    COUNT(ld.LOCDADCOD) as num_points,
    MIN(ST_Y(ld.coords)) as min_lat,
    MAX(ST_Y(ld.coords)) as max_lat,
    MIN(ST_X(ld.coords)) as min_lon,
    MAX(ST_X(ld.coords)) as max_lon
FROM viagem v
INNER JOIN localizacaodados ld ON v.CODVIA = ld.CODVIA
WHERE v.DATAHORINI >= '2025-01-01'
  AND ld.coords IS NOT NULL
GROUP BY v.CODVIA, v.PLACA, v.DATAHORINI, v.DATAHORFIN, v.DISTANCIA
HAVING num_points >= 50
ORDER BY num_points DESC
LIMIT 20;
```

### Route Format Conversion

**Source Format (MySQL):**
```sql
SELECT ST_Y(coords) as lat, ST_X(coords) as lon
FROM localizacaodados
WHERE CODVIA = 6103
ORDER BY DATAHORA ASC;
```

**Target Format (AITrack JSON):**
```json
{
  "PUV7890_6103": [
    [-19.9545, -43.9228],
    [-19.9545, -43.9228],
    [-19.9546, -43.9227],
    ...
  ]
}
```

**Note:** Format is `[latitude, longitude]` (Y, X in MySQL POINT notation).

### Implementation Plan

**Script:** `tools/extract_routes.py`

**Features:**
- Database connection with credentials from ENV or CLI
- Configurable filters (min_points, max_routes, vehicle_filter)
- Output to `config/routes_extracted.json`
- Option to merge with existing synthetic routes

**Usage Examples:**
```bash
# Extract 20 best routes
python tools/extract_routes.py --max-routes 20 --output config/routes_extracted.json

# Extract only PUV7890 routes
python tools/extract_routes.py --vehicle PUV7890 --max-routes 15

# Merge with existing routes
python tools/extract_routes.py --merge --max-routes 10
```

## Integration with AITrack Simulator

### Current Architecture
- Simulator loads routes from `config/routes.json`
- `server/routes_loader.py` handles loading and densification
- Each vehicle follows a route in loop

### Enhanced Architecture
- Support multiple route sources: synthetic (SP) + real (BH)
- `routes_loader.py` merges routes from multiple JSON files
- Simulator can specify which source(s) to use

### Migration Path

**Phase 1:** Extract routes to separate file
```bash
python tools/extract_routes.py --output config/routes_extracted.json
```

**Phase 2:** Test with extracted routes only
```bash
cp config/routes.json config/routes_backup.json
cp config/routes_extracted.json config/routes.json
python simulator.py
```

**Phase 3:** Merge synthetic + real routes
```bash
python tools/extract_routes.py --merge --max-routes 10
```

**Phase 4:** Configure simulator route source preference
- Environment variable: `ROUTE_SOURCES=routes.json,routes_extracted.json`
- Or CLI flag: `python simulator.py --routes all`

## Sample Queries for Analysis

### Find Most Active Vehicles
```sql
SELECT
    v.PLACA,
    COUNT(DISTINCT via.CODVIA) as num_trips,
    SUM(via.DISTANCIA) as total_km,
    MIN(via.DATAHORINI) as first_trip,
    MAX(via.DATAHORFIN) as last_trip
FROM veiculo v
LEFT JOIN viagem via ON v.PLACA = via.PLACA
GROUP BY v.PLACA
HAVING num_trips > 10
ORDER BY num_trips DESC;
```

### Analyze Trip Patterns by Time
```sql
SELECT
    HOUR(DATAHORINI) as hour_of_day,
    COUNT(*) as num_trips,
    AVG(DISTANCIA) as avg_distance_km,
    AVG(DURACAO) as avg_duration_min
FROM viagem
WHERE DATAHORINI >= '2025-01-01'
GROUP BY hour_of_day
ORDER BY hour_of_day;
```

### Get Trips with Highest Point Density
```sql
SELECT
    v.CODVIA,
    v.PLACA,
    COUNT(ld.LOCDADCOD) as num_points,
    v.DISTANCIA,
    COUNT(ld.LOCDADCOD) / v.DISTANCIA as points_per_km
FROM viagem v
INNER JOIN localizacaodados ld ON v.CODVIA = ld.CODVIA
GROUP BY v.CODVIA, v.PLACA, v.DISTANCIA
HAVING num_points > 50 AND v.DISTANCIA > 1
ORDER BY points_per_km DESC
LIMIT 10;
```

### Extract Complete Route Data
```sql
SELECT
    ld.DATAHORA,
    ST_Y(ld.coords) as latitude,
    ST_X(ld.coords) as longitude,
    ld.VELATU as speed_kmh,
    ld.ACELGPSATU as acceleration,
    ld.VARDIRATU as heading_change
FROM localizacaodados ld
WHERE ld.CODVIA = ?
  AND ld.coords IS NOT NULL
ORDER BY ld.DATAHORA ASC;
```

## Future Enhancements

### Phase 1: Basic Route Extraction ✓
- Extract GPS routes from `localizacaodados`
- Convert to AITrack JSON format
- Integrate with simulator

### Phase 2: Speed Profile Extraction
- Use `VELATU` field for realistic speed variation
- Eliminate random speed generation in simulator
- Match real acceleration/deceleration patterns

### Phase 3: Behavioral Scoring
- Extract scoring metrics (OST, OSA, GAA, BRA, etc.)
- Correlate with trip segments
- Identify high-risk driving patterns

### Phase 4: Real-time Data Pipeline
- Stream live data from dirijabem to AITrack
- Near real-time vehicle visualization
- Historical playback capabilities

### Phase 5: Multi-region Expansion
- Extract routes from additional geographic areas
- Build comprehensive route library
- Regional traffic pattern analysis

## References

- **AITrack Repository:** `/home/pasteurjr/progreact/aitrack/`
- **Simulator Code:** `simulator.py`, `server/routes_loader.py`
- **Current Routes:** `config/routes.json` (5 synthetic São Paulo routes)
- **Database Documentation:** This file
- **Extraction Plan:** `/home/pasteurjr/.claude/plans/moonlit-hopping-robin.md`

---

*Document created: 2026-01-27*
*Database: dirijabem @ camerascasas.no-ip.info:3307*
*Analysis scope: 16 tables, 3.2M GPS points, 5,682 trips*
