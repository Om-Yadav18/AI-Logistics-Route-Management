# Module 1: Project Foundation

## 1. Purpose
This module creates the foundation of the NER Logistics Intelligence system. 

Before building complex features like satellite data ingestion, weather analysis, and dynamic routing, we need a reliable baseline: a backend API server and a frontend user interface that can start cleanly, communicate with each other over HTTP, and allow new feature modules to be plugged in independently.

---

## 2. Technology Used

### Backend
* **FastAPI**: A modern, high-speed web framework for Python. 
  * *Why we use it*: It is lightweight, fast, has native support for asynchronous programming (`async`/`await`), and automatically validates data. This is crucial for handling upcoming concurrent tasks like fetching satellite imagery and computing route graphs.
* **Uvicorn**: An ASGI (Asynchronous Server Gateway Interface) web server.
  * *Why we use it*: FastAPI is the application framework, but Uvicorn is the actual server engine that listens for incoming HTTP network connections and passes them to FastAPI.
* **CORS Middleware (`fastapi.middleware.cors`)**: A security configuration layer.
  * *Why we use it*: During development, our React frontend runs on `http://localhost:5173` while our backend runs on `http://127.0.0.1:8000`. Browsers block cross-origin requests by default for security; CORS middleware tells the browser to allow the frontend to talk to the backend.
* **Python-dotenv**: A configuration helper library.
  * *Why we use it*: It reads variables from a `.env` file (like port numbers or future API keys) and loads them into the environment so we never hard-code configuration values into source code.

### Frontend
* **React**: A popular JavaScript library for building component-based user interfaces.
  * *Why we use it*: It allows us to manage UI states (e.g., whether the backend is connected, disconnected, or loading) smoothly using components and hooks.
* **Vite**: A modern build tool and local development server for frontend web applications.
  * *Why we use it*: It replaces older, slower bundlers (like Webpack) and provides near-instant startup and fast Hot Module Replacement (HMR).

---

## 3. Input

For the health check, the input is:
* An **HTTP `GET` request** sent from the client (browser/React) to the endpoint URL: `http://127.0.0.1:8000/api/health`.
* The request contains standard HTTP headers (e.g., `Accept: application/json`). No query parameters or request body are required for this check.

---

## 4. Processing / Logic

The end-to-end request processing flows as follows:

```text
React Frontend (Component Mounts)
        ↓
Initiates fetch('http://127.0.0.1:8000/api/health')
        ↓
HTTP GET Request over local network
        ↓
Uvicorn ASGI Server receives network packet
        ↓
FastAPI Application routes to /api/health
        ↓
CORS Middleware validates origin headers
        ↓
health_check() function executes in main.py
        ↓
Constructs Python dictionary with service metadata
        ↓
FastAPI serializes dictionary to JSON
        ↓
HTTP 200 OK response sent over network
        ↓
React receives response, parses JSON, and updates state
        ↓
UI renders "Backend: Connected"
```

---

## 5. Output

The backend produces a standardized JSON response with an HTTP `200 OK` status code:

```json
{
  "status": "healthy",
  "service": "NER Logistics Intelligence",
  "environment": "development",
  "version": "1.0.0"
}
```

* `status`: Indicates the health state (`healthy`).
* `service`: Name of the backend system.
* `environment`: Operating mode (`development` or `production`).
* `version`: API release version.

---

## 6. Important Files

* `backend/app/main.py`: The entry point of the backend application. Initializes the FastAPI app, configures CORS middleware, and defines the root `/` and `/api/health` endpoints.
* `backend/app/api/__init__.py`: Package marker for future API route modules (such as satellite endpoints, weather endpoints, and routing endpoints).
* `backend/app/services/__init__.py`: Package marker for future business logic services (such as Copernicus API client and risk scoring algorithms).
* `frontend/index.html`: The single-page application HTML entry point containing the `<div id="root"></div>` mount node.
* `frontend/src/main.jsx`: Mounts the React application tree into the DOM root.
* `frontend/src/app.jsx`: The main React component that performs the fetch call to `/api/health`, handles loading/error/success states, and renders the connection status.
* `frontend/vite.config.js`: Configuration file for Vite defining the React plugin and local dev server parameters (`host: 127.0.0.1`, `port: 5173`).
* `.gitignore`: Prevents virtual environments (`venv/`), dependencies (`node_modules/`), and sensitive files (`.env`) from being committed to Git.

---

## 7. Important Functions / Classes

### `read_root()` (`backend/app/main.py`)
* **Purpose**: Verifies that the API server is alive and responding at the root URL `/`.
* **Input**: None (`GET /`).
* **Output**: Dictionary `{"service": "...", "status": "online", "version": "1.0.0"}`.
* **Why it matters**: Provides a quick sanity check for basic server connectivity.

### `health_check()` (`backend/app/main.py`)
* **Purpose**: Returns the operational health status and environment metadata of the backend.
* **Input**: None (`GET /api/health`).
* **Output**: JSON dictionary containing `status`, `service`, `environment`, and `version`.
* **Why it matters**: Serves as the standard health check contract for the frontend and monitoring tools to confirm the backend is ready before sending feature requests.

### `checkBackendHealth()` (`frontend/src/app.jsx`)
* **Purpose**: Asynchronously calls the backend health endpoint from React.
* **Input**: None (triggered on component mount or manual retry button).
* **Output**: Updates React state variables (`health`, `loading`, `error`).
* **Why it matters**: Manages the asynchronous network lifecycle and translates the HTTP response into visual UI feedback.

---

## 8. Data Flow

```text
┌────────────────────────────────────────┐
│          React Frontend                │
│         (http://localhost:5173)        │
│                                        │
│  State: [loading: true]                │
│  useEffect() triggers fetch()          │
└──────────────────┬─────────────────────┘
                   │
                   │ HTTP GET /api/health
                   ▼
┌────────────────────────────────────────┐
│          Uvicorn ASGI Server           │
│         (http://127.0.0.1:8000)        │
│                                        │
│  FastAPI Router -> health_check()      │
│  Returns JSON Payload                  │
└──────────────────┬─────────────────────┘
                   │
                   │ HTTP 200 OK + JSON
                   ▼
┌────────────────────────────────────────┐
│          React Frontend                │
│                                        │
│  State: [health: data, loading: false] │
│  UI shows: "Backend: Connected"        │
└────────────────────────────────────────┘
```

---

## 9. Limitations and Assumptions

* **Stateless Health Check**: The health endpoint currently confirms that the FastAPI process and Uvicorn server are alive. It does not yet verify connectivity to external services (like Copernicus satellite APIs or weather feeds), which will be added in subsequent modules.
* **No Authentication Yet**: Endpoints are currently open without API keys or JWT tokens, suitable for initial local prototyping.
* **Local Development CORS**: CORS is configured with `allow_origins=["*"]` for development simplicity. In production, this will be locked down to the exact domain origin.
* **No Offline Cache Yet**: The frontend currently requires active local connectivity to reach the backend; offline caching and Bluetooth P2P sync will be implemented in future modules.

---

## 10. How I Should Explain This to a Judge

### When asked: *"What is your technology architecture?"*
> "Our architecture is built as a modular, decoupled system. The backend uses Python with **FastAPI** running on **Uvicorn**, selected because its native asynchronous support allows us to concurrently query satellite imagery, weather feeds, and compute road graphs without blocking the server. The user-facing dashboard is built with **React and Vite**, providing a fast and reactive interface. The frontend and backend communicate via clean, standard REST APIs, allowing every layer of our pipeline—from satellite ingestion to offline synchronization—to be built and tested independently."

### When asked: *"How does your frontend communicate with your backend?"*
> "The React frontend communicates with the FastAPI backend over HTTP using asynchronous REST requests. When the client loads, it initiates a `GET` request to our `/api/health` endpoint. FastAPI processes the request through CORS middleware to ensure secure cross-origin communication, executes the health handler, and returns a JSON payload. The React frontend consumes this response, updates its internal state, and displays the real-time operational status of the service."

---

## 11. Realistic Judge Questions & Answers

**Q1: Why didn't you use Django or Flask instead of FastAPI?**
> *Answer*: Flask and Django are primarily synchronous by default. Our logistics pipeline will frequently perform long-running I/O operations—such as downloading Sentinel-1 SAR metadata and polling weather data—while simultaneously serving routing requests. FastAPI's native `async`/`await` architecture and ASGI support prevent these remote calls from blocking the entire application.

**Q2: What is the difference between FastAPI and Uvicorn?**
> *Answer*: FastAPI is the application framework where we define routes, data models, and business logic. Uvicorn is the ASGI web server that actually runs the application, listens on network sockets, and handles incoming HTTP traffic concurrently.

**Q3: What is CORS and why did you have to configure it?**
> *Answer*: CORS stands for Cross-Origin Resource Sharing. Web browsers enforce a security rule that prevents a web page hosted on one port (`5173`) from making requests to a different port (`8000`) unless the destination server explicitly permits it. We configured FastAPI's `CORSMiddleware` to authorize requests from our frontend.

**Q4: How does this foundation support the future offline/P2P capabilities of the project?**
> *Answer*: By establishing a clean, structured REST contract where endpoints return standardized JSON payloads with clear versioning and timestamps, we can later serialize these exact payloads into client-side offline storage (IndexedDB/Cache) and exchange them peer-to-peer via Bluetooth when internet access is lost.
