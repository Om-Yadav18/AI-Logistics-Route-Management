# SIH26002 — AI-Based Smart Logistics & Accessibility Intelligence Platform

**Team:** Cognitive Coders  
**SIH Problem Statement:** SIH26002  
**Theme:** Transportation & Logistics  
**Region:** North Eastern Region (NER)

---

## 1. What We Are Building

We are building an **AI + GIS based logistics intelligence platform** for managing essential-goods movement in areas where roads can become unsafe, blocked, or inaccessible and where Internet connectivity may be poor.

The system combines:

- Satellite data
- Weather data
- Map / GIS road data
- GPS / vehicle data
- Geo-tagged field reports
- Disruption detection
- Road-segment status
- Risk-aware route planning
- Alternate route generation
- Offline / low-connectivity field operation

### Core idea

> **The system should not only find a route. It should understand changing road conditions, identify risky or blocked road segments, recommend a suitable alternate route, and keep operating in low-connectivity areas.**

---

# 2. Product Architecture

Our product has two major operational sides:

1. **Cloud / Central Side** — Internet-connected intelligence, data processing, disruption detection, GIS processing and global state.
2. **Field Side** — Local edge infrastructure that allows nearby users to continue operating with little or no Internet.

The user-facing mobile application will be a **real Android app**, built with Flutter.

A web dashboard can be added for central/control-room users.

---

# 3. High-Level Architecture

```text
                         CLOUD / CENTRAL SIDE
                            (Internet)

      Satellite        Weather        Map / GIS       GPS / Reports
          |                |               |                |
          +----------------+---------------+----------------+
                                   |
                                   v
                        +-----------------------+
                        | Data Ingestion        |
                        | Validation / Processing|
                        +-----------+-----------+
                                    |
                                    v
                        +-----------------------+
                        | Disruption Detection  |
                        | / Risk Analysis       |
                        +-----------+-----------+
                                    |
                                    v
                        +-----------------------+
                        | GIS Processing        |
                        | Match disruption to   |
                        | affected road segment |
                        +-----------+-----------+
                                    |
                                    v
                        +-----------------------+
                        | Road Graph            |
                        | Update                |
                        +-----------+-----------+
                                    |
                                    v
                        +-----------------------+
                        | Route Engine          |
                        | Risk + ETA +          |
                        | Alternate Routes      |
                        +-----------+-----------+
                                    |
                                    v
                        +-----------------------+
                        | Central Backend       |
                        | Versioned Road State  |
                        | Routes + Alerts       |
                        +-----------+-----------+
                                    |
                                  SYNC
                                    |
                                    v

                         FIELD / EDGE SIDE

                  +--------------------------------+
                  | Local Field Server             |
                  | Depot / Checkpoint / Camp      |
                  | Local DB + Cached Data         |
                  | Sync Manager                   |
                  +---------------+----------------+
                                  |
                              Wi-Fi / LAN
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
             +-------------+             +-------------+
             | Flutter     |             | Flutter     |
             | Android App |             | Android App |
             | Driver      |             | Field User  |
             +-------------+             +-------------+
```

---

# 4. Cloud / Central Side

The central side requires Internet connectivity.

### Data Sources

- **Satellite data** — environmental/infrastructure information.
- **Weather data** — rainfall and other weather conditions affecting road risk.
- **Map/GIS data** — road network and geographic information.
- **GPS/vehicle data** — vehicle location and movement.
- **Field reports** — geo-tagged incidents such as blockage, flooding or damage.

### Data flow

```text
Data Sources
     ↓
Ingestion
     ↓
Validation
     ↓
Normalization
     ↓
Processed Data
```

---

# 5. Disruption Detection

The system identifies possible disruptions such as:

- Flooding
- Landslides
- Heavy-rainfall related risk
- Road blockage
- Road damage
- Other accessibility disruptions

A disruption record should contain:

```text
Location
Type
Severity / Risk
Confidence
Timestamp
Source
```

For the prototype, start with **rules + simulated/available data**. Add ML where sufficient data exists.

---

# 6. GIS: Match Disruption to Road Segment

The system must determine which road segment is affected.

```text
Incident coordinates
       ↓
GIS processing
       ↓
Affected road segment
       ↓
Road ID = R102
```

Example:

```text
Road ID: R102
Status: BLOCKED
Reason: Landslide
Risk: HIGH
Updated: 14:32
Confidence: 0.91
```

---

# 7. Road Graph

The road network is represented as a graph.

```text
A -------- B
|          |
|          |
C -------- D
      |
      E
```

Each road segment/edge can contain:

- Distance
- Travel time
- Accessibility status
- Risk score
- Disruption type
- Last updated time

When a road becomes blocked or risky, its graph state is updated.

```text
Before:

A ---- B ---- C ---- D
       OPEN


After:

A ---- B    X    C ---- D
            |
         BLOCKED
```

---

# 8. Route Engine

The route engine computes suitable routes using the current road state.

The goal is not simply **the shortest route**.

The goal is a route considering:

- Accessibility
- Risk
- Travel time
- Current road status

Example:

```text
Route A
Distance: 100 km
ETA: 3h 30m
Risk: HIGH
Status: Not recommended

Route B
Distance: 115 km
ETA: 3h 55m
Risk: LOW
Status: Recommended
```

The route engine must support:

- Blocked-road avoidance
- Risk-aware routing
- Alternate route generation
- ETA calculation

---

# 9. Central Backend

The central backend manages:

- Road state
- Road risk
- Disruptions
- Routes
- Alerts
- Field reports
- Vehicle/location data
- Synchronization
- Version information

### Versioned road state

```text
Central Road Graph Version: 1842
Field Server Version:       1837
```

When connectivity becomes available:

```text
Field 1837
    ↓
Sync
    ↓
Central 1842
    ↓
Receive required updates
    ↓
Field becomes 1842
```

---

# 10. Field / Edge Side

The field side is designed for little or no Internet connectivity.

A local server can be installed at:

- Depot
- Checkpoint
- Relief camp

The field server maintains locally available:

- Cached road state
- Cached routes
- Recent alerts
- Relevant map data
- Local incident reports
- Synchronization state

```text
Central Server
      ↓ Internet when available
Local Field Server
      ↓ Wi-Fi / LAN
Flutter Android App
```

---

# 11. Mobile Application

## Primary Client: Android App

The primary field application will be a **Flutter Android application** for:

- Drivers
- Field officers
- Logistics operators

Main screens:

```text
1. Login
2. Main Map
3. Route Details
4. Disruption Alerts
5. Report Incident
6. Vehicle / Mission Status
7. Offline / Sync Status
8. Settings
```

Main flow:

```text
Login
  ↓
Dashboard / Map
  ├── View road status
  ├── View disruption alert
  ├── View recommended route
  ├── Report incident
  └── View sync/offline status
```

---

# 12. Offline Mobile Operation

```text
Internet Available
        ↓
Central Server
        ↓
      Sync
        ↓
Field Server
        ↓ Wi-Fi
Flutter App
```

When Internet is unavailable:

```text
Internet = OFF

Flutter App
     ↓ Wi-Fi
Field Server
     ↓
Cached / Local Data
```

The app should continue to show locally synchronized information and allow relevant offline actions such as incident reporting, which can be synchronized later.

---

# 13. Synchronization

### Cloud → Field

```text
Central Server
      ↓
Sync API
      ↓
Field Server
      ↓
Local database/cache
```

### Field → Cloud

```text
Offline Incident
      ↓
Stored locally
      ↓
Internet returns
      ↓
Sync Manager
      ↓
Central Server
```

Updates should carry metadata such as:

- Version
- Timestamp
- Source
- Record ID
- Update type
- Synchronization status

---

# 14. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Mobile App | **Flutter + Dart** | Primary Android application |
| Web Dashboard | **React.js** | Central/control-room dashboard |
| Backend | **Python + FastAPI** | APIs and business logic |
| Central DB | **PostgreSQL + PostGIS** | Spatial and application data |
| Field DB | **SQLite initially** | Local cached/offline data |
| AI/ML | **Python + Scikit-learn / PyTorch** | Risk/disruption intelligence |
| Maps/GIS | **OpenStreetMap + PostGIS** | Road network and spatial processing |
| Routing | **OSRM / GraphHopper / custom graph layer** | Route calculation |
| Realtime | **WebSockets / Redis where required** | Live updates |
| Infrastructure | **Docker + Cloud** | Deployment |
| UI Design | **Stitch + Figma** | Design/prototyping |
| AI Coding | **Antigravity / AI coding agent** | Development assistance |
| Version Control | **GitHub** | Source code and collaboration |

Technology choices can be changed later only after the team documents the reason and impact.

---

# 15. How We Use AI Tools

### Stitch

Use for:

- Initial UI exploration
- Screen ideas
- UX variations
- Rapid interface prototypes

### Figma

Use for:

- Final UI/UX
- Design system
- Shared team design
- Screen specifications

### Antigravity / AI Coding Agent

Use for:

- Project scaffolding
- Code generation
- Implementation assistance
- Refactoring
- Tests
- Debugging

AI-generated code must be reviewed and understood by the team before merging.

### GitHub

GitHub is the **single source of truth** for:

- Source code
- Architecture
- Documentation
- Issues
- Pull requests
- Collaboration

---

# 16. Recommended Development Order

## Phase 1 — Product UI

**Stitch → Figma**

Design and finalize:

```text
Login
Map
Route
Alert
Incident Report
Offline / Sync
```

## Phase 2 — Flutter App

Build the Android app using mock data.

```text
Flutter App
├── Login
├── Map
├── Routes
├── Alerts
├── Incident Report
└── Offline State
```

## Phase 3 — Backend

Build:

```text
Flutter
   ↓
FastAPI
   ↓
PostgreSQL + PostGIS
```

Initial APIs:

```text
GET  /roads
GET  /roads/{id}
GET  /routes
GET  /alerts
POST /incidents
POST /locations
POST /sync
```

## Phase 4 — Road Graph + Routing

```text
Road Network
     ↓
Road Graph
     ↓
Block / penalize road
     ↓
Recalculate
     ↓
Alternate Route
```

## Phase 5 — Field Server

```text
Cloud
  ↓
Sync
  ↓
Field Server
  ↓ Wi-Fi/LAN
Flutter App
```

Test with the Internet physically disconnected.

## Phase 6 — Disruption Engine

```text
Weather
Satellite
Field Reports
Historical / simulated data
       ↓
Disruption Engine
       ↓
Affected Road Segment
       ↓
Road Graph Update
       ↓
Route Engine
```

## Phase 7 — AI / ML

After the deterministic pipeline works, introduce ML where it provides measurable value.

---

# 17. Core End-to-End Flow

```text
Data Source
    ↓
Ingestion
    ↓
Disruption Detection
    ↓
GIS Road Segment Matching
    ↓
Road Graph Update
    ↓
Route Engine
    ↓
Central Server
    │
    │ sync whenever connectivity exists
    ↓
Field Server
    │
    │ local Wi-Fi / LAN
    ↓
Flutter Android App
    ↓
Alert + Alternate Route
    ↓
Logistics User
```

---

# 18. Offline Incident Flow

Critical scenario:

> A field officer discovers a blocked road while there is no Internet.

```text
Field Officer
      ↓
Flutter App
      ↓
Create Incident
      ↓
GPS + Type + Description + Photo
      ↓
Local Storage
      ↓
Field Server
      ↓
Internet unavailable
      X
      ↓
Internet returns
      ↓
Sync Manager
      ↓
Central Server
      ↓
Validation / Processing
      ↓
Road Segment Update
      ↓
Route Recalculation
```

---

# 19. Example SIH Demo Scenario

### Initial state

```text
Warehouse
    ↓
Road R101
    ↓
Road R102
    ↓
Relief Camp
```

Initial route:

```text
Route: R101 → R102
Risk: Low
ETA: 4h 10m
```

### Disruption

A landslide is reported near R102.

```text
Field Report
     ↓
GPS coordinates
     ↓
GIS identifies R102
     ↓
R102 = BLOCKED
```

### Recalculation

```text
Original:
R101 → R102
       X
     BLOCKED

Alternate:
R101 → R103 → R104 → Relief Camp
```

The app shows:

```text
⚠ ROAD DISRUPTION

Road R102 is blocked.

Reason:
Landslide

Recommended alternate:
R101 → R103 → R104

ETA:
4h 45m
```

Then disconnect Internet and demonstrate that the field application continues to access locally synchronized information.

Reconnect Internet and demonstrate synchronization back to the central server.

---

# 20. MVP Definition

The first working prototype must prove this loop:

```text
Disruption
    ↓
Affected Road Segment
    ↓
Road Graph Update
    ↓
Alternate Route
    ↓
Central Server
    ↓
Field Server
    ↓
Offline/Local Mobile App
    ↓
Logistics User
```

We do not need to build the entire real-world NER logistics ecosystem for the first MVP. A small simulated region is enough to prove the architecture.

---

# 21. GitHub Project Structure

```text
AI-Logistics-Route-Management/
│
├── README.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
│
├── mobile-app/
│   └── flutter/
│
├── web-dashboard/
│   └── react/
│
├── backend/
│   └── fastapi/
│
├── field-server/
│   └── edge/
│
├── route-engine/
│
├── ai-ml/
│
├── data/
│
├── docs/
│
├── docker/
│
└── tests/
```

---

# 22. Team Development Rule

Before implementing any module, define:

1. What data enters it?
2. What processing happens?
3. What output does it produce?
4. Which module consumes that output?
5. What API/data contract is required?
6. What happens if Internet is unavailable?
7. How is the state synchronized later?
8. How will the module be tested?

No teammate should build an isolated feature without defining how it connects to the rest of the system.

---

# 23. Current Technology Decision

```text
Mobile App       → Flutter
Web Dashboard    → React.js
Central Backend  → FastAPI
Central DB       → PostgreSQL + PostGIS
Field DB         → SQLite initially
AI/ML            → Python + Scikit-learn / PyTorch
Maps/GIS         → OpenStreetMap + PostGIS
Routing          → Route-engine layer
Realtime         → WebSockets / Redis where required
Infrastructure   → Docker + Cloud
Design           → Stitch + Figma
AI Coding        → Antigravity / AI coding agent
Version Control  → GitHub
```

This is the current project baseline.

---

# 24. Project Principle

> **We are building a resilient logistics decision-support system — not just a map or navigation application.**

The platform understands changing road accessibility, detects disruptions, maps them to road segments, updates the road graph, computes suitable alternate routes, and distributes the latest usable information to logistics users through a mobile application and local field infrastructure.

---

## Current Architecture in One Line

**Cloud Data → Disruption Detection → GIS Road Matching → Road Graph → Risk-Aware Route Engine → Central Server → Sync → Field Edge Server → Local Wi-Fi/LAN → Flutter Android App → Alert + Alternate Route**
