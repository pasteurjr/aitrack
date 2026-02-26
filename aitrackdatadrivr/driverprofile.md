# Driver Profile Fuzzy Logic System

## Overview

The AITrack system uses a **Fuzzy Inference System (FIS)** to classify driver behavior based on 12 input metrics derived from GPS telemetry data. The system analyzes speeding, acceleration, braking, and direction changes to produce a driver profile score ranging from 0-100.

**Source File:** `/home/pasteurjr/progreact/aitrack/driverprofile.fcl`

**Technology:** Fuzzy Control Language (FCL) - implements fuzzy logic control system based on jFuzzyLogic library

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Fuzzy Inference System                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  INPUT (12 metrics)                                         │
│  ┌──────────────────┐     ┌──────────────────┐            │
│  │ Speeding Metrics │     │  Accel Metrics   │            │
│  │ - OST, OSA, OSP  │     │ - SAM, SAA       │            │
│  └────────┬─────────┘     │ - GAM, GAA       │            │
│           │               │ - GAP, GAN       │            │
│           │               └────────┬─────────┘            │
│           │                        │                       │
│           │     ┌──────────────────┴──────────┐           │
│           │     │  Direction Metrics          │           │
│           │     │  - BRP, BRM, BRA            │           │
│           │     └──────────┬──────────────────┘           │
│           │                │                               │
│           ▼                ▼                               │
│  ┌─────────────────────────────────────────┐              │
│  │         FUZZIFICATION                    │              │
│  │  Convert crisp values to fuzzy sets      │              │
│  │  (LOW, MEDIUM, HIGH membership)          │              │
│  └─────────────┬───────────────────────────┘              │
│                │                                           │
│                ▼                                           │
│  ┌─────────────────────────────────────────┐              │
│  │         INFERENCE ENGINE                │              │
│  │  21 fuzzy rules combine inputs          │              │
│  │  AND: MIN, ACT: MIN, ACCU: MAX          │              │
│  └─────────────┬───────────────────────────┘              │
│                │                                           │
│                ▼                                           │
│  ┌─────────────────────────────────────────┐              │
│  │         DEFUZZIFICATION (COG)           │              │
│  │  Convert fuzzy output to crisp score    │              │
│  └─────────────┬───────────────────────────┘              │
│                │                                           │
│                ▼                                           │
│  OUTPUT: PERFIL (0-100)                                   │
│  - NORMAL (0-30): Safe driver                             │
│  - MODERADO (30-75): Moderate risk                        │
│  - AGRESSIVO (75-100): High risk                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Input Variables (12 Metrics)

### 1. Speeding Metrics

#### OST - Tempo em Excesso de Velocidade (Time Speeding)
**Definition:** Proportion of trip time spent over the speed limit

**Calculation:** `(seconds_over_speed_limit / total_trip_seconds)`

**Fuzzy Sets:**
- **LOW:** 0% to 10% (membership: 1.0 at 0%, 0.0 at 10-30%)
- **MEDIUM:** 10% to 30% (membership: peak 1.0 at 10%, tapering to 0.0 at 0% and 30%)
- **HIGH:** >30% (membership: 0.0 at 0-10%, 1.0 at 30%+)

**Example:**
- Trip duration: 1800 seconds (30 minutes)
- Time over speed limit: 540 seconds (9 minutes)
- OST = 540/1800 = 0.30 (30%) → **HIGH**

---

#### OSA - Excesso de Velocidade Médio (Average Speeding)
**Definition:** Average km/h over the speed limit when speeding

**Calculation:** `sum(speed - speed_limit) / count(speeding_events)` (only when speed > limit)

**Fuzzy Sets:**
- **LOW:** 0-2 km/h (constant 1.0 membership from 0-1 km/h, tapers to 0.0 at 2-6 km/h)
- **MEDIUM:** 2-6 km/h (peak 1.0 at 2-4 km/h, tapers to 0.0 at 1 km/h and 6 km/h)
- **HIGH:** >6 km/h (membership 0.0 at 0-4 km/h, 1.0 at 6+ km/h)

**Example:**
- Speed readings over limit: [82, 85, 87] km/h (limit: 80 km/h)
- Excess: [2, 5, 7] km/h
- OSA = (2+5+7)/3 = 4.67 km/h → **MEDIUM**

---

#### OSP - Pico de Excesso de Velocidade (Peak Speeding)
**Definition:** Maximum km/h over speed limit during trip

**Calculation:** `max(speed - speed_limit)` across all GPS points

**Fuzzy Sets:** Same as OSA (LOW: 0-2, MEDIUM: 2-6, HIGH: >6 km/h)

**Example:**
- Speed readings: [78, 82, 95, 81] km/h (limit: 80 km/h)
- OSP = 95 - 80 = 15 km/h → **HIGH**

---

### 2. Acceleration Event Metrics

#### SAM - Eventos de Aceleração Moderada (Moderate Acceleration Events)
**Definition:** Count of moderate acceleration events during trip

**Detection:** Acceleration between 2.0-3.5 m/s² (moderate threshold)

**Fuzzy Sets:**
- **LOW:** 0-2 events
- **MEDIUM:** 2-4 events
- **HIGH:** >4 events

**Calculation:**
```python
sam_count = 0
for i in range(1, len(gps_points)):
    delta_v = gps_points[i].speed - gps_points[i-1].speed  # km/h
    delta_t = gps_points[i].timestamp - gps_points[i-1].timestamp  # seconds
    accel = (delta_v / 3.6) / delta_t  # convert to m/s²

    if 2.0 <= accel < 3.5:
        sam_count += 1
```

---

#### SAA - Eventos de Aceleração Agressiva (Aggressive Acceleration Events)
**Definition:** Count of aggressive acceleration events

**Detection:** Acceleration >= 3.5 m/s² (harsh threshold)

**Fuzzy Sets:** Same as SAM (LOW: 0-2, MEDIUM: 2-4, HIGH: >4 events)

**Example:**
- Trip with 8 acceleration events: 5 moderate (2.2-3.2 m/s²), 3 aggressive (3.8-4.5 m/s²)
- SAM = 5 → **HIGH**
- SAA = 3 → **MEDIUM**

---

### 3. G-Force/Acceleration Per Kilometer Metrics

#### GAM - Eventos de Aceleração Moderada por Km
**Definition:** Moderate acceleration events normalized by distance

**Calculation:** `SAM / (total_distance_km)`

**Fuzzy Sets:**
- **LOW:** 0-2 events/km
- **MEDIUM:** 2-3 events/km (narrow peak)
- **HIGH:** >3 events/km

**Example:**
- SAM = 12 events
- Total distance = 25 km
- GAM = 12/25 = 0.48 events/km → **LOW**

---

#### GAA - Eventos de Aceleração Agressiva por Km
**Definition:** Aggressive acceleration events normalized by distance

**Calculation:** `SAA / (total_distance_km)`

**Fuzzy Sets:** Same as GAM (LOW: 0-2, MEDIUM: 2-3, HIGH: >3 events/km)

---

#### GAP - Aceleração Máxima Positiva (Maximum Positive Acceleration)
**Definition:** Peak positive acceleration (speeding up) in m/s²

**Calculation:** `max(delta_v / delta_t)` for all positive accelerations

**Fuzzy Sets:**
- **LOW:** 0-2 m/s²
- **MEDIUM:** 2-3 m/s²
- **HIGH:** >3 m/s²

**Example:**
- Peak acceleration during trip: 4.2 m/s² → **HIGH**

---

#### GAN - Aceleração Máxima Negativa (Maximum Negative Acceleration)
**Definition:** Peak negative acceleration (braking) in m/s² (absolute value)

**Calculation:** `max(abs(delta_v / delta_t))` for all negative accelerations

**Fuzzy Sets:** Same as GAP (LOW: 0-2, MEDIUM: 2-3, HIGH: >3 m/s²)

**Example:**
- Hardest brake: -5.1 m/s² → |−5.1| = 5.1 m/s² → **HIGH**

---

### 4. Direction Change Metrics

#### BRP - Máxima Variação de Direção (Maximum Bearing Change)
**Definition:** Maximum direction change in degrees between consecutive GPS points

**Calculation:** `max(abs(bearing[i] - bearing[i-1]))` accounting for 360° wrap-around

**Fuzzy Sets:** (Note: Quadrupled from original 0-20° to 0-80°)
- **LOW:** 0-40°
- **MEDIUM:** 40-80°
- **HIGH:** >80°

**Example:**
- Sharp turn: bearing changes from 45° to 135° = 90° change → **HIGH**

**Code Calculation:**
```python
def bearing_change(bearing1, bearing2):
    # Handle 360° wrap-around
    diff = abs(bearing2 - bearing1)
    if diff > 180:
        diff = 360 - diff
    return diff

brp = max([bearing_change(points[i].bearing, points[i+1].bearing)
           for i in range(len(points)-1)])
```

---

#### BRM - Eventos de Mudança Moderada de Direção (Moderate Direction Change Events)
**Definition:** Count of moderate direction changes (lane changes, gentle curves)

**Detection:** Bearing change between 20-45° within 5-second window

**Fuzzy Sets:**
- **LOW:** 0-2 events
- **MEDIUM:** 2-3 events (narrow)
- **HIGH:** >3 events

---

#### BRA - Eventos de Mudança Agressiva de Direção (Aggressive Direction Change Events)
**Definition:** Count of aggressive direction changes (sharp turns, swerving)

**Detection:** Bearing change > 45° within 5-second window

**Fuzzy Sets:** Same as BRM (LOW: 0-2, MEDIUM: 2-3, HIGH: >3 events)

---

## Output Variable: PERFIL (Driver Profile)

### Fuzzy Output Sets

The defuzzified output ranges from 0-100:

- **NORMAL** (0-30): Safe, defensive driving behavior
  - Membership: 1.0 from 0-15, tapers to 0.0 at 30

- **MODERADO** (30-75): Moderate risk, some concerning patterns
  - Membership: 0.0 at 15, ramps to 1.0 at 30-60, tapers to 0.0 at 75

- **AGRESSIVO** (75-100): High risk, dangerous driving
  - Membership: 0.0 at 0-60, ramps to 1.0 at 75-100

### Defuzzification Method

**Center of Gravity (COG):** Calculates weighted average of membership functions

```
         ∑(μ(x) * x)
PERFIL = ───────────
           ∑μ(x)

Where:
- μ(x) = membership degree at point x
- x = crisp value on 0-100 scale
```

**Default Value:** 0 (if no rules activate)

---

## Fuzzy Rules (21 Rules)

### Rule Operators
- **AND:** MIN (minimum of membership values)
- **OR:** MAX (maximum of membership values) - implicit via DeMorgan's Law
- **Activation Method (ACT):** MIN
- **Accumulation Method (ACCU):** MAX

---

### Speeding Rules (Rules 1-3, 19-21)

**RULE 1:** `IF OST IS LOW AND OSA IS LOW AND OSP IS LOW THEN PERFIL IS NORMAL`
- All speeding metrics low → Safe driver

**RULE 2:** `IF OST IS MEDIUM AND OSA IS MEDIUM AND OSP IS MEDIUM THEN PERFIL IS MODERADO`
- Consistent moderate speeding → Moderate risk

**RULE 3:** `IF OST IS HIGH AND OSA IS HIGH AND OSP IS HIGH THEN PERFIL IS AGRESSIVO`
- Severe speeding pattern → Aggressive driver

**RULE 19:** `IF OST IS LOW AND OSA IS LOW AND OSP IS MEDIUM THEN PERFIL IS MODERADO`
- Occasional speed spike despite low average → Moderate risk

**RULE 20:** `IF OST IS LOW AND OSA IS MEDIUM AND OSP IS LOW THEN PERFIL IS MODERADO`
- Moderate average speed with low time/peak → Moderate risk

**RULE 21:** `IF OST IS MEDIUM AND OSA IS LOW AND OSP IS LOW THEN PERFIL IS MODERADO`
- Longer time speeding but low magnitude → Moderate risk

**Example Scenario:**
- OST = 35% (HIGH), OSA = 8 km/h (HIGH), OSP = 12 km/h (HIGH)
- **RULE 3 activates** → Output pushes toward AGRESSIVO (75-100)

---

### Acceleration Event Rules (Rules 4-6)

**RULE 4:** `IF (SAM IS LOW OR SAM IS MEDIUM) AND SAA IS LOW THEN PERFIL IS NORMAL`
- Low aggressive acceleration → Safe

**RULE 5:** `IF SAM IS MEDIUM AND SAM IS HIGH AND SAA IS LOW THEN PERFIL IS MODERADO`
- Note: Appears to be typo (SAM appears twice) - likely meant "SAM IS HIGH"
- High moderate acceleration but low aggressive → Moderate risk

**RULE 6:** `IF SAA IS MEDIUM AND SAA IS HIGH AND SAM IS HIGH THEN PERFIL IS AGRESSIVO`
- Note: Similar typo (SAA appears twice)
- High aggressive + high moderate acceleration → Aggressive

**Example Scenario:**
- SAM = 8 (HIGH), SAA = 1 (LOW)
- **RULE 5 activates** → MODERADO

---

### G-Force Rules (Rules 7-12)

**RULE 7:** `IF GAM IS LOW AND GAM IS MEDIUM AND GAA IS LOW THEN PERFIL IS NORMAL`
- Note: GAM appears twice (typo)
- Low aggressive G-forces → Safe

**RULE 8:** `IF GAM IS MEDIUM AND GAM IS HIGH AND GAA IS LOW THEN PERFIL IS MODERADO`
- High moderate G but low aggressive → Moderate

**RULE 9:** `IF (GAA IS MEDIUM OR GAA IS HIGH) AND GAM IS HIGH THEN PERFIL IS AGRESSIVO`
- High G-force events → Aggressive

**RULE 10:** `IF GAP IS LOW AND GAN IS LOW THEN PERFIL IS NORMAL`
- Smooth acceleration and braking → Safe

**RULE 11:** `IF GAP IS MEDIUM AND GAN IS MEDIUM THEN PERFIL IS MODERADO`
- Moderate peak G-forces → Moderate risk

**RULE 12:** `IF GAP IS HIGH AND GAN IS HIGH THEN PERFIL IS AGRESSIVO`
- Harsh acceleration and hard braking → Aggressive

---

### Direction Change Rules (Rules 13-18)

**RULE 13:** `IF (BRM IS LOW OR BRM IS MEDIUM) AND BRA IS LOW THEN PERFIL IS NORMAL`
- Low aggressive turns → Safe

**RULE 14:** `IF (BRM IS MEDIUM OR BRM IS HIGH) AND BRA IS LOW THEN PERFIL IS MODERADO`
- Frequent moderate turns, no aggressive → Moderate

**RULE 15:** `IF (BRA IS MEDIUM OR BRA IS HIGH) AND BRM IS HIGH THEN PERFIL IS AGRESSIVO`
- Aggressive swerving/turns → Aggressive

**RULE 16:** `IF BRP IS LOW THEN PERFIL IS NORMAL`
- Maximum turn angle < 40° → Safe

**RULE 17:** `IF BRP IS MEDIUM AND (OSP IS MEDIUM OR OSP IS HIGH) THEN PERFIL IS MODERADO`
- Sharp turns combined with speeding → Moderate risk

**RULE 18:** `IF BRP IS HIGH AND (OSP IS MEDIUM OR OSP IS HIGH) THEN PERFIL IS AGRESSIVO`
- Very sharp turns (>80°) while speeding → Aggressive

**Example Scenario:**
- BRP = 95° (HIGH), OSP = 8 km/h (HIGH)
- **RULE 18 activates** → AGRESSIVO

---

## Integration with Dirijabem Database

### Database Storage

The calculated fuzzy metrics are stored in the `viagem` table in the `dirijabem` database:

```sql
SELECT
    CODVIA,           -- Trip ID
    CODUSU,           -- User/Driver ID
    DATAHORINI,       -- Trip start
    DATAHORFIN,       -- Trip end

    -- Fuzzy Input Variables
    OST,              -- Time speeding (0.0-1.0)
    OSA,              -- Average speeding (km/h)
    OSP,              -- Peak speeding (km/h)
    SAM,              -- Moderate accel events
    SAA,              -- Aggressive accel events
    BRP,              -- Max bearing change (degrees)
    BRM,              -- Moderate turn events
    BRA,              -- Aggressive turn events
    GAP,              -- Max positive accel (m/s²)
    GAN,              -- Max negative accel (m/s²)
    GAM,              -- Moderate accel per km
    GAA,              -- Aggressive accel per km

    -- Fuzzy Output
    SCORE             -- Final profile score (0-100)

FROM viagem
WHERE CODUSU = ?
ORDER BY DATAHORINI DESC;
```

### Calculation Flow

1. **Real-time GPS data** arrives in `localizacaodados` table
2. **Trip processor** calculates metrics during trip or at end
3. **Fuzzy engine** (jFuzzyLogic) evaluates driverprofile.fcl with metrics
4. **SCORE saved** to viagem.SCORE column
5. **Frontend displays** profile classification

---

## Usage Examples

### Example 1: Safe Driver

**Input Metrics:**
```
OST = 0.05 (5% time speeding)     → LOW
OSA = 1.2 km/h                    → LOW
OSP = 2.8 km/h                    → MEDIUM
SAM = 3                           → MEDIUM
SAA = 0                           → LOW
GAM = 0.8 per km                  → LOW
GAA = 0 per km                    → LOW
GAP = 1.5 m/s²                    → LOW
GAN = 1.8 m/s²                    → LOW
BRP = 25°                         → LOW
BRM = 4                           → HIGH
BRA = 0                           → LOW
```

**Activated Rules:**
- RULE 1: OST LOW, OSA LOW, OSP MEDIUM → Partial activation
- RULE 4: SAM MEDIUM, SAA LOW → NORMAL
- RULE 7: GAM LOW, GAA LOW → NORMAL
- RULE 10: GAP LOW, GAN LOW → NORMAL
- RULE 13: BRM HIGH, BRA LOW → NORMAL
- RULE 16: BRP LOW → NORMAL

**Output:** PERFIL = **22** (NORMAL category)

---

### Example 2: Moderate Risk Driver

**Input Metrics:**
```
OST = 0.18 (18% time speeding)    → MEDIUM
OSA = 4.5 km/h                    → MEDIUM
OSP = 8.2 km/h                    → HIGH
SAM = 7                           → HIGH
SAA = 2                           → MEDIUM
GAM = 1.8 per km                  → LOW
GAA = 0.5 per km                  → LOW
GAP = 2.9 m/s²                    → MEDIUM
GAN = 3.2 m/s²                    → MEDIUM
BRP = 52°                         → MEDIUM
BRM = 6                           → HIGH
BRA = 1                           → LOW
```

**Activated Rules:**
- RULE 2: OST MEDIUM, OSA MEDIUM, OSP HIGH → Partial (OSP breaks pattern)
- RULE 19: OST LOW/MEDIUM, OSA MEDIUM, OSP HIGH → MODERADO
- RULE 5: SAM HIGH, SAA LOW/MEDIUM → MODERADO
- RULE 11: GAP MEDIUM, GAN MEDIUM → MODERADO
- RULE 14: BRM HIGH, BRA LOW → MODERADO
- RULE 17: BRP MEDIUM, OSP HIGH → MODERADO

**Output:** PERFIL = **58** (MODERADO category)

---

### Example 3: Aggressive Driver

**Input Metrics:**
```
OST = 0.42 (42% time speeding)    → HIGH
OSA = 9.8 km/h                    → HIGH
OSP = 15.2 km/h                   → HIGH
SAM = 12                          → HIGH
SAA = 8                           → HIGH
GAM = 3.5 per km                  → HIGH
GAA = 2.8 per km                  → MEDIUM
GAP = 4.8 m/s²                    → HIGH
GAN = 5.2 m/s²                    → HIGH
BRP = 105°                        → HIGH
BRM = 9                           → HIGH
BRA = 5                           → HIGH
```

**Activated Rules:**
- RULE 3: OST HIGH, OSA HIGH, OSP HIGH → AGRESSIVO
- RULE 6: SAA HIGH, SAM HIGH → AGRESSIVO
- RULE 9: GAA HIGH, GAM HIGH → AGRESSIVO
- RULE 12: GAP HIGH, GAN HIGH → AGRESSIVO
- RULE 15: BRA HIGH, BRM HIGH → AGRESSIVO
- RULE 18: BRP HIGH, OSP HIGH → AGRESSIVO

**Output:** PERFIL = **89** (AGRESSIVO category)

---

## Implementation Notes

### Code Integration

The fuzzy logic system is implemented using **jFuzzyLogic** library:

```java
// Load FCL file
FIS fis = FIS.load("driverprofile.fcl");

// Get function block
FunctionBlock fb = fis.getFunctionBlock("tipper");

// Set input variables
fb.setVariable("OST", 0.35);
fb.setVariable("OSA", 7.2);
fb.setVariable("OSP", 12.5);
// ... set all 12 variables

// Evaluate
fb.evaluate();

// Get output
double perfil = fb.getVariable("PERFIL").getValue();
```

### Performance Considerations

- **Evaluation time:** < 5ms per trip on modern hardware
- **Memory:** Minimal (~2KB per FIS instance)
- **Thread-safe:** Each thread should have own FIS instance

### Tuning the System

To adjust sensitivity:

1. **Modify membership functions** in FUZZIFY blocks (e.g., change LOW threshold from 2 to 3)
2. **Adjust rule weights** (requires extending FCL with RULE ... WITH weight syntax)
3. **Add new rules** for edge cases
4. **Change defuzzification method** (COG, COGS, MOM, LM, RM)

**Example: Make BRP less sensitive (increase thresholds by 50%):**
```fcl
FUZZIFY BRP
    TERM LOW := (0, 1) (30, 1) (60,0) (120,0);     # was 20, 40, 80
    TERM MEDIUM :=(0, 0) (30, 0) (60,1) (90,1) (120,0);  # was 20, 40, 60, 80
    TERM HIGH := (0, 0) (90, 0) (120,1);           # was 60, 80
END_FUZZIFY
```

---

## Integration with AI Monitors

### Using Fuzzy Metrics in Monitor Prompts

AI monitors should query these metrics from the database and include them in LLM prompts:

```python
# Query trip metrics
cursor.execute("""
    SELECT OST, OSA, OSP, SAM, SAA, BRP, BRM, BRA,
           GAP, GAN, GAM, GAA, SCORE
    FROM viagem
    WHERE CODUSU = %s AND DATAHORFIN = '1900-01-01 00:00:00'
    LIMIT 1
""", (user_id,))

metrics = cursor.fetchone()

# Build prompt context
prompt = f"""
DRIVER PROFILE ANALYSIS for User {user_id}

FUZZY LOGIC METRICS:
┌─ Speeding ─────────────────────────┐
│ OST (Time):    {metrics['OST']:.1%} {'🔴' if metrics['OST'] > 0.3 else '🟢'}
│ OSA (Avg):     {metrics['OSA']:.1f} km/h
│ OSP (Peak):    {metrics['OSP']:.1f} km/h
└────────────────────────────────────┘

┌─ Acceleration ─────────────────────┐
│ SAM (Moderate): {metrics['SAM']} events
│ SAA (Aggressive): {metrics['SAA']} events
│ GAM (per km):  {metrics['GAM']:.2f}
│ GAA (per km):  {metrics['GAA']:.2f}
│ GAP (Max +):   {metrics['GAP']:.1f} m/s²
│ GAN (Max -):   {metrics['GAN']:.1f} m/s²
└────────────────────────────────────┘

┌─ Direction Changes ────────────────┐
│ BRP (Max):     {metrics['BRP']:.0f}°
│ BRM (Moderate): {metrics['BRM']} events
│ BRA (Aggressive): {metrics['BRA']} events
└────────────────────────────────────┘

FUZZY CLASSIFICATION:
Score: {metrics['SCORE']:.1f}/100 → {'NORMAL' if metrics['SCORE'] < 30 else 'MODERADO' if metrics['SCORE'] < 75 else 'AGRESSIVO'}

TASK: Identify which metric groups (speeding/acceleration/turns)
contributed most to this classification and provide specific recommendations.
"""
```

### Dominant Pattern Detection

AI can identify which rule clusters are firing:

```python
def identify_dominant_pattern(metrics):
    """Returns which behavior category dominates the low score"""

    patterns = []

    # Speeding dominance
    if metrics['OST'] > 0.25 or metrics['OSA'] > 5 or metrics['OSP'] > 8:
        patterns.append(("Excessive Speeding",
                        max(metrics['OST']*100, metrics['OSA'], metrics['OSP'])))

    # Acceleration dominance
    if metrics['SAA'] > 3 or metrics['GAA'] > 2:
        patterns.append(("Harsh Acceleration",
                        metrics['SAA'] + metrics['GAA']))

    # Braking dominance
    if metrics['GAN'] > 3.5:
        patterns.append(("Hard Braking", metrics['GAN']))

    # Turn dominance
    if metrics['BRA'] > 2 or metrics['BRP'] > 70:
        patterns.append(("Aggressive Turns",
                        max(metrics['BRA'], metrics['BRP']/30)))

    # Sort by severity
    patterns.sort(key=lambda x: x[1], reverse=True)

    return patterns[0][0] if patterns else "Mixed Behavior"

# Usage in prompt
dominant = identify_dominant_pattern(metrics)
prompt += f"\nPrimary Issue: {dominant}\n"
```

---

## References

- **jFuzzyLogic Documentation:** http://jfuzzylogic.sourceforge.net/
- **IEC 61131-7 Standard:** Fuzzy Control Language specification
- **Matlab Fuzzy Logic Toolbox:** http://www.mathworks.com/products/fuzzy-logic.html

---

## Changelog

**Version:** Based on driverprofile.fcl (modified BRP thresholds)
- BRP thresholds quadrupled from original (0-20° → 0-80°)
- Added LEO's suggested rules (19-21) for mixed speeding patterns
- Rules 17-18 modified to combine BRP with OSP (speeding + sharp turns)

**Last Updated:** 2026-01-28
