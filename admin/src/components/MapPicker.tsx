import { useEffect, useMemo, useState } from 'react';
import { Button, Input, Space } from 'antd';
import { MapContainer, Marker, Circle, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const DEFAULT_CENTER: [number, number] = [55.751244, 37.618423];

const markerIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

type MapPickerProps = {
  latitude?: number | null;
  longitude?: number | null;
  radiusMeters?: number | null;
  onChange: (coords: { latitude: number; longitude: number; address?: string }) => void;
};

function ClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(event) {
      onPick(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

function Recenter({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], Math.max(map.getZoom(), 15));
  }, [lat, lng, map]);
  return null;
}

export default function MapPicker({ latitude, longitude, radiusMeters, onChange }: MapPickerProps) {
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const hasPoint = typeof latitude === 'number' && typeof longitude === 'number';
  const center = useMemo<[number, number]>(
    () => (hasPoint ? [latitude!, longitude!] : DEFAULT_CENTER),
    [hasPoint, latitude, longitude],
  );

  const searchAddress = async () => {
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    setSearchError(null);
    try {
      const url = new URL('https://nominatim.openstreetmap.org/search');
      url.searchParams.set('format', 'json');
      url.searchParams.set('limit', '1');
      url.searchParams.set('q', q);
      const response = await fetch(url.toString(), {
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) throw new Error('Поиск недоступен');
      const results = (await response.json()) as Array<{
        lat: string;
        lon: string;
        display_name: string;
      }>;
      if (!results.length) {
        setSearchError('Ничего не найдено');
        return;
      }
      const first = results[0];
      onChange({
        latitude: Number(first.lat),
        longitude: Number(first.lon),
        address: first.display_name,
      });
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : 'Ошибка поиска');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="map-picker">
      <Space.Compact style={{ width: '100%', marginBottom: 8 }}>
        <Input
          placeholder="Поиск адреса (например: Москва, Тверская 1)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onPressEnter={() => void searchAddress()}
        />
        <Button type="primary" loading={searching} onClick={() => void searchAddress()}>
          Найти
        </Button>
      </Space.Compact>
      {searchError ? <div className="map-picker-hint error">{searchError}</div> : null}
      <div className="map-picker-hint">Кликните по карте, чтобы поставить точку</div>
      <div className="map-picker-canvas">
        <MapContainer center={center} zoom={hasPoint ? 15 : 11} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClickHandler
            onPick={(lat, lng) => onChange({ latitude: lat, longitude: lng })}
          />
          {hasPoint ? (
            <>
              <Recenter lat={latitude!} lng={longitude!} />
              <Marker position={[latitude!, longitude!]} icon={markerIcon} />
              <Circle
                center={[latitude!, longitude!]}
                radius={radiusMeters || 500}
                pathOptions={{ color: '#1f6f5b', fillColor: '#1f6f5b', fillOpacity: 0.15 }}
              />
            </>
          ) : null}
        </MapContainer>
      </div>
    </div>
  );
}
