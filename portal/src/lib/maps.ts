/** External map links; embedded maps continue to use OpenStreetMap tiles. */
export function googleMapsUrl(location: string, action: 'map' | 'directions' = 'map') {
 const parameter = action === 'directions' ? 'destination' : 'query';
 const path = action === 'directions' ? 'dir' : 'search';
 return `https://www.google.com/maps/${path}/?api=1&${parameter}=${encodeURIComponent(location)}`;
}
