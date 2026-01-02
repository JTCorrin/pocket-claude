/**
 * Native capabilities module
 *
 * Provides unified access to Capacitor native plugins with
 * Svelte 5 runes for reactivity.
 *
 * ## Quick Start
 *
 * Initialize in +layout.svelte:
 * ```svelte
 * <script lang="ts">
 *   import { onMount, onDestroy } from 'svelte';
 *   import { initNativeCapabilities, stopNativeCapabilities } from '$lib/native';
 *
 *   onMount(() => initNativeCapabilities());
 *   onDestroy(() => stopNativeCapabilities());
 * </script>
 * ```
 *
 * ## Usage
 *
 * ```typescript
 * import {
 *   startTracking,
 *   onLocationUpdate,
 *   showNotification,
 *   impactLight
 * } from '$lib/native';
 *
 * // Start background location tracking
 * await startTracking();
 *
 * // React to location updates
 * onLocationUpdate(async (location) => {
 *   await impactLight();
 *   await showNotification('Location Updated', `${location.latitude}, ${location.longitude}`);
 * });
 * ```
 */

// Types
export type { PlatformInfo, CapabilityAvailability } from './types';

// Platform detection
export {
	initPlatformDetection,
	getPlatform,
	getCapabilities,
	isNative,
	isIOS,
	isAndroid,
	runOnNative,
	runIfAvailable
} from './platform.svelte';

// Geolocation
export type { Location, GeolocationState, WatcherOptions } from './geolocation';
export {
	DEFAULT_WATCHER_OPTIONS,
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
} from './geolocation';

// Notifications
export type { LocalNotification, NotificationState } from './notifications';
export {
	initNotifications,
	stopNotifications,
	checkPermissions,
	requestPermissions,
	showNotification,
	cancelNotification,
	cancelAllNotifications,
	onNotificationReceived,
	getNotificationState,
	getNotificationPermissionStatus
} from './notifications';

// Haptics
export {
	impactLight,
	impactMedium,
	impactHeavy,
	notificationSuccess,
	notificationWarning,
	notificationError,
	selectionChanged,
	vibrate
} from './haptics';

// Initialization imports
import { initPlatformDetection } from './platform.svelte';
import { initNotifications, stopNotifications } from './notifications';
import { stopGeolocation } from './geolocation';

/**
 * Initialize all native capabilities
 * Call once in root +layout.svelte
 */
export async function initNativeCapabilities(): Promise<void> {
	// Platform detection first (sync)
	initPlatformDetection();

	// Initialize notifications
	await initNotifications();
}

/**
 * Cleanup all native capabilities
 */
export async function stopNativeCapabilities(): Promise<void> {
	await Promise.all([stopGeolocation(), stopNotifications()]);
}
