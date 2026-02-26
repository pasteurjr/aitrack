 ╭───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮              
     │ Plan: DataDrivr Integration with AITrack                                                                                                                          │              
     │                                                                                                                                                                   │              
     │ Task Overview                                                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Create a specification document and 90-minute implementation plan to integrate DataDrivr behavioral monitoring capabilities into AITrack vehicle tracking system. │              
     │                                                                                                                                                                   │              
     │ Deliverables:                                                                                                                                                     │              
     │ 1. espec_add_datadriver.md - Specification document with integration ideas                                                                                        │              
     │ 2. 90-minute implementation plan for simulator + frontend enhancements                                                                                            │              
     │                                                                                                                                                                   │              
     │ Context Summary                                                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ DataDrivr Mobile-App (Analyzed)                                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ Purpose: Mobile app for real-time driver behavior monitoring                                                                                                      │              
     │                                                                                                                                                                   │              
     │ Data Collected:                                                                                                                                                   │              
     │ - GPS coordinates (latitude, longitude, altitude)                                                                                                                 │              
     │ - Accelerometer data (harsh acceleration detection)                                                                                                               │              
     │ - Speed metrics (current, max, average)                                                                                                                           │              
     │ - Compass/Gyroscope (heading, turn analysis)                                                                                                                      │              
     │ - Trip metadata (duration, distance, timestamps)                                                                                                                  │              
     │                                                                                                                                                                   │              
     │ Behavioral Scoring (8 metrics, 0-100 scale):                                                                                                                      │              
     │ 1. Speed control (speeding violations)                                                                                                                            │              
     │ 2. Acceleration smoothness                                                                                                                                        │              
     │ 3. Braking quality (harsh braking detection)                                                                                                                      │              
     │ 4. Cornering analysis (curve speed/sharpness)                                                                                                                     │              
     │ 5. Distraction detection                                                                                                                                          │              
     │ 6. Time of day risk                                                                                                                                               │              
     │ 7. Fatigue detection                                                                                                                                              │              
     │ 8. Hazardous location awareness                                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ Overall Score: Weighted average of 8 metrics                                                                                                                      │              
     │ Real-time Alerts: Speed limit, harsh events, fuel consumption                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Gamification:                                                                                                                                                     │              
     │ - Points system (100-1000 per achievement)                                                                                                                        │              
     │ - Challenges (weekly, monthly, special)                                                                                                                           │              
     │ - Achievements with rarity levels                                                                                                                                 │              
     │ - Leaderboard/ranking                                                                                                                                             │              
     │                                                                                                                                                                   │              
     │ Current State: Mock data only, no backend integration, ready for MySQL                                                                                            │              
     │                                                                                                                                                                   │              
     │ DataDrivr Insurance-Web (Analyzed)                                                                                                                                │              
     │                                                                                                                                                                   │              
     │ Purpose: Analytics dashboard for insurance companies                                                                                                              │              
     │                                                                                                                                                                   │              
     │ Key Visualizations:                                                                                                                                               │              
     │ - Risk Distribution Charts                                                                                                                                        │              
     │ - Temporal Analysis with Event Markers                                                                                                                            │              
     │ - Multi-dimensional Radar Charts                                                                                                                                  │              
     │ - Behavioral Score Evolution                                                                                                                                      │              
     │ - Claims Processing Funnels                                                                                                                                       │              
     │ - Competitive Analysis                                                                                                                                            │              
     │ - Real-time Alert Panels                                                                                                                                          │              
     │                                                                                                                                                                   │              
     │ Analytics Modules:                                                                                                                                                │              
     │ 1. Behavioral Analysis (score trends, patterns)                                                                                                                   │              
     │ 2. Risk Assessment (predictive scoring)                                                                                                                           │              
     │ 3. Fraud Detection (anomaly detection)                                                                                                                            │              
     │ 4. Claims Processing (automation metrics)                                                                                                                         │              
     │ 5. Pricing Optimization (premium strategies)                                                                                                                      │              
     │ 6. Temporal Analysis (event timelines)                                                                                                                            │              
     │ 7. Personalized Coach (improvement suggestions)                                                                                                                   │              
     │ 8. Market Intelligence (competitive positioning)                                                                                                                  │              
     │                                                                                                                                                                   │              
     │ AITrack Current State (Known)                                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Architecture:                                                                                                                                                     │              
     │ - Socket Server (port 9000): Receives GPS from trackers                                                                                                           │              
     │ - REST API (port 5000): Serves vehicle positions                                                                                                                  │              
     │ - Frontend (React + Leaflet): Real-time map visualization                                                                                                         │              
     │ - Simulator: Generates test data for 10 vehicles                                                                                                                  │              
     │ - Database: MySQL (tracker/dirijabem)                                                                                                                             │              
     │                                                                                                                                                                   │              
     │ Protocols: Maxtrack, Suntech, Queclink                                                                                                                            │              
     │ Current Data: GPS position, speed, heading, ignition, battery                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Limitations:                                                                                                                                                      │              
     │ - No behavioral scoring                                                                                                                                           │              
     │ - No event detection (harsh braking, acceleration)                                                                                                                │              
     │ - Basic visualization (just position markers)                                                                                                                     │              
     │ - No driver analytics or insights                                                                                                                                 │              
     │                                                                                                                                                                   │              
     │ Integration Opportunities                                                                                                                                         │              
     │                                                                                                                                                                   │              
     │ High-Value Integrations                                                                                                                                           │              
     │                                                                                                                                                                   │              
     │ 1. Behavioral Scoring Layer                                                                                                                                       │              
     │ - Add 8-metric scoring system to tracked vehicles                                                                                                                 │              
     │ - Calculate scores based on GPS speed/heading changes                                                                                                             │              
     │ - Display color-coded vehicle markers (green=good, red=poor)                                                                                                      │              
     │ - Real-time score updates in frontend                                                                                                                             │              
     │                                                                                                                                                                   │              
     │ 2. Event Detection System                                                                                                                                         │              
     │ - Harsh acceleration: Speed increase > 15 km/h in 3 seconds                                                                                                       │              
     │ - Harsh braking: Speed decrease > 20 km/h in 3 seconds                                                                                                            │              
     │ - Speeding: Velocity > speed limit + 10 km/h                                                                                                                      │              
     │ - Sharp turns: Heading change > 45° at speed > 30 km/h                                                                                                            │              
     │                                                                                                                                                                   │              
     │ 3. Real-time Alert Dashboard                                                                                                                                      │              
     │ - Panel showing active alerts per vehicle                                                                                                                         │              
     │ - Event markers on map (icons for braking, acceleration, speeding)                                                                                                │              
     │ - Sound/visual notifications for critical events                                                                                                                  │              
     │ - Alert history timeline                                                                                                                                          │              
     │                                                                                                                                                                   │              
     │ 4. Trip Analytics                                                                                                                                                 │              
     │ - Trip summary with score breakdown                                                                                                                               │              
     │ - Route playback with event annotations                                                                                                                           │              
     │ - Comparative analytics (vehicle vs fleet average)                                                                                                                │              
     │ - Temporal analysis charts                                                                                                                                        │              
     │                                                                                                                                                                   │              
     │ 5. Gamification for Fleets                                                                                                                                        │              
     │ - Driver/vehicle leaderboard                                                                                                                                      │              
     │ - Safety achievements                                                                                                                                             │              
     │ - Monthly challenges (lowest harsh events)                                                                                                                        │              
     │ - Points-based rewards                                                                                                                                            │              
     │                                                                                                                                                                   │              
     │ 6. Predictive Insights                                                                                                                                            │              
     │ - Risk scoring per vehicle                                                                                                                                        │              
     │ - Maintenance prediction based on driving patterns                                                                                                                │              
     │ - Driver coaching recommendations                                                                                                                                 │              
     │ - Route optimization suggestions                                                                                                                                  │              
     │                                                                                                                                                                   │              
     │ 90-Minute Implementation Plan                                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Phase 1: Simulator Enhancements (30 minutes)                                                                                                                      │              
     │                                                                                                                                                                   │              
     │ Goal: Add behavioral event generation to simulator                                                                                                                │              
     │                                                                                                                                                                   │              
     │ File: simulator.py                                                                                                                                                │              
     │                                                                                                                                                                   │              
     │ Changes:                                                                                                                                                          │              
     │ 1. Add event detection logic:                                                                                                                                     │              
     │   - Calculate acceleration from speed deltas                                                                                                                      │              
     │   - Detect harsh braking events (random probability)                                                                                                              │              
     │   - Detect speeding (compare to configurable limit)                                                                                                               │              
     │   - Generate event objects with timestamp, type, severity                                                                                                         │              
     │ 2. Modify packet generation:                                                                                                                                      │              
     │   - Include event data in packets (extend protocol or use JSON metadata)                                                                                          │              
     │   - Add "behavioral_score" field (0-100)                                                                                                                          │              
     │   - Add "current_event" field (null or event type)                                                                                                                │              
     │ 3. Simulate realistic behavior patterns:                                                                                                                          │              
     │   - 80% "good" drivers (score 70-95)                                                                                                                              │              
     │   - 15% "moderate" drivers (score 50-70)                                                                                                                          │              
     │   - 5% "poor" drivers (score 20-50)                                                                                                                               │              
     │                                                                                                                                                                   │              
     │ Output: Enhanced simulator sending behavioral data                                                                                                                │              
     │                                                                                                                                                                   │              
     │ Phase 2: Backend Event Processing (20 minutes)                                                                                                                    │              
     │                                                                                                                                                                   │              
     │ Goal: Process and store behavioral events                                                                                                                         │              
     │                                                                                                                                                                   │              
     │ File: server/db_handler.py                                                                                                                                        │              
     │                                                                                                                                                                   │              
     │ Changes:                                                                                                                                                          │              
     │ 1. Create events table (if not exists):                                                                                                                           │              
     │ CREATE TABLE vehicle_events (                                                                                                                                     │              
     │   id INT AUTO_INCREMENT PRIMARY KEY,                                                                                                                              │              
     │   device_id VARCHAR(50),                                                                                                                                          │              
     │   event_type ENUM('harsh_accel', 'harsh_brake', 'speeding', 'sharp_turn'),                                                                                        │              
     │   severity ENUM('low', 'medium', 'high'),                                                                                                                         │              
     │   timestamp DATETIME,                                                                                                                                             │              
     │   latitude DOUBLE,                                                                                                                                                │              
     │   longitude DOUBLE,                                                                                                                                               │              
     │   speed FLOAT,                                                                                                                                                    │              
     │   score_impact INT                                                                                                                                                │              
     │ )                                                                                                                                                                 │              
     │ 2. Add event insertion function                                                                                                                                   │              
     │ 3. Calculate running behavioral score per vehicle                                                                                                                 │              
     │                                                                                                                                                                   │              
     │ File: server/protocol_parsers.py                                                                                                                                  │              
     │                                                                                                                                                                   │              
     │ Changes:                                                                                                                                                          │              
     │ - Parse behavioral metadata from packets                                                                                                                          │              
     │ - Extract event information                                                                                                                                       │              
     │ - Pass to db_handler                                                                                                                                              │              
     │                                                                                                                                                                   │              
     │ File: server/api.py                                                                                                                                               │              
     │                                                                                                                                                                   │              
     │ New Endpoints:                                                                                                                                                    │              
     │ - GET /api/vehicles/<id>/score - Current behavioral score                                                                                                         │              
     │ - GET /api/vehicles/<id>/events - Recent events                                                                                                                   │              
     │ - GET /api/fleet/leaderboard - Top performers                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Phase 3: Frontend Visualizations (40 minutes)                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Goal: Display behavioral data on map and dashboard                                                                                                                │              
     │                                                                                                                                                                   │              
     │ File: frontend/src/components/MapComponent.tsx                                                                                                                    │              
     │                                                                                                                                                                   │              
     │ Changes:                                                                                                                                                          │              
     │ 1. Color-code vehicle markers by score:                                                                                                                           │              
     │   - Green (score 75+): Good                                                                                                                                       │              
     │   - Yellow (score 50-74): Moderate                                                                                                                                │              
     │   - Red (score < 50): Poor                                                                                                                                        │              
     │ 2. Add event markers on map:                                                                                                                                      │              
     │   - Icons for harsh braking (brake symbol)                                                                                                                        │              
     │   - Icons for harsh acceleration (lightning)                                                                                                                      │              
     │   - Icons for speeding (speed sign)                                                                                                                               │              
     │   - Click to show event details                                                                                                                                   │              
     │ 3. Vehicle popup enhancements:                                                                                                                                    │              
     │   - Show current behavioral score                                                                                                                                 │              
     │   - Show recent events count                                                                                                                                      │              
     │   - Link to detailed analytics                                                                                                                                    │              
     │                                                                                                                                                                   │              
     │ New Component: BehavioralDashboard.tsx                                                                                                                            │              
     │                                                                                                                                                                   │              
     │ Features:                                                                                                                                                         │              
     │ 1. Fleet Overview Panel:                                                                                                                                          │              
     │   - Average fleet score                                                                                                                                           │              
     │   - Total events today                                                                                                                                            │              
     │   - Top 3 performers                                                                                                                                              │              
     │   - Bottom 3 performers                                                                                                                                           │              
     │ 2. Real-time Alerts Panel:                                                                                                                                        │              
     │   - List of active alerts                                                                                                                                         │              
     │   - Severity indicators                                                                                                                                           │              
     │   - Vehicle name/plate                                                                                                                                            │              
     │   - Timestamp                                                                                                                                                     │              
     │ 3. Event Timeline:                                                                                                                                                │              
     │   - Horizontal timeline showing last 10 events                                                                                                                    │              
     │   - Color-coded by type                                                                                                                                           │              
     │   - Filterable by vehicle                                                                                                                                         │              
     │ 4. Score Distribution Chart:                                                                                                                                      │              
     │   - Bar chart showing score distribution                                                                                                                          │              
     │   - Categories: Excellent, Good, Moderate, Poor                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ File: frontend/src/App.tsx                                                                                                                                        │              
     │                                                                                                                                                                   │              
     │ Changes:                                                                                                                                                          │              
     │ - Add BehavioralDashboard component                                                                                                                               │              
     │ - Add toggle to show/hide event markers                                                                                                                           │              
     │ - Add filter controls (show only poor drivers, etc.)                                                                                                              │              
     │                                                                                                                                                                   │              
     │ Specification Document Structure                                                                                                                                  │              
     │                                                                                                                                                                   │              
     │ File: espec_add_datadriver.md                                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Section 1: Executive Summary                                                                                                                                      │              
     │                                                                                                                                                                   │              
     │ - Overview of DataDrivr capabilities                                                                                                                              │              
     │ - Integration benefits for AITrack                                                                                                                                │              
     │ - Expected value proposition                                                                                                                                      │              
     │                                                                                                                                                                   │              
     │ Section 2: DataDrivr Architecture Analysis                                                                                                                        │              
     │                                                                                                                                                                   │              
     │ - Mobile app sensor data collection                                                                                                                               │              
     │ - 8-metric behavioral scoring system                                                                                                                              │              
     │ - Insurance analytics platform features                                                                                                                           │              
     │ - Current limitations and opportunities                                                                                                                           │              
     │                                                                                                                                                                   │              
     │ Section 3: AITrack Current State                                                                                                                                  │              
     │                                                                                                                                                                   │              
     │ - Architecture overview                                                                                                                                           │              
     │ - Data flow diagram                                                                                                                                               │              
     │ - Existing capabilities                                                                                                                                           │              
     │ - Integration readiness                                                                                                                                           │              
     │                                                                                                                                                                   │              
     │ Section 4: Integration Strategy                                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ 4.1 Data Layer Integration                                                                                                                                        │              
     │ - Database schema extensions                                                                                                                                      │              
     │ - Event storage design                                                                                                                                            │              
     │ - Scoring calculation engine                                                                                                                                      │              
     │                                                                                                                                                                   │              
     │ 4.2 Behavioral Scoring System                                                                                                                                     │              
     │ - Metric definitions adapted for fleet tracking                                                                                                                   │              
     │ - Scoring algorithm implementation                                                                                                                                │              
     │ - Real-time score updates                                                                                                                                         │              
     │                                                                                                                                                                   │              
     │ 4.3 Event Detection Engine                                                                                                                                        │              
     │ - Harsh acceleration detection                                                                                                                                    │              
     │ - Harsh braking detection                                                                                                                                         │              
     │ - Speeding detection                                                                                                                                              │              
     │ - Sharp turn detection                                                                                                                                            │              
     │ - Custom event types                                                                                                                                              │              
     │                                                                                                                                                                   │              
     │ 4.4 Frontend Enhancements                                                                                                                                         │              
     │ - Behavioral dashboard design                                                                                                                                     │              
     │ - Event visualization on map                                                                                                                                      │              
     │ - Analytics charts and graphs                                                                                                                                     │              
     │ - Alert notification system                                                                                                                                       │              
     │                                                                                                                                                                   │              
     │ Section 5: Use Cases                                                                                                                                              │              
     │                                                                                                                                                                   │              
     │ 5.1 Fleet Management                                                                                                                                              │              
     │ - Monitor driver safety across fleet                                                                                                                              │              
     │ - Identify high-risk drivers                                                                                                                                      │              
     │ - Coaching and training prioritization                                                                                                                            │              
     │                                                                                                                                                                   │              
     │ 5.2 Insurance Integration                                                                                                                                         │              
     │ - Risk-based premium calculation                                                                                                                                  │              
     │ - Claims validation (correlation with events)                                                                                                                     │              
     │ - Fraud detection support                                                                                                                                         │              
     │                                                                                                                                                                   │              
     │ 5.3 Maintenance Prediction                                                                                                                                        │              
     │ - Correlate harsh driving with vehicle wear                                                                                                                       │              
     │ - Predictive maintenance scheduling                                                                                                                               │              
     │ - Cost optimization                                                                                                                                               │              
     │                                                                                                                                                                   │              
     │ 5.4 Route Optimization                                                                                                                                            │              
     │ - Identify hazardous routes                                                                                                                                       │              
     │ - Suggest safer alternatives                                                                                                                                      │              
     │ - Traffic pattern analysis                                                                                                                                        │              
     │                                                                                                                                                                   │              
     │ Section 6: Technical Implementation Roadmap                                                                                                                       │              
     │                                                                                                                                                                   │              
     │ Phase 1: Foundation (1-2 weeks)                                                                                                                                   │              
     │ - Database schema updates                                                                                                                                         │              
     │ - Basic event detection in simulator                                                                                                                              │              
     │ - API endpoints for behavioral data                                                                                                                               │              
     │                                                                                                                                                                   │              
     │ Phase 2: Core Features (2-3 weeks)                                                                                                                                │              
     │ - Real-time scoring engine                                                                                                                                        │              
     │ - Event visualization on map                                                                                                                                      │              
     │ - Basic behavioral dashboard                                                                                                                                      │              
     │                                                                                                                                                                   │              
     │ Phase 3: Advanced Analytics (3-4 weeks)                                                                                                                           │              
     │ - Temporal analysis charts                                                                                                                                        │              
     │ - Predictive insights                                                                                                                                             │              
     │ - Driver coaching suggestions                                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Phase 4: Gamification (1-2 weeks)                                                                                                                                 │              
     │ - Leaderboard system                                                                                                                                              │              
     │ - Achievement badges                                                                                                                                              │              
     │ - Challenge framework                                                                                                                                             │              
     │                                                                                                                                                                   │              
     │ Phase 5: Integration & Testing (1-2 weeks)                                                                                                                        │              
     │ - End-to-end testing                                                                                                                                              │              
     │ - Performance optimization                                                                                                                                        │              
     │ - Documentation                                                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ Section 7: Data Flow Diagrams                                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ - Current AITrack data flow                                                                                                                                       │              
     │ - Proposed enhanced data flow                                                                                                                                     │              
     │ - Event detection pipeline                                                                                                                                        │              
     │ - Scoring calculation workflow                                                                                                                                    │              
     │                                                                                                                                                                   │              
     │ Section 8: API Specifications                                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ - New endpoint definitions                                                                                                                                        │              
     │ - Request/response formats                                                                                                                                        │              
     │ - WebSocket events for real-time updates                                                                                                                          │              
     │                                                                                                                                                                   │              
     │ Section 9: Security & Privacy Considerations                                                                                                                      │              
     │                                                                                                                                                                   │              
     │ - Driver data privacy (LGPD compliance)                                                                                                                           │              
     │ - Access control for behavioral data                                                                                                                              │              
     │ - Audit logging                                                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ Section 10: Performance Considerations                                                                                                                            │              
     │                                                                                                                                                                   │              
     │ - Real-time processing requirements                                                                                                                               │              
     │ - Database optimization strategies                                                                                                                                │              
     │ - Caching for score calculations                                                                                                                                  │              
     │ - Scalability for large fleets                                                                                                                                    │              
     │                                                                                                                                                                   │              
     │ Section 11: Future Enhancements                                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ - Machine learning for predictive scoring                                                                                                                         │              
     │ - Integration with insurance APIs                                                                                                                                 │              
     │ - Mobile app for drivers                                                                                                                                          │              
     │ - Advanced fraud detection                                                                                                                                        │              
     │ - Route recommendation engine                                                                                                                                     │              
     │                                                                                                                                                                   │              
     │ Critical Files                                                                                                                                                    │              
     │                                                                                                                                                                   │              
     │ New Files:                                                                                                                                                        │              
     │ - espec_add_datadriver.md - Main specification document                                                                                                           │              
     │ - frontend/src/components/BehavioralDashboard.tsx - Dashboard component                                                                                           │              
     │ - frontend/src/components/EventMarker.tsx - Map event markers                                                                                                     │              
     │ - frontend/src/hooks/useBehavioralData.ts - Data fetching hook                                                                                                    │              
     │ - server/behavioral_engine.py - Scoring and event detection logic                                                                                                 │              
     │                                                                                                                                                                   │              
     │ Modified Files:                                                                                                                                                   │              
     │ - simulator.py - Add event generation                                                                                                                             │              
     │ - server/db_handler.py - Event storage functions                                                                                                                  │              
     │ - server/api.py - New API endpoints                                                                                                                               │              
     │ - frontend/src/components/MapComponent.tsx - Enhanced visualization                                                                                               │              
     │ - frontend/src/App.tsx - Dashboard integration                                                                                                                    │              
     │ - CLAUDE.md - Document new features                                                                                                                               │              
     │                                                                                                                                                                   │              
     │ Verification Steps                                                                                                                                                │              
     │                                                                                                                                                                   │              
     │ 1. Run Enhanced Simulator                                                                                                                                         │              
     │ python simulator.py                                                                                                                                               │              
     │ - Verify events are being generated                                                                                                                               │              
     │ - Check console logs for event types                                                                                                                              │              
     │ - Confirm behavioral scores vary across vehicles                                                                                                                  │              
     │                                                                                                                                                                   │              
     │ 2. Check Database                                                                                                                                                 │              
     │ mysql -u root -p tracker -e "SELECT * FROM vehicle_events ORDER BY timestamp DESC LIMIT 10;"                                                                      │              
     │ - Verify events are being stored                                                                                                                                  │              
     │ - Confirm data integrity                                                                                                                                          │              
     │                                                                                                                                                                   │              
     │ 3. Test API Endpoints                                                                                                                                             │              
     │ curl http://localhost:5000/api/vehicles/SIM-1000/score                                                                                                            │              
     │ curl http://localhost:5000/api/vehicles/SIM-1000/events                                                                                                           │              
     │ curl http://localhost:5000/api/fleet/leaderboard                                                                                                                  │              
     │ - Verify JSON responses                                                                                                                                           │              
     │ - Check data accuracy                                                                                                                                             │              
     │                                                                                                                                                                   │              
     │ 4. Frontend Testing                                                                                                                                               │              
     │ cd frontend && npm start                                                                                                                                          │              
     │ - Open http://localhost:3000                                                                                                                                      │              
     │ - Verify color-coded vehicle markers                                                                                                                              │              
     │ - Check event markers appear on map                                                                                                                               │              
     │ - Confirm behavioral dashboard displays data                                                                                                                      │              
     │ - Test alert notifications                                                                                                                                        │              
     │                                                                                                                                                                   │              
     │ 5. End-to-End Scenario                                                                                                                                            │              
     │ - Start simulator with 10 vehicles                                                                                                                                │              
     │ - Watch for events in real-time                                                                                                                                   │              
     │ - Verify map updates immediately                                                                                                                                  │              
     │ - Check leaderboard ranking changes                                                                                                                               │              
     │ - Confirm alerts trigger for severe events                                                                                                                        │              
     │                                                                                                                                                                   │              
     │ Success Criteria                                                                                                                                                  │              
     │                                                                                                                                                                   │              
     │ 90-Minute Demo Goals:                                                                                                                                             │              
     │ 1. Simulator generates realistic behavioral events                                                                                                                │              
     │ 2. Frontend displays color-coded vehicles by score                                                                                                                │              
     │ 3. Event markers appear on map with icons                                                                                                                         │              
     │ 4. Basic behavioral dashboard shows:                                                                                                                              │              
     │   - Fleet average score                                                                                                                                           │              
     │   - Recent events list                                                                                                                                            │              
     │   - Top/bottom performers                                                                                                                                         │              
     │ 5. At least one real-time alert fires during demo                                                                                                                 │              
     │                                                                                                                                                                   │              
     │ Document Goals:                                                                                                                                                   │              
     │ 1. Clear explanation of integration benefits                                                                                                                      │              
     │ 2. Technical implementation details                                                                                                                               │              
     │ 3. Realistic timelines for full implementation                                                                                                                    │              
     │ 4. Actionable roadmap for development                                                                                                                             │              
     │ 5. Professional diagrams and examples                                                                                                                             │              
     │                                                                                                                                                                   │              
     │ Trade-offs & Decisions                                                                                                                                            │              
     │                                                                                                                                                                   │              
     │ Decision 1: Event Detection Logic                                                                                                                                 │              
     │ - Choice: Calculate from GPS speed/heading deltas                                                                                                                 │              
     │ - Alternative: Require actual accelerometer data                                                                                                                  │              
     │ - Rationale: Works with existing tracker hardware, no new sensors needed                                                                                          │              
     │                                                                                                                                                                   │              
     │ Decision 2: Scoring Algorithm                                                                                                                                     │              
     │ - Choice: Simplified 3-metric system (speed, braking, acceleration)                                                                                               │              
     │ - Alternative: Full 8-metric DataDrivr system                                                                                                                     │              
     │ - Rationale: Faster implementation, can expand later                                                                                                              │              
     │                                                                                                                                                                   │              
     │ Decision 3: Real-time vs Batch Processing                                                                                                                         │              
     │ - Choice: Real-time event detection and scoring                                                                                                                   │              
     │ - Alternative: Batch process at trip end                                                                                                                          │              
     │ - Rationale: Better UX, immediate feedback, aligns with monitoring use case                                                                                       │              
     │                                                                                                                                                                   │              
     │ Decision 4: Frontend Architecture                                                                                                                                 │              
     │ - Choice: New BehavioralDashboard component alongside map                                                                                                         │              
     │ - Alternative: Integrate everything into existing map                                                                                                             │              
     │ - Rationale: Separation of concerns, easier to maintain                                                                                                           │              
     │                                                                                                                                                                   │              
     │ Decision 5: Database Design                                                                                                                                       │              
     │ - Choice: Separate events table, not embedded in localizacao                                                                                                      │              
     │ - Alternative: Add event fields to existing tables                                                                                                                │              
     │ - Rationale: Better performance for queries, cleaner schema                                                                                                       │              
     │                                                                                                                                                                   │              
     │ Timeline Breakdown (90 minutes)                                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ Minutes 0-10: Setup & Planning                                                                                                                                    │              
     │ - Review current code                                                                                                                                             │              
     │ - Set up development environment                                                                                                                                  │              
     │ - Create feature branch                                                                                                                                           │              
     │                                                                                                                                                                   │              
     │ Minutes 10-30: Simulator Enhancement                                                                                                                              │              
     │ - Add event generation logic (15 min)                                                                                                                             │              
     │ - Test simulator output (5 min)                                                                                                                                   │              
     │                                                                                                                                                                   │              
     │ Minutes 30-50: Backend Changes                                                                                                                                    │              
     │ - Add events table migration (5 min)                                                                                                                              │              
     │ - Implement event storage (10 min)                                                                                                                                │              
     │ - Create API endpoints (5 min)                                                                                                                                    │              
     │                                                                                                                                                                   │              
     │ Minutes 50-90: Frontend Implementation                                                                                                                            │              
     │ - Color-coded markers (10 min)                                                                                                                                    │              
     │ - Event markers on map (10 min)                                                                                                                                   │              
     │ - Basic behavioral dashboard (15 min)                                                                                                                             │              
     │ - Real-time alerts panel (5 min)                                                                                                                                  │              
     │                                                                                                                                                                   │              
     │ Minutes 90: Testing & Demo Prep                                                                                                                                   │              
     │ - End-to-end test                                                                                                                                                 │              
     │ - Prepare demo script                                                                                                                                             │              
     │ - Take screenshots                                                                                                                                                │              
     │                                                                                                                                                                   │              
     │ Notes                                                                                                                                                             │              
     │                                                                                                                                                                   │              
     │ Expertise Applied (Vehicle Tracking Specialist Perspective):                                                                                                      │              
     │                                                                                                                                                                   │              
     │ 1. Event Detection: Standard industry practice for fleet management systems. Thresholds based on real-world fleet operator requirements.                          │              
     │ 2. Scoring System: Simplified from insurance-grade (8 metrics) to fleet-grade (3 metrics) focusing on actionable insights for fleet managers.                     │              
     │ 3. Real-time Processing: Critical for vehicle monitoring use case. Batch processing acceptable for insurance analytics but not for tracking.                      │              
     │ 4. Visualization Priorities: Map-first design reflects fleet operator workflows. Dashboard supplements map, not replaces it.                                      │              
     │ 5. Scalability Consideration: Design supports 100-1000 vehicles per instance. Event storage with time-based partitioning for large fleets.                        │              
     │ 6. Integration Path: Gradual enhancement approach allows AITrack to maintain current functionality while adding DataDrivr intelligence layer by layer.            │              
     ╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯    