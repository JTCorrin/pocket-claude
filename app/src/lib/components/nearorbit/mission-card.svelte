<script lang="ts">
	import { cn } from '$lib/utils.js';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import ClockIcon from '@lucide/svelte/icons/clock';
	import TerminalBlock from './terminal-block.svelte';
	import type { Mission, MissionStatus } from './types.js';

	interface Props {
		/** The mission data to display */
		mission: Mission;
		/** Click handler for opening the mission */
		onclick?: () => void;
		/** Additional CSS classes */
		class?: string;
	}

	let { mission, onclick, class: className }: Props = $props();

	const hasTerminalPreview = $derived(
		mission.terminalPreview && mission.terminalPreview.length > 0
	);

	/**
	 * Get status indicator color and label
	 */
	function getStatusConfig(status: MissionStatus): {
		dotClass: string;
		labelClass: string;
		label: string;
		animate: boolean;
	} {
		switch (status) {
			case 'active':
				return {
					dotClass: 'bg-teal-400',
					labelClass: 'text-teal-400',
					label: 'ACTIVE',
					animate: true
				};
			case 'paused':
				return {
					dotClass: 'bg-yellow-500',
					labelClass: 'text-yellow-500',
					label: 'PAUSED',
					animate: false
				};
			case 'completed':
				return {
					dotClass: 'bg-green-500',
					labelClass: 'text-green-500',
					label: 'COMPLETED',
					animate: false
				};
			case 'failed':
				return {
					dotClass: 'bg-red-500',
					labelClass: 'text-red-500',
					label: 'FAILED',
					animate: false
				};
			default:
				return {
					dotClass: 'bg-zinc-500',
					labelClass: 'text-zinc-500',
					label: 'UNKNOWN',
					animate: false
				};
		}
	}

	const statusConfig = $derived(getStatusConfig(mission.status));
</script>

<button
	type="button"
	{onclick}
	class={cn(
		'group p-5 bg-zinc-900 border border-zinc-800 rounded-xl text-left w-full',
		'hover:border-teal-400/50 cursor-pointer transition-all relative overflow-hidden',
		mission.status === 'active' && 'hover:border-teal-400/50',
		mission.status === 'paused' && 'hover:border-zinc-600',
		className
	)}
>
	<!-- Chevron indicator -->
	<div
		class="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity"
	>
		<ChevronRightIcon class="w-5 h-5 text-zinc-500 group-hover:text-teal-400" />
	</div>

	<!-- Status Row -->
	<div class="flex items-center gap-3 mb-3">
		<div
			class={cn('w-2 h-2 rounded-full', statusConfig.dotClass, statusConfig.animate && 'animate-pulse')}
		></div>
		<span class={cn('text-xs font-bold tracking-wide', statusConfig.labelClass)}>
			{statusConfig.label}
		</span>
		<span class="text-zinc-500 text-xs font-mono">ID: {mission.id}</span>
	</div>

	<!-- Title -->
	<h3 class="text-lg font-medium text-white mb-1 pr-8">{mission.title}</h3>

	<!-- Description -->
	<p class="text-sm text-zinc-400 mb-4 line-clamp-1">{mission.description}</p>

	<!-- Terminal Preview or Status Info -->
	{#if hasTerminalPreview && mission.terminalPreview}
		<div class="bg-[#0d0d0f] rounded-lg p-3 font-mono text-xs text-zinc-400 border border-zinc-800/50">
			<div class="flex justify-between mb-1 text-zinc-600">
				<span>Terminal Output</span>
				{#if mission.lastActivity}
					<span>{mission.lastActivity}</span>
				{/if}
			</div>
			{#each mission.terminalPreview.slice(0, 3) as line, index (index)}
				<div
					class={cn(
						line.type === 'command' && 'text-zinc-300',
						line.type === 'success' && 'text-green-400',
						line.type === 'error' && 'text-red-400',
						line.type === 'info' && 'opacity-50'
					)}
				>
					{#if line.type === 'command'}$ {/if}{line.content}
				</div>
			{/each}
		</div>
	{:else if mission.status === 'paused'}
		<div class="text-xs text-zinc-500 flex items-center gap-2">
			<ClockIcon class="w-3 h-3" />
			{mission.error || 'Waiting for user input'}
		</div>
	{:else if mission.error}
		<div class="text-xs text-red-400 flex items-center gap-2">
			{mission.error}
		</div>
	{/if}
</button>
