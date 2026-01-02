/**
 * Geolocation types
 */

/**
 * Location coordinates from background geolocation plugin
 */
export interface Location {
	latitude: number;
	longitude: number;
	accuracy: number;
	altitude: number | null;
	altitudeAccuracy: number | null;
	bearing: number | null;
	speed: number | null;
	time: number | null;
	simulated: boolean;
}

/**
 * Geolocation watcher options
 */
export interface WatcherOptions {
	/** Android notification message for background tracking */
	backgroundMessage?: string;
	/** Android notification title for background tracking */
	backgroundTitle?: string;
	/** Auto-request permissions on start */
	requestPermissions?: boolean;
	/** Allow stale locations while getting GPS fix */
	stale?: boolean;
	/** Minimum distance in meters between updates */
	distanceFilter?: number;
}

/**
 * Geolocation state
 */
export interface GeolocationState {
	currentLocation: Location | null;
	isTracking: boolean;
	watcherId: string | null;
	error: string | null;
	locationHistory: Location[];
	updateCount: number;
}

/**
 * Default watcher options for Guardian app
 */
export const DEFAULT_WATCHER_OPTIONS: WatcherOptions = {
	backgroundMessage: 'Guardian is tracking your location for safety',
	backgroundTitle: 'Location Active',
	requestPermissions: true,
	stale: false,
	distanceFilter: 10
};
