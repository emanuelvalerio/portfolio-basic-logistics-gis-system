'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { message } from 'antd';

// Reads the port from .env (client-side vars MUST start with NEXT_PUBLIC_).
const API_PORT =
    process.env.NEXT_PUBLIC_FASTAPI_DATA_PROCESSING_DOCKER ||
    process.env.FASTAPI_DATA_PROCESSING_PORT_DOCKER ||
    '5556';
const API_BASE_URL = `http://localhost:${API_PORT}`;

type GeoData = {
    type: string;
    features: Array<{
        type: string;
        properties: { name?: string;[key: string]: any };
        geometry: { type: string; coordinates: any };
    }>;
};

// Dynamic import pointing to the same folder (./Map). Kept exactly as before.
const DynamicMap = dynamic(() => import('./Map'), {
    ssr: false,
    loading: () => <div className="loader">Carregando motor geográfico…</div>,
});

export default function Home() {
    const [apiStatus, setApiStatus] = useState<'Checking...' | 'Online' | 'Offline'>('Checking...');
    const [geoData, setGeoData] = useState<GeoData | null>(null);
    const [neighborhoodData, setNeighborhoodData] = useState<GeoData | null>(null);
    const [streetsData, setStreetsData] = useState<GeoData | null>(null);

    // Layer visibility — toggles just pass the data through or null to hide it.
    const [show, setShow] = useState({ agencias: true, bairros: true, ruas: true });

    const fetchMapData = () => {
        fetch(`${API_BASE_URL}/api/v1/collect/get-postal-agencies-from-db`)
            .then((res) => { if (!res.ok) throw new Error('fail'); return res.json(); })
            .then((data) => { if (data?.features?.length) setGeoData(data); })
            .catch((err) => console.error('Agencies: keeping fallback.', err));

        fetch(`${API_BASE_URL}/api/v1/collect/get-neighborhoods-from-db`)
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => { if (data?.features?.length) setNeighborhoodData(data); })
            .catch((err) => console.error('Neighborhoods:', err));

        fetch(`${API_BASE_URL}/api/v1/collect/get-alagoas-streets-from-db`)
            .then((res) => { if (!res.ok) throw new Error('fail'); return res.json(); })
            .then((data) => { if (data?.features?.length) setStreetsData(data); })
            .catch((err) => console.error('Streets:', err));
    };

    useEffect(() => {
        fetch(`${API_BASE_URL}/health`)
            .then((res) => { if (!res.ok) throw new Error('net'); return res.json(); })
            .then((data) => {
                setApiStatus(data.status === 'online' ? 'Online' : 'Offline');
                message.success('Conectado à FastAPI');
                fetchMapData();
            })
            .catch(() => {
                setApiStatus('Offline');
                message.warning('FastAPI offline. Exibindo dados de fallback no mapa.');
            });

        // Default fallback point so the map is never empty.
        setGeoData({
            type: 'FeatureCollection',
            features: [
                {
                    type: 'Feature',
                    properties: { name: 'Correios - Superintendência Estadual de Alagoas (SEDE)' },
                    geometry: { type: 'Point', coordinates: [-35.7345, -9.6455] },
                },
            ],
        });
    }, []);

    const handleIngest = () => {
        message.loading({ content: 'Ingerindo e carregando dados…', key: 'ingest' });
        Promise.all([
            fetch(`${API_BASE_URL}/api/v1/collect/ingest-postal-agencies-file`, { method: 'POST' }),
            fetch(`${API_BASE_URL}/api/v1/collect/ingest-neighborhoods-file`, { method: 'POST' }),
            fetch(`${API_BASE_URL}/api/v1/collect/ingest-alagoas-streets-file`, { method: 'POST' }),
        ])
            .then(() => {
                message.success({ content: 'Ingestão disparada, carregando mapa…', key: 'ingest', duration: 3 });
                fetchMapData();
            })
            .catch(() => {
                message.error({ content: 'Falha na ingestão. Veja os logs da API.', key: 'ingest', duration: 3 });
                fetchMapData();
            });
    };

    const toggleFullscreen = () =>
        document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();

    const statusColor =
        apiStatus === 'Online' ? '#3FB950' : apiStatus === 'Offline' ? '#F85149' : '#D29922';

    return (
        <main className="console">
            {/* Fullscreen map (requires the Map component to fill 100% — see note) */}
            <div className="map-slot">
                <DynamicMap
                    geoData={show.agencias ? geoData : null}
                    neighborhoodData={show.bairros ? neighborhoodData : null}
                    streetsData={show.ruas ? streetsData : null}
                />
            </div>

            {/* Brand (top-left) */}
            <div className="overlay glass brand">
                <div className="mark">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#FF6A2B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2C12 2 5 8 5 14a7 7 0 0 0 14 0c0-2-1-3.5-2-5-1.5 2-3 2-3 0 0-2 1-4-2-7Z" />
                    </svg>
                </div>
                <div>
                    <div className="title">MIRA · GIS</div>
                    <div className="sub">Protótipo logístico</div>
                </div>
            </div>

            {/* Control panel (top-right) */}
            <div className="overlay glass panel">
                <div className="eyebrow">Backend</div>
                <div className="status-row">
                    <span>API · porta {API_PORT}</span>
                    <span className="status"><span className="dot" style={{ background: statusColor }} />{apiStatus}</span>
                </div>

                <button className="primary" onClick={handleIngest}>Carregar dados</button>

                <div className="eyebrow" style={{ marginTop: 14 }}>Camadas</div>
                <div className="layers">
                    <Toggle label="Agências" color="#FF6A2B" checked={show.agencias}
                        onChange={(v) => setShow((s) => ({ ...s, agencias: v }))} />
                    <Toggle label="Bairros" color="#45C0C2" square checked={show.bairros}
                        onChange={(v) => setShow((s) => ({ ...s, bairros: v }))} />
                    <Toggle label="Ruas (Alagoas)" color="#9AA3AB" checked={show.ruas}
                        onChange={(v) => setShow((s) => ({ ...s, ruas: v }))} />
                </div>
            </div>

            {/* Fullscreen button (bottom-right) */}
            <button className="overlay glass fab" onClick={toggleFullscreen} aria-label="Tela cheia">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 8V3h5M21 8V3h-5M3 16v5h5M21 16v5h-5" />
                </svg>
            </button>

            <style jsx global>{`
        html, body { margin: 0; height: 100%; background: #0b0d10; }
        .leaflet-container { background: #0b0d10 !important; height: 100%; width: 100%; }
        .leaflet-control-attribution {
          background: rgba(15,18,22,0.6) !important; color: #9AA3AB !important;
          backdrop-filter: blur(12px); border-radius: 8px;
        }
        .leaflet-control-attribution a { color: #9AA3AB !important; }
      `}</style>

            <style jsx>{`
        .console { position: fixed; inset: 0; overflow: hidden; background: #0b0d10;
                   font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
        .map-slot { position: absolute; inset: 0; z-index: 0; }
        .loader { position: fixed; inset: 0; display: grid; place-items: center;
                  color: #9AA3AB; font-size: 14px; background: #0b0d10; }

        .overlay { position: absolute; z-index: 500; }
        .glass { background: rgba(15,18,22,0.72); -webkit-backdrop-filter: blur(16px) saturate(1.2);
                 backdrop-filter: blur(16px) saturate(1.2); border: 1px solid rgba(255,255,255,0.10);
                 border-radius: 14px; box-shadow: 0 8px 30px rgba(0,0,0,0.45); color: #F3F1EC; }
        .eyebrow { font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase;
                   color: #9AA3AB; font-weight: 600; }

        .brand { top: 16px; left: 16px; display: flex; align-items: center; gap: 12px; padding: 10px 14px; }
        .brand .mark { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center;
                       background: rgba(255,106,43,0.15); border: 1px solid rgba(255,106,43,0.35); }
        .brand .mark svg { width: 17px; height: 17px; }
        .brand .title { font-size: 14px; font-weight: 650; letter-spacing: -0.01em; }
        .brand .sub { font-size: 11px; color: #9AA3AB; }

        .panel { top: 16px; right: 16px; width: 248px; padding: 14px; }
        .status-row { display: flex; align-items: center; justify-content: space-between; font-size: 13px; margin-top: 4px; }
        .status { display: inline-flex; align-items: center; gap: 6px; }
        .dot { width: 8px; height: 8px; border-radius: 50%; }
        .primary { margin-top: 12px; width: 100%; border: 0; cursor: pointer; border-radius: 9px;
                   background: #FF6A2B; color: #1a0d06; font-size: 13px; font-weight: 700; padding: 9px 0;
                   transition: filter .15s; }
        .primary:hover { filter: brightness(1.08); }
        .primary:focus-visible { outline: 2px solid #45C0C2; outline-offset: 2px; }

        .layers { margin-top: 2px; }
        .fab { bottom: 20px; right: 16px; width: 44px; height: 44px; display: grid; place-items: center;
               cursor: pointer; color: #F3F1EC; }
        .fab svg { width: 19px; height: 19px; }
        .fab:hover { border-color: rgba(255,106,43,0.5); color: #fff; }
        .fab:focus-visible { outline: 2px solid #45C0C2; outline-offset: 2px; }

        @media (max-width: 560px) { .panel { width: calc(100vw - 32px); } }
      `}</style>
        </main>
    );
}

function Toggle({ label, color, square, checked, onChange }: {
    label: string; color: string; square?: boolean; checked: boolean; onChange: (v: boolean) => void;
}) {
    return (
        <label className="row">
            <span className="name">
                <span className="swatch" style={{ background: color, borderRadius: square ? 3 : 999 }} />
                {label}
            </span>
            <span className="switch">
                <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
                <span className="track" />
            </span>
            <style jsx>{`
        .row { display: flex; align-items: center; justify-content: space-between; padding: 9px 0;
               border-top: 1px solid rgba(255,255,255,0.10); cursor: pointer; }
        .row:first-child { border-top: 0; }
        .name { display: flex; align-items: center; gap: 9px; font-size: 13px; color: #F3F1EC; }
        .swatch { width: 11px; height: 11px; }
        .switch { position: relative; width: 34px; height: 20px; flex: none; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .track { position: absolute; inset: 0; border-radius: 20px; background: rgba(255,255,255,0.14); transition: .18s; }
        .track::before { content: ""; position: absolute; height: 14px; width: 14px; left: 3px; top: 3px;
                         border-radius: 50%; background: #fff; transition: .18s; }
        .switch input:checked + .track { background: #FF6A2B; }
        .switch input:checked + .track::before { transform: translateX(14px); }
        .switch input:focus-visible + .track { outline: 2px solid #45C0C2; outline-offset: 2px; }
      `}</style>
        </label>
    );
}
