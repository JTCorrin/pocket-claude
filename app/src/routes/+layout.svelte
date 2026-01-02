<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	// API offline support
	import { initOfflineSupport, stopOfflineSupport } from '$lib/api/offline';

	// Native capabilities
	import { initNativeCapabilities, stopNativeCapabilities } from '$lib/native';

	let { children } = $props();

	onMount(async () => {
		// Initialize offline support (network detection, request queue)
		initOfflineSupport();

		// Initialize native capabilities (platform, notifications)
		await initNativeCapabilities();
	});

	onDestroy(() => {
		stopOfflineSupport();
		stopNativeCapabilities();
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{@render children()}
