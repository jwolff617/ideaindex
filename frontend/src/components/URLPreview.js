import React, { useState, useEffect } from 'react';
import { API } from '../App';
import axios from 'axios';
import { ExternalLink } from 'lucide-react';

const URLPreview = ({ url }) => {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPreview();
  }, [url]);

  const fetchPreview = async () => {
    try {
      const response = await axios.get(`${API}/url-preview?url=${encodeURIComponent(url)}`);
      setPreview(response.data);
    } catch (error) {
      console.error('Failed to fetch URL preview', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="border border-gray-200 rounded-lg p-3 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div className="h-3 bg-gray-200 rounded w-1/2"></div>
      </div>
    );
  }

  if (!preview) return null;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="block border border-gray-200 rounded-lg overflow-hidden hover:border-emerald-300 transition-colors group my-3"
    >
      {preview.image && (
        <img
          src={preview.image}
          alt={preview.title}
          className="w-full h-48 object-cover"
          onError={(e) => e.target.style.display = 'none'}
        />
      )}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h4 className="font-semibold text-gray-900 group-hover:text-emerald-600 transition-colors line-clamp-2 mb-1">
              {preview.title}
            </h4>
            {preview.description && (
              <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                {preview.description}
              </p>
            )}
            <div className="flex items-center space-x-1 text-xs text-gray-500">
              <ExternalLink size={12} />
              <span>{preview.domain}</span>
            </div>
          </div>
        </div>
      </div>
    </a>
  );
};

// Component to detect and render URLs in text
export const TextWithURLPreviews = ({ text }) => {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const urls = text.match(urlRegex) || [];
  
  if (urls.length === 0) {
    return <p className="text-gray-700 whitespace-pre-wrap">{text}</p>;
  }

  // Split text by URLs
  const parts = text.split(urlRegex);
  
  return (
    <div>
      {parts.map((part, index) => {
        if (urlRegex.test(part)) {
          return (
            <div key={index}>
              <URLPreview url={part} />
            </div>
          );
        }
        return part ? (
          <p key={index} className="text-gray-700 whitespace-pre-wrap">
            {part}
          </p>
        ) : null;
      })}
    </div>
  );
};

export default URLPreview;
