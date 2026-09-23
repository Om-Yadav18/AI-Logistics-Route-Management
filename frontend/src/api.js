/**
 * Centralized API client for NER Logistics Intelligence backend.
 * Uses VITE_API_BASE_URL or defaults to local FastAPI server on http://127.0.0.1:8000.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Standard fetch helper with timeout and JSON error handling.
 */
async function request(endpoint, params = {}) {
  const url = new URL(`${API_BASE_URL}${endpoint}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.append(key, value);
    }
  });

  try {
    const response = await fetch(url.toString(), {
      headers: {
        'Accept': 'application/json',
      },
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const errorMsg = data?.detail || `HTTP error ${response.status}: ${response.statusText}`;
      throw new Error(errorMsg);
    }

    return data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(`Unable to connect to backend at ${API_BASE_URL}. Ensure FastAPI is running.`);
    }
    throw err;
  }
}

export const api = {
  // 1. System Health
  checkHealth: () => request('/api/health'),

  // 2. Satellite Metadata & Acquisition
  getSentinel1Latest: (bbox) => request('/api/satellite/sentinel-1/latest', bbox),
  getSentinel2Latest: (bbox) => request('/api/satellite/sentinel-2/latest', bbox),
  getSatelliteLatestSummary: (bbox) => request('/api/satellite/latest', bbox),
  acquireSentinel1Raster: (params) => request('/api/satellite/sentinel-1/acquire', params),

  // 3. SAR Change Detection / Flood Candidates
  runChangeDetection: (params) => request('/api/satellite/sentinel-1/change-detection', params),

  // 4. Weather & Corroboration
  getCurrentWeather: (lat, lon) => request('/api/weather/current', { lat, lon }),
  getWeatherCorroboration: (lat, lon, timestamp) => request('/api/weather/corroborate', { lat, lon, timestamp }),
};

export { API_BASE_URL };
