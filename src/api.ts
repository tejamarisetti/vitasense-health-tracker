/**
 * Global API Client Configuration
 * Uses import.meta.env.VITE_API_BASE_URL when set (e.g. on Vercel pointing to Render),
 * otherwise defaults to relative path '' (which leverages the Vite dev proxy).
 */

const RAW_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim();
export const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, '');

/**
 * Builds a full API endpoint URL.
 * Example: apiEndpoint('/api/auth/demo') -> 'https://vitasense-backend-druv.onrender.com/api/auth/demo'
 */
export function apiEndpoint(path: string): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${cleanPath}` : cleanPath;
}

