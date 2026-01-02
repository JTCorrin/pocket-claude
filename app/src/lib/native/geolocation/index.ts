/**
 * Geolocation module exports
 */

export type { Location, GeolocationState, WatcherOptions } from './types';
export { DEFAULT_WATCHER_OPTIONS } from './types';

export {
	startTracking,
	stopTracking,
	openLocationSettings,
	onLocationUpdate,
	clearHistory,
	getGeolocationState,
	getCurrentLocation,
	isTracking,
	getLocationHistory,
	getUpdateCount,
	getError,
	stopGeolocation
} from './geolocation.svelte';
