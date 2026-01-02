/**
 * Background geolocation tracking with Svelte 5 runes
 *
 * Uses @capacitor-community/background-geolocation for true
 * background location tracking on iOS and Android.
 */

import { registerPlugin } from '@capacitor/core';
import type { BackgroundGeolocationPlugin, Location as PluginLocation, CallbackError } from '@capacitor-community/background-geolocation';
import type { Location, GeolocationState, WatcherOptions } from './types';
import { DEFAULT_WATCHER_OPTIONS } from './types';

const BackgroundGeolocation = registerPlugin<BackgroundGeolocationPlugin>('BackgroundGeolocation');
import { getCapabilities } from '../platform.svelte';

// Maximum locations to keep in history
const MAX_HISTORY_SIZE = 100;

// Reactive state
let geolocationState = $state<GeolocationState>({
	currentLocation: null,
	isTracking: false,
	watcherId: null,
	error: null,
	locationHistory: [],
	updateCount: 0
});

// Callbacks for location updates
let locationCallbacks: Array<(location: Location) => void> = [];

/**
 * Start location tracking (works in foreground AND background)
 *
 * @param options - Watcher configuration options
 * @returns true if tracking started successfully
 */
export async function startTracking(options?: Partial<WatcherOptions>): Promise<boolean> {
	if (!getCapabilities().geolocation) {
		geolocationState.error = 'Geolocation not available on this platform';
		return false;
	}

	if (geolocationState.isTracking) {
		return true; // Already tracking
	}

	const watcherOptions = { ...DEFAULT_WATCHER_OPTIONS, ...options };

	try {
		const watcherId = await BackgroundGeolocation.addWatcher(
			{
				backgroundMessage: watcherOptions.backgroundMessage,
				backgroundTitle: watcherOptions.backgroundTitle,
				requestPermissions: watcherOptions.requestPermissions,
				stale: watcherOptions.stale,
				distanceFilter: watcherOptions.distanceFilter
			},
			(location: PluginLocation | undefined, error: CallbackError | undefined) => {
				if (error) {
					geolocationState.error = error.message ?? 'Unknown location error';
					return;
				}

				if (location) {
					const loc: Location = {
						latitude: location.latitude,
						longitude: location.longitude,
						accuracy: location.accuracy,
						altitude: location.altitude ?? null,
						altitudeAccuracy: location.altitudeAccuracy ?? null,
						bearing: location.bearing ?? null,
						speed: location.speed ?? null,
						time: location.time ?? null,
						simulated: location.simulated ?? false
					};

					// Update state
					geolocationState.currentLocation = loc;
					geolocationState.error = null;
					geolocationState.updateCount++;

					// Add to history
					geolocationState.locationHistory = [
						...geolocationState.locationHistory.slice(-(MAX_HISTORY_SIZE - 1)),
						loc
					];

					// Notify callbacks
					locationCallbacks.forEach((cb) => cb(loc));
				}
			}
		);

		geolocationState.watcherId = watcherId;
		geolocationState.isTracking = true;
		geolocationState.error = null;

		return true;
	} catch (error) {
		geolocationState.error = error instanceof Error ? error.message : 'Failed to start tracking';
		return false;
	}
}

/**
 * Stop location tracking
 */
export async function stopTracking(): Promise<void> {
	if (!geolocationState.watcherId) return;

	try {
		await BackgroundGeolocation.removeWatcher({ id: geolocationState.watcherId });
	} catch {
		// Ignore errors when stopping
	}

	geolocationState.watcherId = null;
	geolocationState.isTracking = false;
}

/**
 * Open device location settings
 * Useful when user has denied permissions
 */
export async function openLocationSettings(): Promise<void> {
	if (!getCapabilities().geolocation) return;

	try {
		await BackgroundGeolocation.openSettings();
	} catch {
		// Ignore errors
	}
}

/**
 * Subscribe to location updates
 *
 * @param callback - Function called on each location update
 * @returns Cleanup function to unsubscribe
 */
export function onLocationUpdate(callback: (location: Location) => void): () => void {
	locationCallbacks.push(callback);
	return () => {
		const index = locationCallbacks.indexOf(callback);
		if (index > -1) locationCallbacks.splice(index, 1);
	};
}

/**
 * Clear location history
 */
export function clearHistory(): void {
	geolocationState.locationHistory = [];
}

// Getters for reactive state

/**
 * Get full geolocation state (reactive)
 */
export function getGeolocationState(): GeolocationState {
	return geolocationState;
}

/**
 * Get current location (reactive)
 */
export function getCurrentLocation(): Location | null {
	return geolocationState.currentLocation;
}

/**
 * Check if tracking is active (reactive)
 */
export function isTracking(): boolean {
	return geolocationState.isTracking;
}

/**
 * Get location history (reactive)
 */
export function getLocationHistory(): Location[] {
	return geolocationState.locationHistory;
}

/**
 * Get update count (reactive)
 */
export function getUpdateCount(): number {
	return geolocationState.updateCount;
}

/**
 * Get last error (reactive)
 */
export function getError(): string | null {
	return geolocationState.error;
}

/**
 * Cleanup geolocation resources
 */
export async function stopGeolocation(): Promise<void> {
	await stopTracking();
	locationCallbacks = [];
}
