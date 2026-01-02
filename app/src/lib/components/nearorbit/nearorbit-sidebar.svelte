<script lang="ts">
	import { cn } from '$lib/utils.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import LayoutGridIcon from '@lucide/svelte/icons/layout-grid';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';
	import type { ComponentProps } from 'svelte';
	import type { ViewType, ServerStatus } from './types.js';

	interface Props extends ComponentProps<typeof Sidebar.Root> {
		/** Currently active view */
		activeView?: ViewType;
		/** Handler for navigation changes */
		onnavigate?: (view: ViewType) => void;
		/** Server status information */
		serverStatus?: ServerStatus;
	}

	let {
		activeView = 'dashboard',
		onnavigate,
		serverStatus = {
			name: 'Home Server',
			isOnline: true,
			cpuUsage: '12%',
			memoryUsage: '4GB'
		},
		ref = $bindable(null),
		collapsible = 'icon',
		...restProps
	}: Props = $props();

	const navItems: { id: ViewType; label: string; icon: typeof LayoutGridIcon }[] = [
		{ id: 'dashboard', label: 'Missions', icon: LayoutGridIcon },
		{ id: 'settings', label: 'Settings', icon: Settings2Icon }
	];

	/**
	 * Check if a nav item should be highlighted
	 * The dashboard nav item is active for both dashboard and chat views
	 */
	function isNavActive(navId: ViewType): boolean {
		if (navId === 'dashboard') {
			return activeView === 'dashboard' || activeView === 'chat';
		}
		return activeView === navId;
	}
</script>

<Sidebar.Root {collapsible} {...restProps}>
	<!-- Branding Header -->
	<Sidebar.Header class="border-b border-zinc-800/50">
		<div class="flex items-center gap-3 px-2 py-2">
			<!-- Hexagon Logo -->
			<svg
				width="28"
				height="28"
				viewBox="0 0 100 100"
				fill="none"
				class="text-teal-400 shrink-0"
			>
				<path
					d="M50 20 L85 40 L85 75 L50 95 L15 75 L15 40 Z"
					stroke="currentColor"
					stroke-width="8"
				/>
			</svg>
			<span class="font-bold text-white tracking-tight group-data-[collapsible=icon]:hidden">
				Near Orbit
			</span>
		</div>
	</Sidebar.Header>

	<!-- Navigation -->
	<Sidebar.Content>
		<Sidebar.Group>
			<Sidebar.GroupContent>
				<Sidebar.Menu>
					{#each navItems as item (item.id)}
						{@const isActive = isNavActive(item.id)}
						<Sidebar.MenuItem>
							<Sidebar.MenuButton
								{isActive}
								tooltipContent={item.label}
								onclick={() => onnavigate?.(item.id)}
								class={cn(
									isActive && 'bg-zinc-800 text-teal-400',
									!isActive && 'text-zinc-500 hover:text-white hover:bg-zinc-800/50'
								)}
							>
								<item.icon class="w-5 h-5" />
								<span>{item.label}</span>
							</Sidebar.MenuButton>
						</Sidebar.MenuItem>
					{/each}
				</Sidebar.Menu>
			</Sidebar.GroupContent>
		</Sidebar.Group>
	</Sidebar.Content>

	<!-- Server Status Footer -->
	<Sidebar.Footer class="border-t border-zinc-800">
		<div class="flex items-center gap-3 px-2 py-2">
			<!-- Server Avatar -->
			<div class="relative shrink-0">
				<div
					class="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-xs font-mono border border-zinc-700"
				>
					SRV
				</div>
				<div
					class={cn(
						'absolute -bottom-1 -right-1 w-3 h-3 border-2 border-zinc-900 rounded-full',
						serverStatus.isOnline ? 'bg-green-500' : 'bg-red-500'
					)}
				></div>
			</div>

			<!-- Server Info (hidden when collapsed) -->
			<div class="overflow-hidden group-data-[collapsible=icon]:hidden">
				<div class="text-sm text-white font-medium truncate">{serverStatus.name}</div>
				{#if serverStatus.cpuUsage && serverStatus.memoryUsage}
					<div class="text-xs text-zinc-500 truncate">
						Cpu: {serverStatus.cpuUsage} - Mem: {serverStatus.memoryUsage}
					</div>
				{:else}
					<div class="text-xs text-zinc-500 truncate">
						{serverStatus.isOnline ? 'Connected' : 'Disconnected'}
					</div>
				{/if}
			</div>
		</div>
	</Sidebar.Footer>

	<Sidebar.Rail />
</Sidebar.Root>
