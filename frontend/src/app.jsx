import React, { useState, useEffect } from 'react';
import { api, API_BASE_URL } from './api';

function App() {
  // System Health State
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState(null);

  // Satellite Inputs State
  const [bbox, setBbox] = useState({
    min_lon: '91.50',
    min_lat: '26.00',
    max_lon: '92.00',
    max_lat: '26.50',
  });

  // Change Detection Inputs State
  const [changeParams, setChangeParams] = useState({
    baseline_file: 'validation_baseline_may2024.tif',
    event_file: 'validation_event_july2024.tif',
    water_threshold_db: '-16.0',
    change_threshold_db: '-4.0',
    min_region_pixels: '5',
  });

  // Weather Inputs State
  const [coords, setCoords] = useState({
    lat: '26.15',
    lon: '91.65',
  });

  // Results & Active Operation State
  const [activeTab, setActiveTab] = useState('system');
  const [activeTitle, setActiveTitle] = useState('System Health');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resultData, setResultData] = useState(null);
  const [showRawJson, setShowRawJson] = useState(false);

  // Initial Health Check
  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await api.checkHealth();
      setHealth(data);
      setResultData(data);
      setActiveTitle('System Health (/api/health)');
    } catch (err) {
      setHealthError(err.message);
      setHealth(null);
      setError(err.message);
    } finally {
      setHealthLoading(false);
    }
  };

  const handleAction = async (title, apiCall) => {
    setLoading(true);
    setError(null);
    setActiveTitle(title);
    try {
      const data = await apiCall();
      setResultData(data);
    } catch (err) {
      setError(err.message);
      setResultData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h1 style={styles.title}>NER Logistics Intelligence</h1>
            <p style={styles.subtitle}>Engineering Prototype — Interactive Testing Shell (Modules 1–4)</p>
          </div>
          <div style={styles.apiBadge}>
            Backend: <code>{API_BASE_URL}</code>
          </div>
        </div>
      </header>

      {/* Main Grid: Left Controls, Right Results */}
      <div style={styles.grid}>
        {/* Left Column: Modules Controls */}
        <div style={styles.controlsCol}>

          {/* Module 1: System Status */}
          <section style={styles.card}>
            <div style={styles.cardHeader}>
              <h2 style={styles.cardTitle}>1. System Status</h2>
              <span style={{
                ...styles.badge,
                backgroundColor: healthLoading ? '#e2e8f0' : health ? '#def7ec' : '#fde8e8',
                color: healthLoading ? '#475569' : health ? '#03543f' : '#9b1c1c'
              }}>
                {healthLoading ? 'Checking...' : health ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <p style={styles.cardDesc}>Verify FastAPI backend health and operational status.</p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                id="btn-check-system"
                onClick={checkHealth}
                disabled={healthLoading}
                style={styles.primaryButton}
              >
                {healthLoading ? 'Checking...' : 'Check System'}
              </button>
            </div>
            {health && (
              <div style={styles.inlineMeta}>
                <span><strong>Service:</strong> {health.service}</span>
                <span><strong>Version:</strong> {health.version}</span>
                <span><strong>Env:</strong> {health.environment}</span>
              </div>
            )}
          </section>

          {/* Module 2 & 3A: Satellite Data */}
          <section style={styles.card}>
            <div style={styles.cardHeader}>
              <h2 style={styles.cardTitle}>2. Satellite Data (Sentinel-1 & 2)</h2>
            </div>
            <p style={styles.cardDesc}>Query CDSE Copernicus catalogue metadata or stream calibrated SAR raster.</p>
            
            <div style={styles.paramGrid}>
              <div>
                <label style={styles.label}>Min Lon</label>
                <input
                  type="text"
                  value={bbox.min_lon}
                  onChange={(e) => setBbox({ ...bbox, min_lon: e.target.value })}
                  style={styles.input}
                />
              </div>
              <div>
                <label style={styles.label}>Min Lat</label>
                <input
                  type="text"
                  value={bbox.min_lat}
                  onChange={(e) => setBbox({ ...bbox, min_lat: e.target.value })}
                  style={styles.input}
                />
              </div>
              <div>
                <label style={styles.label}>Max Lon</label>
                <input
                  type="text"
                  value={bbox.max_lon}
                  onChange={(e) => setBbox({ ...bbox, max_lon: e.target.value })}
                  style={styles.input}
                />
              </div>
              <div>
                <label style={styles.label}>Max Lat</label>
                <input
                  type="text"
                  value={bbox.max_lat}
                  onChange={(e) => setBbox({ ...bbox, max_lat: e.target.value })}
                  style={styles.input}
                />
              </div>
            </div>

            <div style={styles.buttonGroup}>
              <button
                id="btn-sentinel1-latest"
                onClick={() => handleAction('Sentinel-1 Latest Metadata', () => api.getSentinel1Latest(bbox))}
                disabled={loading}
                style={styles.button}
              >
                Get Sentinel-1
              </button>
              <button
                id="btn-sentinel2-latest"
                onClick={() => handleAction('Sentinel-2 Latest Metadata', () => api.getSentinel2Latest(bbox))}
                disabled={loading}
                style={styles.button}
              >
                Get Sentinel-2
              </button>
              <button
                id="btn-satellite-latest"
                onClick={() => handleAction('Latest Satellite Summary', () => api.getSatelliteLatestSummary(bbox))}
                disabled={loading}
                style={styles.button}
              >
                Get Latest Satellite Data
              </button>
              <button
                id="btn-acquire-sentinel1"
                onClick={() => handleAction('Acquire Sentinel-1 SAR Raster', () => api.acquireSentinel1Raster({ ...bbox, width: 256, height: 256 }))}
                disabled={loading}
                style={styles.accentButton}
              >
                Acquire Sentinel-1 Raster
              </button>
            </div>
          </section>

          {/* Module 3B: Environmental Change Detection */}
          <section style={styles.card}>
            <div style={styles.cardHeader}>
              <h2 style={styles.cardTitle}>3. SAR Change Detection</h2>
            </div>
            <p style={styles.cardDesc}>
              Bitemporal SAR differential backscatter analysis for <strong>Environmental / Flood Candidates</strong>.
            </p>

            <div style={styles.paramGrid}>
              <div style={{ gridColumn: 'span 2' }}>
                <label style={styles.label}>Baseline Raster (Pre-disaster)</label>
                <input
                  type="text"
                  value={changeParams.baseline_file}
                  onChange={(e) => setChangeParams({ ...changeParams, baseline_file: e.target.value })}
                  style={styles.input}
                />
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <label style={styles.label}>Event Raster (Monsoon / Crisis)</label>
                <input
                  type="text"
                  value={changeParams.event_file}
                  onChange={(e) => setChangeParams({ ...changeParams, event_file: e.target.value })}
                  style={styles.input}
                />
              </div>
              <div>
                <label style={styles.label}>Water Cutoff (dB)</label>
                <input
                  type="text"
                  value={changeParams.water_threshold_db}
                  onChange={(e) => setChangeParams({ ...changeParams, water_threshold_db: e.target.value })}
                  style={styles.input}
                />
              </div>
              <div>
                <label style={styles.label}>Drop Cutoff (dB)</label>
                <input
                  type="text"
                  value={changeParams.change_threshold_db}
                  onChange={(e) => setChangeParams({ ...changeParams, change_threshold_db: e.target.value })}
                  style={styles.input}
                />
              </div>
            </div>

            <div style={{ marginTop: '12px' }}>
              <button
                id="btn-run-change-detection"
                onClick={() => handleAction('SAR Flood Candidate Detection', () => api.runChangeDetection(changeParams))}
                disabled={loading}
                style={styles.accentButton}
              >
                Run Change Detection
              </button>
            </div>
          </section>

          {/* Module 4: Weather Integration */}
          <section style={styles.card}>
            <div style={styles.cardHeader}>
              <h2 style={styles.cardTitle}>4. Weather Data (Open-Meteo)</h2>
            </div>
            <p style={styles.cardDesc}>Antecedent precipitation accumulation and meteorological corroboration.</p>

            <div style={styles.paramGrid}>
              <div>
                <label style={styles.label}>Latitude</label>
                <input
                  type="text"
                  value={coords.lat}
                  onChange={(e) => setCoords({ ...coords, lat: e.target.value })}
                  style={styles.input}
                />
              </div>
              <div>
                <label style={styles.label}>Longitude</label>
                <input
                  type="text"
                  value={coords.lon}
                  onChange={(e) => setCoords({ ...coords, lon: e.target.value })}
                  style={styles.input}
                />
              </div>
            </div>

            <div style={{ ...styles.buttonGroup, marginTop: '12px' }}>
              <button
                id="btn-get-weather"
                onClick={() => handleAction('Current Weather & Rainfall', () => api.getCurrentWeather(coords.lat, coords.lon))}
                disabled={loading}
                style={styles.button}
              >
                Get Current Weather
              </button>
              <button
                id="btn-check-corroboration"
                onClick={() => handleAction('Satellite Weather Corroboration', () => api.getWeatherCorroboration(coords.lat, coords.lon))}
                disabled={loading}
                style={styles.primaryButton}
              >
                Check Weather Corroboration
              </button>
            </div>
          </section>
        </div>

        {/* Right Column: Results Viewer */}
        <div style={styles.resultsCol}>
          <div style={styles.resultsCard}>
            <div style={styles.resultsHeader}>
              <div>
                <span style={styles.resultsLabel}>OUTPUT CONSOLE</span>
                <h3 style={styles.resultsTitle}>{activeTitle}</h3>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                  onClick={() => setShowRawJson(!showRawJson)}
                  style={styles.toggleButton}
                >
                  {showRawJson ? 'Formatted View' : 'Raw JSON'}
                </button>
              </div>
            </div>

            {/* Loading Indicator */}
            {loading && (
              <div style={styles.loadingBox}>
                <div style={styles.spinner}></div>
                <span>Executing backend request...</span>
              </div>
            )}

            {/* Error Message */}
            {!loading && error && (
              <div style={styles.errorBox}>
                <strong>Request Failed:</strong> {error}
              </div>
            )}

            {/* Formatted or Raw Output */}
            {!loading && !error && resultData && (
              <div style={{ marginTop: '12px' }}>
                {showRawJson ? (
                  <pre style={styles.codeBlock}>{JSON.stringify(resultData, null, 2)}</pre>
                ) : (
                  <FormattedDisplay data={resultData} />
                )}
              </div>
            )}

            {/* Empty State */}
            {!loading && !error && !resultData && (
              <div style={styles.emptyBox}>
                Select an operation from the left panel to execute and inspect backend responses.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Intelligent Formatted Viewer for API Payloads.
 */
function FormattedDisplay({ data }) {
  if (!data || typeof data !== 'object') {
    return <pre style={styles.codeBlock}>{String(data)}</pre>;
  }

  // 1. Change Detection GeoJSON Display
  if (data.type === 'FeatureCollection' && Array.isArray(data.features)) {
    const summary = data.metadata?.summary || {};
    return (
      <div>
        <div style={styles.metricGrid}>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>Hazard Category</div>
            <div style={styles.metricValue}>Environmental / Flood Candidates</div>
          </div>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>Candidate Regions</div>
            <div style={styles.metricValue}>{data.features.length}</div>
          </div>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>Total Candidate Area</div>
            <div style={styles.metricValue}>{summary.total_candidate_area_km2 || 0} km²</div>
          </div>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>Inundated Pixels</div>
            <div style={styles.metricValue}>{summary.candidate_pixels || 0} px</div>
          </div>
        </div>

        <h4 style={{ fontSize: '0.95rem', margin: '16px 0 8px 0', color: '#333' }}>
          Detected Candidate Polygons:
        </h4>

        {data.features.length === 0 ? (
          <div style={styles.noticeBox}>No flood candidate polygons detected for the given thresholds.</div>
        ) : (
          <div style={styles.tableContainer}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>#</th>
                  <th style={styles.th}>Hazard Type</th>
                  <th style={styles.th}>Area (km²)</th>
                  <th style={styles.th}>Pixel Count</th>
                  <th style={styles.th}>Mean Drop (dB)</th>
                  <th style={styles.th}>Vertices</th>
                </tr>
              </thead>
              <tbody>
                {data.features.map((feat, idx) => {
                  const props = feat.properties || {};
                  const coords = feat.geometry?.coordinates?.[0] || [];
                  return (
                    <tr key={idx} style={styles.tr}>
                      <td style={styles.td}>{idx + 1}</td>
                      <td style={styles.td}>
                        <span style={styles.candidateBadge}>{props.hazard_type || 'flood_candidate'}</span>
                      </td>
                      <td style={styles.td}><strong>{props.area_km2}</strong></td>
                      <td style={styles.td}>{props.pixel_count}</td>
                      <td style={styles.td}>{props.mean_drop_db} dB</td>
                      <td style={styles.td}>{coords.length} pts</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  // 2. Weather & Corroboration Display
  if (data.precipitation_summary && data.corroboration) {
    const p = data.precipitation_summary;
    const c = data.corroboration;
    return (
      <div>
        <div style={styles.metricGrid}>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>Current Condition</div>
            <div style={styles.metricValue}>{p.current_weather_description || 'Unknown'}</div>
          </div>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>Corroboration Level</div>
            <div style={{
              ...styles.metricValue,
              color: c.support_level === 'HIGH_SUPPORT' ? '#03543f' : c.support_level === 'MODERATE_SUPPORT' ? '#b45309' : '#1e40af'
            }}>
              {c.support_level}
            </div>
          </div>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>Past 48h Rainfall</div>
            <div style={styles.metricValue}>{p.past_48h_mm} mm</div>
          </div>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>Forecast 24h Trend</div>
            <div style={styles.metricValue}>{c.forecast_trend} ({p.forecast_24h_mm} mm)</div>
          </div>
        </div>

        <div style={styles.explanationBox}>
          <strong>Physical Corroboration Assessment:</strong>
          <p style={{ margin: '4px 0 0 0', color: '#444' }}>{c.explanation}</p>
        </div>

        <div style={styles.inlineMeta}>
          <span><strong>Past 24h Rain:</strong> {p.past_24h_mm} mm</span>
          <span><strong>Past 72h Rain:</strong> {p.past_72h_mm} mm</span>
          <span><strong>Severe Weather:</strong> {p.is_severe_weather ? 'YES (Warning)' : 'No'}</span>
          <span><strong>Elevation:</strong> {data.location?.elevation_m} m</span>
        </div>
      </div>
    );
  }

  // 3. Satellite Observation Display (Single / Combined)
  if (data.satellite || data.product_type || data.statistics || data.summary) {
    return (
      <div>
        {data.summary && (
          <div style={styles.noticeBox}>
            <strong>Summary:</strong> {data.summary}
          </div>
        )}

        <div style={styles.metaList}>
          {data.product_name && <div><strong>Product Name:</strong> <code>{data.product_name}</code></div>}
          {data.observation_date && <div><strong>Acquisition Date:</strong> {data.observation_date}</div>}
          {data.platform && <div><strong>Platform:</strong> {data.platform}</div>}
          {data.cloud_cover_percentage !== undefined && (
            <div><strong>Cloud Cover:</strong> {data.cloud_cover_percentage}%</div>
          )}
          {data.source_mode && <div><strong>Acquisition Mode:</strong> <span style={styles.candidateBadge}>{data.source_mode}</span></div>}
          {data.file_name && <div><strong>Raster File:</strong> <code>{data.file_name}</code></div>}
          {data.dimensions && <div><strong>Dimensions:</strong> {data.dimensions}</div>}
          {data.crs && <div><strong>CRS:</strong> {data.crs}</div>}
          {data.statistics && (
            <div style={{ marginTop: '8px', padding: '8px', background: '#f8fafc', borderRadius: '4px' }}>
              <strong>Pixel Statistics:</strong>
              <div style={styles.inlineMeta}>
                <span>Min: {data.statistics.min?.toFixed(4)}</span>
                <span>Max: {data.statistics.max?.toFixed(4)}</span>
                <span>Mean: {data.statistics.mean?.toFixed(4)}</span>
                <span>Valid: {data.statistics.valid_pixel_count}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // 4. Default Key-Value Fallback
  return <pre style={styles.codeBlock}>{JSON.stringify(data, null, 2)}</pre>;
}

// Clean, Functional Engineering Prototype Styles
const styles = {
  container: {
    fontFamily: 'Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif',
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '24px 16px',
    color: '#1e293b',
    backgroundColor: '#f8fafc',
    minHeight: '100vh',
  },
  header: {
    marginBottom: '20px',
    paddingBottom: '16px',
    borderBottom: '1px solid #e2e8f0',
  },
  title: {
    fontSize: '1.5rem',
    fontWeight: '700',
    margin: '0 0 4px 0',
    color: '#0f172a',
  },
  subtitle: {
    fontSize: '0.9rem',
    color: '#64748b',
    margin: 0,
  },
  apiBadge: {
    fontSize: '0.8rem',
    backgroundColor: '#e2e8f0',
    padding: '4px 10px',
    borderRadius: '4px',
    color: '#334155',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
    gap: '20px',
    alignItems: 'start',
  },
  controlsCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  resultsCol: {
    position: 'sticky',
    top: '20px',
  },
  card: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '16px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  cardTitle: {
    fontSize: '1.05rem',
    fontWeight: '600',
    margin: 0,
    color: '#1e293b',
  },
  cardDesc: {
    fontSize: '0.82rem',
    color: '#64748b',
    marginTop: 0,
    marginBottom: '12px',
    lineHeight: '1.4',
  },
  paramGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
    marginBottom: '12px',
  },
  label: {
    display: 'block',
    fontSize: '0.75rem',
    fontWeight: '600',
    color: '#475569',
    marginBottom: '2px',
  },
  input: {
    width: '100%',
    padding: '6px 8px',
    fontSize: '0.82rem',
    border: '1px solid #cbd5e1',
    borderRadius: '4px',
    boxSizing: 'border-box',
    fontFamily: 'inherit',
    backgroundColor: '#f8fafc',
  },
  buttonGroup: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  button: {
    padding: '7px 12px',
    fontSize: '0.82rem',
    fontWeight: '500',
    backgroundColor: '#f1f5f9',
    color: '#334155',
    border: '1px solid #cbd5e1',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'background-color 0.15s',
  },
  primaryButton: {
    padding: '7px 14px',
    fontSize: '0.82rem',
    fontWeight: '600',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  accentButton: {
    padding: '7px 14px',
    fontSize: '0.82rem',
    fontWeight: '600',
    backgroundColor: '#0f766e',
    color: '#ffffff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  toggleButton: {
    padding: '4px 8px',
    fontSize: '0.75rem',
    backgroundColor: '#e2e8f0',
    color: '#334155',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  badge: {
    fontSize: '0.72rem',
    fontWeight: '600',
    padding: '2px 8px',
    borderRadius: '12px',
  },
  candidateBadge: {
    fontSize: '0.72rem',
    fontWeight: '600',
    padding: '2px 6px',
    borderRadius: '4px',
    backgroundColor: '#fef3c7',
    color: '#92400e',
  },
  inlineMeta: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
    fontSize: '0.8rem',
    color: '#475569',
    marginTop: '10px',
    paddingTop: '8px',
    borderTop: '1px solid #f1f5f9',
  },
  resultsCard: {
    backgroundColor: '#ffffff',
    border: '1px solid #cbd5e1',
    borderRadius: '8px',
    padding: '16px',
    minHeight: '480px',
    boxShadow: '0 2px 6px rgba(0,0,0,0.06)',
  },
  resultsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: '12px',
    borderBottom: '1px solid #e2e8f0',
  },
  resultsLabel: {
    fontSize: '0.68rem',
    fontWeight: '700',
    letterSpacing: '0.05em',
    color: '#64748b',
  },
  resultsTitle: {
    fontSize: '1rem',
    fontWeight: '600',
    margin: '2px 0 0 0',
    color: '#0f172a',
  },
  loadingBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '24px',
    color: '#2563eb',
    fontSize: '0.9rem',
  },
  spinner: {
    width: '16px',
    height: '16px',
    border: '2px solid #e2e8f0',
    borderTop: '2px solid #2563eb',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  errorBox: {
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#991b1b',
    padding: '12px',
    borderRadius: '6px',
    fontSize: '0.85rem',
    marginTop: '12px',
  },
  emptyBox: {
    textAlign: 'center',
    padding: '48px 16px',
    color: '#94a3b8',
    fontSize: '0.88rem',
  },
  codeBlock: {
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    padding: '12px',
    borderRadius: '6px',
    fontSize: '0.78rem',
    overflowX: 'auto',
    maxHeight: '400px',
    margin: 0,
    fontFamily: 'Consolas, Monaco, monospace',
  },
  metricGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
    gap: '10px',
    marginBottom: '14px',
  },
  metricCard: {
    backgroundColor: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    padding: '10px',
  },
  metricLabel: {
    fontSize: '0.72rem',
    color: '#64748b',
    fontWeight: '500',
  },
  metricValue: {
    fontSize: '0.95rem',
    fontWeight: '700',
    color: '#0f172a',
    marginTop: '2px',
  },
  explanationBox: {
    backgroundColor: '#eff6ff',
    border: '1px solid #dbeafe',
    borderRadius: '6px',
    padding: '10px 12px',
    fontSize: '0.82rem',
    color: '#1e40af',
    marginBottom: '12px',
  },
  noticeBox: {
    backgroundColor: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    padding: '8px 12px',
    fontSize: '0.82rem',
    color: '#334155',
    marginBottom: '12px',
  },
  metaList: {
    fontSize: '0.85rem',
    lineHeight: '1.7',
    color: '#334155',
  },
  tableContainer: {
    overflowX: 'auto',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.8rem',
    textAlign: 'left',
  },
  th: {
    backgroundColor: '#f1f5f9',
    padding: '8px 10px',
    fontWeight: '600',
    color: '#475569',
    borderBottom: '1px solid #e2e8f0',
  },
  td: {
    padding: '8px 10px',
    borderBottom: '1px solid #f1f5f9',
  },
  tr: {
    '&:hover': {
      backgroundColor: '#f8fafc',
    },
  },
};

export default App;
