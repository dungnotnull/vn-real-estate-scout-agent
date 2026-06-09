import React, { useState, useEffect } from 'react';
import { Map } from 'mapbox-gl';
import axios from 'axios';

interface Property {
  listing_id: string;
  title: string;
  price_vnd: number;
  area_m2: number;
  address: string;
  latitude: number;
  longitude: number;
  total_score: number;
  bedrooms: number;
  property_type: string;
  platform: string;
  url: string;
  images: string[];
  flags: string[];
}

interface SearchPreferences {
  max_price?: number;
  preferred_cities: string[];
  property_types: string[];
  min_area?: number;
  bedrooms_min?: number;
  workplace_latitude?: number;
  workplace_longitude?: number;
  max_commute_minutes?: number;
}

const PropertyMap: React.FC = () => {
  const mapContainer = React.useRef<HTMLDivElement>(null);
  const map = React.useRef<Map | null>(null);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [showSearch, setShowSearch] = useState(true);

  useEffect(() => {
    if (mapContainer.current && !map.current) {
      map.current = new Map({
        container: mapContainer.current,
        style: 'https://api.mapbox.com/mapbox-gl-js/v3.0.1/mapbox-gl.css',
        center: [106.6545, 10.7737], // Ho Chi Minh City
        zoom: 12,
        accessToken: import.meta.env.VITE_MAPBOX_TOKEN || '',
      });

      map.current.on('load', () => {
        map.current?.resize();
      });
    }

    return () => {
      map.current?.remove();
    };
  }, []);

  const handleSearch = async (preferences: SearchPreferences) => {
    setLoading(true);
    try {
      const response = await axios.post('/api/search', preferences);
      setProperties(response.data.top_candidates);
      setShowSearch(false);

      // Add markers to map
      if (map.current && response.data.top_candidates) {
        response.data.top_candidates.forEach((prop: Property) => {
          if (prop.latitude && prop.longitude) {
            new mapboxgl.Marker()
              .setLngLat([prop.longitude, prop.latitude])
              .setPopup(new mapboxgl.Popup().setHTML(createPopupContent(prop)))
              .addTo(map.current!);
          }
        });
      }
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const createPopupContent = (property: Property): string => {
    const scoreColor = property.total_score >= 0.8 ? 'green' : property.total_score >= 0.6 ? 'yellow' : 'red';

    return `
      <div style="padding: 10px; min-width: 200px;">
        <h3 style="margin: 0 0 10px 0; font-size: 14px;">${property.title}</h3>
        <p><strong>Price:</strong> ${property.price_vnd?.toLocaleString()} VND</p>
        <p><strong>Area:</strong> ${property.area_m2} m²</p>
        <p><strong>Score:</strong> <span style="color: ${scoreColor}">${(property.total_score * 100).toFixed(1)}%</span></p>
        <a href="${property.url}" target="_blank" style="color: #2563eb;">View Listing</a>
      </div>
    `;
  };

  return (
    <div className="h-screen flex">
      {/* Sidebar */}
      <div className="w-96 bg-white shadow-lg overflow-y-auto">
        <div className="p-4">
          <h1 className="text-2xl font-bold text-gray-800 mb-4">
            vn-real-estate-scout
          </h1>

          {showSearch ? (
            <SearchForm onSearch={handleSearch} loading={loading} />
          ) : (
            <PropertyList
              properties={properties}
              onSelect={setSelectedProperty}
              onNewSearch={() => setShowSearch(true)}
            />
          )}
        </div>
      </div>

      {/* Map */}
      <div className="flex-1">
        <div ref={mapContainer} className="w-full h-full" />
      </div>

      {/* Property Details Panel */}
      {selectedProperty && (
        <PropertyDetailsPanel
          property={selectedProperty}
          onClose={() => setSelectedProperty(null)}
        />
      )}
    </div>
  );
};

const SearchForm: React.FC<{
  onSearch: (prefs: SearchPreferences) => void;
  loading: boolean;
}> = ({ onSearch, loading }) => {
  const [preferences, setPreferences] = useState<SearchPreferences>({
    preferred_cities: ['Ho Chi Minh City'],
    property_types: ['apartment'],
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(preferences);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          City
        </label>
        <select
          value={preferences.preferred_cities[0]}
          onChange={(e) => setPreferences({ ...preferences, preferred_cities: [e.target.value] })}
          className="w-full border rounded px-3 py-2"
        >
          <option>Ho Chi Minh City</option>
          <option>Hanoi</option>
          <option>Da Nang</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Property Type
        </label>
        <select
          value={preferences.property_types[0]}
          onChange={(e) => setPreferences({ ...preferences, property_types: [e.target.value] })}
          className="w-full border rounded px-3 py-2"
        >
          <option>apartment</option>
          <option>house</option>
          <option>villa</option>
          <option>land</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Max Price (VND)
        </label>
        <input
          type="number"
          value={preferences.max_price || ''}
          onChange={(e) => setPreferences({ ...preferences, max_price: Number(e.target.value) })}
          className="w-full border rounded px-3 py-2"
          placeholder="3000000000"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Min Area (m²)
        </label>
        <input
          type="number"
          value={preferences.min_area || ''}
          onChange={(e) => setPreferences({ ...preferences, min_area: Number(e.target.value) })}
          className="w-full border rounded px-3 py-2"
          placeholder="50"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-primary text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
      >
        {loading ? 'Searching...' : 'Search Properties'}
      </button>
    </form>
  );
};

const PropertyList: React.FC<{
  properties: Property[];
  onSelect: (prop: Property) => void;
  onNewSearch: () => void;
}> = ({ properties, onSelect, onNewSearch }) => {
  return (
    <div>
      <button
        onClick={onNewSearch}
        className="w-full mb-4 bg-secondary text-white py-2 rounded hover:bg-green-700"
      >
        New Search
      </button>

      <h2 className="text-lg font-semibold mb-2">Top Recommendations</h2>

      <div className="space-y-2">
        {properties.map((property, index) => (
          <div
            key={property.listing_id}
            onClick={() => onSelect(property)}
            className="p-3 border rounded hover:bg-gray-50 cursor-pointer"
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="text-xs text-gray-500">#{index + 1}</div>
                <h3 className="font-medium text-sm">{property.title}</h3>
                <p className="text-xs text-gray-600">{property.address}</p>
                <p className="text-sm font-semibold text-green-600">
                  {property.price_vnd?.toLocaleString()} VND
                </p>
              </div>
              <div className="ml-2">
                <div className={`text-lg font-bold ${
                  property.total_score >= 0.8 ? 'text-green-600' :
                  property.total_score >= 0.6 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {(property.total_score * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const PropertyDetailsPanel: React.FC<{
  property: Property;
  onClose: () => void;
}> = ({ property, onClose }) => {
  return (
    <div className="w-80 bg-white shadow-lg overflow-y-auto">
      <div className="p-4">
        <button
          onClick={onClose}
          className="mb-4 text-sm text-gray-600 hover:text-gray-800"
        >
          ← Close
        </button>

        <h2 className="text-lg font-bold mb-2">{property.title}</h2>

        <div className="space-y-2 text-sm">
          <div>
            <span className="font-medium">Price:</span>{' '}
            {property.price_vnd?.toLocaleString()} VND
          </div>

          <div>
            <span className="font-medium">Area:</span>{' '}
            {property.area_m2} m²
          </div>

          <div>
            <span className="font-medium">Bedrooms:</span>{' '}
            {property.bedrooms}
          </div>

          <div>
            <span className="font-medium">Type:</span>{' '}
            {property.property_type}
          </div>

          <div>
            <span className="font-medium">Platform:</span>{' '}
            {property.platform}
          </div>

          <div>
            <span className="font-medium">Score:</span>{' '}
            <span className={
              property.total_score >= 0.8 ? 'text-green-600 font-bold' :
              property.total_score >= 0.6 ? 'text-yellow-600 font-bold' :
              'text-red-600 font-bold'
            }>
              {(property.total_score * 100).toFixed(1)}%
            </span>
          </div>

          {property.flags && property.flags.length > 0 && (
            <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded">
              <div className="font-medium text-yellow-800">Flags:</div>
              {property.flags.map((flag, i) => (
                <div key={i} className="text-xs text-yellow-700">⚠️ {flag}</div>
              ))}
            </div>
          )}

          {property.images && property.images.length > 0 && (
            <div className="mt-3">
              <div className="font-medium mb-1">Images:</div>
              <div className="grid grid-cols-2 gap-1">
                {property.images.slice(0, 4).map((img, i) => (
                  <img
                    key={i}
                    src={img}
                    alt={`Property ${i + 1}`}
                    className="w-full h-20 object-cover rounded"
                  />
                ))}
              </div>
            </div>
          )}

          <a
            href={property.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block mt-4 w-full bg-primary text-white text-center py-2 rounded hover:bg-blue-700"
          >
            View Original Listing
          </a>
        </div>
      </div>
    </div>
  );
};

export default PropertyMap;
