'use client';

import { useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, LayersControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export default function Map({ geoData, neighborhoodData, streetsData }: { geoData: any; neighborhoodData?: any; streetsData?: any }) {
  useEffect(() => {
    // This ensures Leaflet only tries to change the icons when the browser is fully loaded,
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
      // Destructure handling both Portuguese (original geojson) and English (from DB query) property names
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

  return (
    <MapContainer
      center={[-9.645500, -35.734500]}
      zoom={10}
      style={{ height: '60vh', width: '100%', borderRadius: '8px', zIndex: 1 }}
    >
      <LayersControl position="topright">
        {/* Base Layer: The actual map background */}
        <LayersControl.BaseLayer checked name="OpenStreetMap">
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        </LayersControl.BaseLayer>

        {/* Overlay: Neighborhood Polygons */}
        {neighborhoodData && (
          <LayersControl.Overlay checked name="Neighborhoods (MultiPolygon)">
            <GeoJSON 
               key={`neigh-${JSON.stringify(neighborhoodData).substring(0,20)}`} 
               data={neighborhoodData} 
               onEachFeature={onEachNeighborhood}
               style={{ color: '#1890ff', weight: 2, fillOpacity: 0.15 }}
            />
          </LayersControl.Overlay>
        )}

        {/* Overlay: Streets dataset from PostGIS */}
        {streetsData && (
          <LayersControl.Overlay checked name="Alagoas Streets (MultiLineString)">
            <GeoJSON
              key={`streets-${JSON.stringify(streetsData).substring(0, 20)}`}
              data={streetsData}
              onEachFeature={onEachStreet}
              style={{ color: '#8c8c8c', weight: 1, fillOpacity: 0 }}
            />
          </LayersControl.Overlay>
        )}
        
        {/* Overlay: The togglable points from PostGIS */}
        {geoData && (
          <LayersControl.Overlay checked name="Postal Agencies (Point)">
            <GeoJSON key={JSON.stringify(geoData)} data={geoData} onEachFeature={onEachPostalAgency} />
          </LayersControl.Overlay>
        )}
      </LayersControl>
    </MapContainer>
  );
}