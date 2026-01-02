<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';

	import {
		// Platform
		getPlatform,
		getCapabilities,

		// Geolocation
		getGeolocationState,
		startTracking,
		stopTracking,
		openLocationSettings,
		onLocationUpdate,
		clearHistory,

		// Notifications
		getNotificationState,
		showNotification,
		requestPermissions,

		// Haptics
		impactLight,
		impactMedium,
		impactHeavy,
		notificationSuccess,

		// Types
		type Location
	} from '$lib/native';

	// Get reactive state
	const platform = getPlatform();
	const capabilities = getCapabilities();
	const geoState = getGeolocationState();
	const notifState = getNotificationState();

	// Local state
	let notifyOnUpdate = $state(false);
	let hapticOnUpdate = $state(true);
	let cleanupLocationListener: (() => void) | null = null;

	onMount(() => {
		// Subscribe to location updates for haptics and notifications
		cleanupLocationListener = onLocationUpdate(handleLocationUpdate);
	});

	onDestroy(() => {
		cleanupLocationListener?.();
	});

	async function handleLocationUpdate(location: Location) {
		// Haptic feedback on each update
		if (hapticOnUpdate) {
			await impactLight();
		}

		// Show notification if enabled (every 5th update to avoid spam)
		if (notifyOnUpdate && geoState.updateCount % 5 === 0) {
			await showNotification(
				'Location Updated',
				`${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`
			);
		}
	}

	async function handleStartTracking() {
		const started = await startTracking();
		if (started) {
			await notificationSuccess();
			await showNotification('Tracking Started', 'Location tracking is now active');
		}
	}

	async function handleStopTracking() {
		await stopTracking();
		await impactMedium();
	}

	async function handleRequestNotificationPermissions() {
		await requestPermissions();
		await impactLight();
	}

	async function handleClearHistory() {
		clearHistory();
		await impactLight();
	}

	function formatCoords(lat: number, lng: number): string {
		return `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
	}

	function formatTime(timestamp: number | null): string {
		if (!timestamp) return 'N/A';
		return new Date(timestamp).toLocaleTimeString();
	}
</script>

<div class="container mx-auto max-w-2xl space-y-6 p-4">
	<h1 class="text-2xl font-bold">Native Capabilities Demo</h1>
	<p class="text-muted-foreground text-sm">
		Test background geolocation, notifications, and haptics
	</p>

	<!-- Platform Info Card -->
	<Card.Root>
		<Card.Header>
			<Card.Title>Platform Information</Card.Title>
		</Card.Header>
		<Card.Content>
			<dl class="grid grid-cols-2 gap-2 text-sm">
				<dt class="font-medium">Platform:</dt>
				<dd class="capitalize">{platform.platform}</dd>
				<dt class="font-medium">Is Native:</dt>
				<dd>{platform.isNative ? 'Yes' : 'No (Web)'}</dd>
			</dl>

			<h4 class="mt-4 mb-2 font-medium">Available Capabilities:</h4>
			<ul class="space-y-1 text-sm">
				<li class="flex items-center gap-2">
					<span class={capabilities.geolocation ? 'text-green-600' : 'text-red-600'}>
						{capabilities.geolocation ? '✓' : '✗'}
					</span>
					Background Geolocation
				</li>
				<li class="flex items-center gap-2">
					<span class={capabilities.notifications ? 'text-green-600' : 'text-red-600'}>
						{capabilities.notifications ? '✓' : '✗'}
					</span>
					Local Notifications
				</li>
				<li class="flex items-center gap-2">
					<span class={capabilities.haptics ? 'text-green-600' : 'text-red-600'}>
						{capabilities.haptics ? '✓' : '✗'}
					</span>
					Haptics
				</li>
			</ul>
		</Card.Content>
	</Card.Root>

	<!-- Location Tracking Card -->
	<Card.Root>
		<Card.Header>
			<Card.Title>Location Tracking</Card.Title>
			<Card.Description>
				{#if geoState.isTracking}
					<span class="text-green-600">● Tracking active</span> - works in background
				{:else}
					<span class="text-muted-foreground">○ Not tracking</span>
				{/if}
			</Card.Description>
		</Card.Header>
		<Card.Content class="space-y-4">
			<dl class="grid grid-cols-2 gap-2 text-sm">
				<dt class="font-medium">Updates:</dt>
				<dd>{geoState.updateCount}</dd>
				<dt class="font-medium">History:</dt>
				<dd>{geoState.locationHistory.length} positions</dd>
			</dl>

			{#if geoState.currentLocation}
				<div class="bg-muted rounded-lg p-3">
					<p class="mb-1 font-mono text-sm">
						{formatCoords(geoState.currentLocation.latitude, geoState.currentLocation.longitude)}
					</p>
					<p class="text-muted-foreground text-xs">
						Accuracy: {Math.round(geoState.currentLocation.accuracy)}m |
						{formatTime(geoState.currentLocation.time)}
					</p>
					{#if geoState.currentLocation.speed !== null}
						<p class="text-muted-foreground text-xs">
							Speed: {(geoState.currentLocation.speed * 3.6).toFixed(1)} km/h
						</p>
					{/if}
				</div>
			{/if}

			{#if geoState.error}
				<p class="text-destructive text-sm">{geoState.error}</p>
			{/if}

			<!-- Options -->
			<div class="flex flex-wrap gap-4 text-sm">
				<label class="flex items-center gap-2">
					<input type="checkbox" bind:checked={hapticOnUpdate} />
					Haptic on update
				</label>
				<label class="flex items-center gap-2">
					<input type="checkbox" bind:checked={notifyOnUpdate} />
					Notify on update
				</label>
			</div>

			<div class="flex flex-wrap gap-2">
				{#if !geoState.isTracking}
					<Button onclick={handleStartTracking} size="sm">Start Tracking</Button>
				{:else}
					<Button onclick={handleStopTracking} variant="secondary" size="sm">Stop Tracking</Button>
				{/if}
				<Button onclick={() => openLocationSettings()} variant="outline" size="sm">
					Location Settings
				</Button>
				<Button onclick={handleClearHistory} variant="ghost" size="sm">Clear History</Button>
			</div>

			<!-- Location History -->
			{#if geoState.locationHistory.length > 0}
				<div class="max-h-40 overflow-y-auto">
					<h4 class="mb-2 text-sm font-medium">Recent Positions:</h4>
					<ul class="space-y-1 font-mono text-xs">
						{#each geoState.locationHistory.slice(-10).reverse() as loc}
							<li class="text-muted-foreground">
								{formatCoords(loc.latitude, loc.longitude)} - {formatTime(loc.time)}
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</Card.Content>
	</Card.Root>

	<!-- Notifications Card -->
	<Card.Root>
		<Card.Header>
			<Card.Title>Local Notifications</Card.Title>
			<Card.Description>
				Permission: <span class="capitalize">{notifState.permissionStatus}</span>
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="flex flex-wrap gap-2">
				{#if notifState.permissionStatus !== 'granted'}
					<Button onclick={handleRequestNotificationPermissions} size="sm">
						Request Permission
					</Button>
				{/if}
				<Button
					onclick={() => showNotification('Test Notification', 'This is a test notification!')}
					variant="outline"
					size="sm"
				>
					Send Test
				</Button>
			</div>
		</Card.Content>
	</Card.Root>

	<!-- Haptics Card -->
	<Card.Root>
		<Card.Header>
			<Card.Title>Haptic Feedback</Card.Title>
			<Card.Description>Test different haptic patterns</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="flex flex-wrap gap-2">
				<Button onclick={() => impactLight()} variant="outline" size="sm">Light</Button>
				<Button onclick={() => impactMedium()} variant="outline" size="sm">Medium</Button>
				<Button onclick={() => impactHeavy()} variant="outline" size="sm">Heavy</Button>
				<Button onclick={() => notificationSuccess()} variant="outline" size="sm">Success</Button>
			</div>
		</Card.Content>
	</Card.Root>
</div>
