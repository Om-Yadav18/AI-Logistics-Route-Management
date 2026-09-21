# SIH26002 --- AI-Based Smart Logistics & Accessibility Intelligence Platform

**Team:** Cognitive Coders\
**SIH Problem Statement:** SIH26002\
**Theme:** Transportation & Logistics\
**Region:** North Eastern Region (NER)

------------------------------------------------------------------------

## 1. What We Are Building

We are building an **AI + GIS based logistics intelligence platform**
for managing essential-goods movement in areas where roads can become
unsafe, blocked, or inaccessible and where Internet connectivity may be
poor.

The system combines:

-   Satellite data
-   Weather data
-   Map / GIS road data
-   GPS / vehicle data
-   Geo-tagged field reports
-   Disruption detection
-   Road-segment status
-   Risk-aware route planning
-   Alternate route generation
-   Offline-first field operation

The key idea is:

> **The system should not only find a route. It should understand
> changing road conditions, identify risky or blocked road segments,
> recommend an alternate route, and keep working in low-connectivity
> areas.**

------------------------------------------------------------------------

# 2. Updated System Architecture

Our system is divided into two major sides:

1.  **Cloud / Central Side** --- Internet-connected intelligence and
    global data processing.
2.  **Field Side** --- Local edge infrastructure that continues
    operating with little or no Internet.

``` text
                    CLOUD / CENTRAL SIDE
                       (needs Internet)

 Satellite + Weather + Map/GIS Data
                  |
                  v
        +------------------------+
        | Data Ingestion         |
        | Processing             |
        | Validation             |
        +-----------+------------+
                    |
                    v
        +------------------------+
        | Disruption Detection   |
        | / Risk Analysis        |
        +-----------+------------+
                    |
                    v
        +------------------------+
        | GIS Processing         |
        | Match disruption to    |
        | affected road segment  |
        +-----------+------------+
                    |
                    v
        +------------------------+
        | Road Graph Update      |
        | Road status / risk     |
        +-----------+------------+
                    |
                    v
        +------------------------+
        | Route Engine           |
        | Alternate routes       |
        | Risk + ETA             |
        +-----------+------------+
                    |
                    v
        +------------------------+
        | Central Server         |
        | Versioned road status  |
        | Routes + alerts        |
        +-----------+------------+
                    |
                    | Synchronizes
                    | whenever a
                    | network link exists
                    v

                    FIELD SIDE
              (little or no Internet)

        +-----------------------------+
        | Local Field / Edge Server   |
        |                             |
        | Depot / Checkpoint / Camp   |
        | Local data + cached routes  |
        +--------------+--------------+
                       |
                    Local Wi-Fi
                       / LAN
                       |
              +--------+--------+
              |                 |
              v                 v
         +---------+       +---------+
         | Phone   |       | Laptop  |
         | PWA     |       | PWA     |
         +----+----+       +----+----+
              |                 |
              +--------+--------+
                       |
                       v
              Alert + Alternate
              Route for Logistics
              User
```

------------------------------------------------------------------------

# 3. Cloud / Central Side

The central side requires Internet connectivity.

## Data Sources

The platform can receive information from multiple sources:

### Satellite Data

Used as an additional source of information for detecting environmental
or infrastructure-related changes.

### Weather Data

Provides information such as rainfall and other weather conditions that
can contribute to road disruption risk.

### Map / GIS Data

Provides the underlying road network and geographic information required
for road-segment identification and routing.

### GPS / Vehicle Data

Provides vehicle location and movement information.

### Field Reports

Field users can provide geo-tagged reports about incidents such as road
blockage, damage, flooding, or other accessibility problems.

------------------------------------------------------------------------

# 4. Data Ingestion and Processing

All incoming data first goes through an ingestion and processing layer.

``` text
Data Sources
     |
     v
Ingestion
     |
     v
Validation
     |
     v
Normalization
     |
     v
Processed Data
```

The purpose of this layer is to bring information from different sources
into a form that the rest of the platform can use.

------------------------------------------------------------------------

# 5. Disruption Detection

The processed data is used to identify possible disruptions.

Examples include:

-   Flooding
-   Landslides
-   Heavy rainfall related risk
-   Road blockage
-   Road damage
-   Other accessibility disruptions

The output should identify:

``` text
Disruption
    |
    +-- Location
    +-- Type
    +-- Severity / Risk
    +-- Confidence
    +-- Timestamp
```

The system can use a combination of rules, available data, and ML models
depending on the available training data.

------------------------------------------------------------------------

# 6. GIS: Match Disruption to Road Segment

Detecting a disruption is not enough.

The system needs to answer:

> **Which road segment is affected?**

For example:

``` text
Detected incident
      |
      v
GPS coordinates
      |
      v
GIS processing
      |
      v
Nearest / affected road segment
      |
      v
Road ID = R102
```

The affected road segment can then receive an updated status.

Example:

``` text
Road ID: R102
Status: BLOCKED
Reason: Landslide
Risk: HIGH
Updated: 14:32
```

------------------------------------------------------------------------

# 7. Road Graph

The road network is represented as a graph.

``` text
A -------- B
|          |
|          |
C -------- D
      |
      E
```

Each road segment is an edge in the graph.

The edge can contain information such as:

``` text
Road Segment
    |
    +-- Distance
    +-- Travel time
    +-- Accessibility status
    +-- Risk score
    +-- Disruption type
    +-- Last updated time
```

When a road becomes blocked or risky, its graph information is updated.

For example:

``` text
Before:

A ---- B ---- C ---- D
       OPEN

After disruption:

A ---- B    X    C ---- D
            BLOCKED
```

The route engine then works with the updated graph.

------------------------------------------------------------------------

# 8. Route Engine

The route engine calculates suitable routes using the current road
state.

The goal is not simply:

> **Shortest route**

The goal is:

> **A route that is suitable considering road accessibility, risk and
> travel time.**

Example:

``` text
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

The system can therefore select an alternate route when the original
route becomes unsafe or inaccessible.

------------------------------------------------------------------------

# 9. Central Server

The central server maintains the latest global state of the system.

It stores:

-   Road status
-   Road risk
-   Disruptions
-   Routes
-   Alerts
-   Relevant field reports
-   Version information

## Versioned Road State

The road network should be versioned so that field systems can determine
what information they have and what needs to be synchronized.

Example:

``` text
Central Road Graph Version: 1842
Field Server Version:       1837
```

When connectivity becomes available:

``` text
Field 1837
    |
    v
Sync
    |
    v
Central 1842
    |
    v
Receive required updates
    |
    v
Field becomes 1842
```

This allows the field system to stay synchronized without requiring
continuous Internet connectivity.

------------------------------------------------------------------------

# 10. Field Side

The field side is designed for environments with little or no Internet
connectivity.

A local server can be installed at locations such as:

-   Depot
-   Checkpoint
-   Relief camp
-   Other operational field locations

``` text
Central Server
      |
   Internet
      |
      v
Local Field Server
      |
   Local Wi-Fi
      |
      v
Phones / Laptops
```

The local server acts as an **edge node** for nearby users.

------------------------------------------------------------------------

# 11. PWA --- Offline User Interface

Users access the system through a Progressive Web App (PWA).

The PWA can cache relevant information so that the application remains
useful when Internet connectivity is unavailable.

Potential cached information includes:

-   Relevant map data
-   Road status
-   Recent alerts
-   Previously synchronized routes
-   Local operational data

The user experience should remain available through the local Wi-Fi/LAN
even if the Internet connection is unavailable.

------------------------------------------------------------------------

# 12. Synchronization

Synchronization is one of the most important parts of the architecture.

The system should synchronize whenever a network link becomes available.

``` text
               CENTRAL
                  |
             Internet
                  |
                  v
             FIELD NODE
                  |
              Local LAN
                  |
                  v
                PWA
```

When Internet is unavailable:

``` text
Central Server       X       Field Server
                             |
                             v
                       Local PWA works
```

When Internet returns:

``` text
Field Server
     |
     v
Sync Manager
     |
     v
Central Server
     |
     v
Updated global state
```

The synchronization mechanism should use version information to
determine which updates are missing.

------------------------------------------------------------------------

# 13. Complete End-to-End Flow

A typical disruption flow looks like this:

``` text
1. Weather / Satellite / Field data arrives
                    |
                    v
2. Data ingestion and processing
                    |
                    v
3. Disruption detected
                    |
                    v
4. GIS identifies affected road segment
                    |
                    v
5. Road graph is updated
                    |
                    v
6. Route engine recalculates routes
                    |
                    v
7. Central server stores new road state
   and route information
                    |
                    v
8. Update synchronizes to field server
   when connectivity exists
                    |
                    v
9. Local PWA receives alert
                    |
                    v
10. Logistics user sees:
       - disruption
       - affected road
       - alternate route
       - route information
```

------------------------------------------------------------------------

# 14. Offline Scenario

This is the important field scenario.

Suppose the Internet connection is lost.

``` text
Internet = OFF
```

The local field server still has:

``` text
Cached road data
+
Cached routes
+
Recent road status
+
Recent alerts
```

Therefore:

``` text
Driver / Logistics User
          |
          v
      Local Wi-Fi
          |
          v
     Field Server
          |
          v
         PWA
```

The user can still access the information available locally.

When connectivity returns, synchronization occurs.

------------------------------------------------------------------------

# 15. Example SIH Demonstration Scenario

We can demonstrate the platform using a simulated logistics mission.

### Initial state

``` text
Warehouse
    |
    v
Road R101
    |
    v
Road R102
    |
    v
Relief Camp
```

The system initially recommends:

``` text
Route: R101 → R102
Risk: Low
ETA: 4h 10m
```

### Disruption

A landslide is detected/reported near R102.

``` text
Field Report
     +
Location
     |
     v
R102 identified
     |
     v
R102 = BLOCKED
```

### Recalculation

The route engine updates the route:

``` text
Original Route
R101 → R102
       X
     BLOCKED

New Route
R101 → R103 → R104 → Relief Camp
```

The logistics user receives:

``` text
ALERT

Road R102 is blocked.

Reason:
Landslide

Recommended alternate route:
R101 → R103 → R104

ETA:
4h 45m
```

### Internet failure

Now disconnect the Internet.

The field user can still access the locally synchronized information
through:

``` text
Phone
  ↓
Local Wi-Fi
  ↓
Field Server
  ↓
PWA
```

### Reconnection

Reconnect Internet.

``` text
Field Server
     ↓
Automatic synchronization
     ↓
Central Server
```

This demonstrates the core value of our architecture.

------------------------------------------------------------------------

# 16. Main Modules We Need to Build

The project can be divided into these modules:

``` text
1. Data Ingestion
2. Disruption Detection
3. GIS / Road Segment Matching
4. Road Graph Management
5. Route Engine
6. Central Backend
7. Versioning + Synchronization
8. Field Edge Server
9. Offline PWA
10. Alerts / Notifications
11. Dashboard
12. Testing + Demo Simulation
```

Each module can be developed independently and then integrated.

------------------------------------------------------------------------

# 17. High-Level Technology Direction

The original SIH proposal identifies the following technology direction:

  Layer            Technology
  ---------------- ---------------------------------------
  Frontend         React.js, Bootstrap, Leaflet / Mapbox
  Backend          Python, FastAPI, REST APIs
  AI/ML            Python, Scikit-learn / PyTorch
  Database         PostgreSQL + PostGIS
  Real-time        Redis / WebSockets
  Integration      GPS, Weather APIs, GIS data
  Infrastructure   Cloud + Secure APIs

For the updated edge architecture, we additionally need a local
field-server setup and offline data storage/synchronization.

------------------------------------------------------------------------

# 18. MVP Goal

We should not try to implement the entire real-world NER logistics
ecosystem immediately.

Our first working prototype should prove this complete loop:

``` text
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
Offline PWA
    ↓
Logistics User
```

If this loop works reliably, we have demonstrated the core of the
proposed system.

------------------------------------------------------------------------

# 19. What Success Looks Like

A successful prototype should allow a judge to see:

### Before disruption

``` text
Recommended Route
Risk: Low
ETA: X
```

### After disruption

``` text
⚠ Road blocked / high risk

Affected segment: R102

Alternate route generated.
Risk: Lower
ETA: X + additional time
```

### During Internet failure

``` text
Internet: OFF

Local PWA: WORKING
Road information: AVAILABLE
Route information: AVAILABLE
Alerts: AVAILABLE
```

### After reconnection

``` text
Internet: ON

Synchronization: COMPLETED
Field state: UPDATED
Central state: UPDATED
```

------------------------------------------------------------------------

## Project Principle

> **We are building a resilient logistics decision-support system ---
> not just a map or navigation application.**

The system continuously builds an understanding of road accessibility,
detects disruptions, updates the road network, computes suitable
alternate routes, and distributes the latest usable information to
logistics users even in low-connectivity environments.

------------------------------------------------------------------------

## Current Architecture

**Cloud / Central**

`Data Sources → Ingestion → Disruption Detection → GIS Matching → Road Graph → Route Engine → Versioned Central Server`

**Field**

`Central Server ↔ Sync ↔ Local Field Server → Local Wi-Fi/LAN → Offline PWA → Logistics User`

------------------------------------------------------------------------

## Team Development Rule

Before implementing a module, define:

1.  What data enters it?
2.  What processing happens?
3.  What output does it produce?
4.  Which other module consumes that output?
5.  What happens if Internet is unavailable?
6.  How is the state synchronized later?

This keeps the implementation aligned with the overall architecture.
