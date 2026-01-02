/**
 * Local notifications management with Svelte 5 runes
 */

import { LocalNotifications } from '@capacitor/local-notifications';
import type { LocalNotification, NotificationState } from './types';
import { getCapabilities } from '../platform.svelte';

// Reactive state
let notificationState = $state<NotificationState>({
	permissionStatus: 'unknown',
	lastNotificationId: 0
});

let initialized = false;
let notificationListeners: Array<(notification: LocalNotification) => void> = [];

/**
 * Initialize notifications module
 */
export async function initNotifications(): Promise<void> {
	if (initialized || typeof window === 'undefined') return;
	if (!getCapabilities().notifications) return;

	initialized = true;

	await checkPermissions();

	// Listen for notification actions
	try {
		await LocalNotifications.addListener('localNotificationReceived', (notification) => {
			notificationListeners.forEach((cb) =>
				cb({
					id: notification.id,
					title: notification.title ?? '',
					body: notification.body ?? '',
					extra: notification.extra
				})
			);
		});
	} catch {
		// Ignore listener errors
	}
}

/**
 * Check notification permissions
 */
export async function checkPermissions(): Promise<NotificationState['permissionStatus']> {
	if (!getCapabilities().notifications) {
		notificationState.permissionStatus = 'denied';
		return 'denied';
	}

	try {
		const status = await LocalNotifications.checkPermissions();
		// Map 'prompt-with-rationale' to our type union
		const displayStatus = status.display as NotificationState['permissionStatus'];
		notificationState.permissionStatus = displayStatus;
		return displayStatus;
	} catch {
		return 'denied';
	}
}

/**
 * Request notification permissions
 */
export async function requestPermissions(): Promise<boolean> {
	if (!getCapabilities().notifications) return false;

	try {
		const status = await LocalNotifications.requestPermissions();
		const displayStatus = status.display as NotificationState['permissionStatus'];
		notificationState.permissionStatus = displayStatus;
		return status.display === 'granted';
	} catch {
		return false;
	}
}

/**
 * Show a local notification immediately
 *
 * @param title - Notification title
 * @param body - Notification body text
 * @param extra - Optional extra data
 * @returns Notification ID or null if failed
 */
export async function showNotification(
	title: string,
	body: string,
	extra?: Record<string, unknown>
): Promise<number | null> {
	if (!getCapabilities().notifications) return null;

	// Request permissions if needed
	if (notificationState.permissionStatus !== 'granted') {
		const granted = await requestPermissions();
		if (!granted) return null;
	}

	const id = ++notificationState.lastNotificationId;

	try {
		await LocalNotifications.schedule({
			notifications: [
				{
					id,
					title,
					body,
					extra
				}
			]
		});
		return id;
	} catch {
		return null;
	}
}

/**
 * Cancel a notification by ID
 */
export async function cancelNotification(id: number): Promise<void> {
	if (!getCapabilities().notifications) return;

	try {
		await LocalNotifications.cancel({ notifications: [{ id }] });
	} catch {
		// Ignore errors
	}
}

/**
 * Cancel all pending notifications
 */
export async function cancelAllNotifications(): Promise<void> {
	if (!getCapabilities().notifications) return;

	try {
		const pending = await LocalNotifications.getPending();
		if (pending.notifications.length > 0) {
			await LocalNotifications.cancel({ notifications: pending.notifications });
		}
	} catch {
		// Ignore errors
	}
}

/**
 * Subscribe to notification received events
 */
export function onNotificationReceived(
	callback: (notification: LocalNotification) => void
): () => void {
	notificationListeners.push(callback);
	return () => {
		const index = notificationListeners.indexOf(callback);
		if (index > -1) notificationListeners.splice(index, 1);
	};
}

// Getters

/**
 * Get notification state (reactive)
 */
export function getNotificationState(): NotificationState {
	return notificationState;
}

/**
 * Get notification permission status (reactive)
 */
export function getNotificationPermissionStatus(): NotificationState['permissionStatus'] {
	return notificationState.permissionStatus;
}

/**
 * Cleanup notifications module
 */
export async function stopNotifications(): Promise<void> {
	if (getCapabilities().notifications) {
		try {
			await LocalNotifications.removeAllListeners();
		} catch {
			// Ignore errors
		}
	}
	initialized = false;
	notificationListeners = [];
}
