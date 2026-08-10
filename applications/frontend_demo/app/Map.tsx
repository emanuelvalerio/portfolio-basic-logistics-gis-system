'use client';

import { useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

type BaseMap = 'dark' | 'osm';

export default function Map({
  baseMap = 'dark',
  geoData,
  neighborhoodData,
  streetsData,
  fireData,
}: {
  baseMap?: BaseMap;
  geoData: any;
  neighborhoodData?: any;
  streetsData?: any;
  fireData?: any;
}) {
  useEffect(() => {
    // Ensures Leaflet only swaps the icons once the browser is fully loaded,
    // avoiding crashes during startup.
    if (typeof window !== 'undefined') {
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
      });
    }
  }, []);

  const onEachPostalAgency = (feature: any, layer: L.Layer) => {
    if (feature.properties) {
      const { Nome, Name, Endereço, Address, Cidade, City, CEP, state, Telefone, Phone } = feature.properties;

      const displayName = Name || Nome || 'Unknown Agency';
      const displayAddress = Address || Endereço || 'N/A';
      const displayCity = City || Cidade || 'N/A';
      const displayZip = feature.properties['ZIP Code'] || CEP || 'N/A';
      const displayPhone = Phone || Telefone || 'N/A';
      const displayState = state || 'AL';

      const popupContent = `
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
          <h4 style="margin-top: 0; margin-bottom: 8px; color: #001529;">${displayName}</h4>
          <p style="margin: 4px 0; font-size: 13px;"><strong>Address:</strong> ${displayAddress}</p>
          <p style="margin: 4px 0; font-size: 13px;"><strong>City:</strong> ${displayCity} - ${displayState}</p>
          <p style="margin: 4px 0; font-size: 13px;"><strong>ZIP Code:</strong> ${displayZip}</p>
          <p style="margin: 4px 0; font-size: 13px;"><strong>Phone:</strong> ${displayPhone}</p>
        </div>
      `;
      layer.bindPopup(popupContent);
    }
  };

  const onEachNeighborhood = (feature: any, layer: L.Layer) => {
    if (feature.properties) {
      const name = feature.properties.NM_BAIRRO || 'Unknown';
      const city = feature.properties.NM_MUN || 'Unknown';
      const state = feature.properties.NM_UF || 'Unknown';
      const area = feature.properties.AREA_KM2 || 0;
      layer.bindPopup(`
        <div style="font-family: Arial, sans-serif;">
          <h4 style="margin: 0; color: #1890ff;">${name}</h4>
          <p style="margin: 4px 0 2px 0; font-size: 13px;"><strong>City/State:</strong> ${city} - ${state}</p>
          <p style="margin: 2px 0; font-size: 13px;"><strong>Area:</strong> ${Number(area).toFixed(2)} km²</p>
        </div>
      `);
    }
  };

  const onEachStreet = (feature: any, layer: L.Layer) => {
    if (feature.properties) {
      const ref = feature.properties.ref || 'N/A';
      const postalCod = feature.properties.postal_cod || 'N/A';
      const name = feature.properties.name || 'Unknown Street';
      const city = feature.properties.NM_MUN || 'Unknown';
      const neighborhood = feature.properties.Bairro || 'Unknown';

      layer.bindPopup(`
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
          <h4 style="margin: 0; color: #595959;">${name}</h4>
          <p style="margin: 4px 0 2px 0; font-size: 13px;"><strong>Reference:</strong> ${ref}</p>
          <p style="margin: 2px 0; font-size: 13px;"><strong>Postal Code:</strong> ${postalCod}</p>
          <p style="margin: 2px 0; font-size: 13px;"><strong>City:</strong> ${city}</p>
          <p style="margin: 2px 0; font-size: 13px;"><strong>Neighborhood:</strong> ${neighborhood}</p>
        </div>
      `);
    }
  };

  const onEachFire = (feature: any, layer: L.Layer) => {
    if (feature.properties) {
      const p = feature.properties;
      const area = p.area_km2 != null ? Number(p.area_km2).toFixed(1) : 'N/A';
      const when = p.occurred_at ? new Date(p.occurred_at).toLocaleString('pt-BR') : 'N/A';
      const detections = p.qtd_deteccoes ?? 'N/A';
      layer.bindPopup(`
        <div style="font-family: Arial, sans-serif; min-width: 210px;">
          <h4 style="margin: 0 0 6px; color: #B3320F;">🔥 Evento de incêndio</h4>
          <p style="margin: 3px 0; font-size: 13px;"><strong>Área:</strong> ${area} km²</p>
          <p style="margin: 3px 0; font-size: 13px;"><strong>Última detecção:</strong> ${when}</p>
          <p style="margin: 3px 0; font-size: 13px;"><strong>Nº de detecções:</strong> ${detections}</p>
          <p style="margin: 3px 0; font-size: 12px; color: #888;"><strong>ID:</strong> ${p.external_id || 'N/A'}</p>
        </div>
      `);
    }
  };

  return (
    <MapContainer
      center={[-9.645500, -35.734500]}
      zoom={10}
      zoomControl={false}
      style={{ height: '100%', width: '100%' }}
    >
      {/* Base tile — switchable between dark (CARTO) and light (OpenStreetMap).
          The `key` forces Leaflet to swap the tile layer when the choice changes. */}
      {baseMap === 'osm' ? (
        <TileLayer
          key="osm"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
          maxZoom={19}
        />
      ) : (
        <TileLayer
          key="dark"
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution="&copy; OpenStreetMap &copy; CARTO"
          subdomains="abcd"
          maxZoom={19}
        />
      )}

      {/* Zoom moved to bottom-left so it doesn't collide with the brand pill */}
      <ZoomControl position="bottomleft" />

      {/* Neighborhood polygons */}
      {neighborhoodData && (
        <GeoJSON
          key={`neigh-${JSON.stringify(neighborhoodData).substring(0, 20)}`}
          data={neighborhoodData}
          onEachFeature={onEachNeighborhood}
          style={{ color: '#45C0C2', weight: 2, fillOpacity: 0.12 }}
        />
      )}

      {/* Streets */}
      {streetsData && (
        <GeoJSON
          key={`streets-${JSON.stringify(streetsData).substring(0, 20)}`}
          data={streetsData}
          onEachFeature={onEachStreet}
          style={{ color: '#8c94a0', weight: 1, fillOpacity: 0 }}
        />
      )}

      {/* SIPAM fire events (polygons) — ember/red */}
      {fireData && (
        <GeoJSON
          key={`fire-${JSON.stringify(fireData).substring(0, 20)}`}
          data={fireData}
          onEachFeature={onEachFire}
          style={{ color: '#FF3B2F', weight: 1.5, fillColor: '#FF6A2B', fillOpacity: 0.35 }}
        />
      )}

      {/* Postal agencies (points) */}
      {geoData && (
        <GeoJSON key={JSON.stringify(geoData)} data={geoData} onEachFeature={onEachPostalAgency} />
      )}
    </MapContainer>
  );
}
