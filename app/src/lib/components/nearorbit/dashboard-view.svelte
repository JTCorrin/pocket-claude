<script lang="ts">
	import { cn } from '$lib/utils.js';
	import CheckCircleIcon from '@lucide/svelte/icons/check-circle';
	import XCircleIcon from '@lucide/svelte/icons/x-circle';
	import MissionCard from './mission-card.svelte';
	import type { Mission, HistoryItem } from './types.js';

	interface Props {
		/** Active and paused missions to display */
		activeMissions?: Mission[];
		/** Recent history items */
		historyItems?: HistoryItem[];
		/** Handler for opening a mission */
		onopenmission?: (mission: Mission) => void;
		/** Handler for opening a history item */
		onopenhistory?: (item: HistoryItem) => void;
		/** Additional CSS classes */
		class?: string;
	}

	let {
		activeMissions = [],
		historyItems = [],
		onopenmission,
		onopenhistory,
		class: className
	}: Props = $props();
</script>

<div class={cn('flex-1 overflow-y-auto p-6', className)}>
	<div class="max-w-5xl mx-auto w-full">
		<!-- Running Now Section -->
		{#if activeMissions.length > 0}
			<h3 class="text-xs font-mono text-zinc-500 uppercase tracking-widest mb-4">
				Running Now
			</h3>
			<div class="grid md:grid-cols-2 gap-4 mb-8">
				{#each activeMissions as mission (mission.id)}
					<MissionCard {mission} onclick={() => onopenmission?.(mission)} />
				{/each}
			</div>
		{/if}

		<!-- Recent History Section -->
		{#if historyItems.length > 0}
			<h3 class="text-xs font-mono text-zinc-500 uppercase tracking-widest mb-4">
				Recent History
			</h3>
			<div class="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
				<div class="divide-y divide-zinc-800">
					{#each historyItems as item (item.id)}
						<button
							type="button"
							class="w-full p-4 flex items-center justify-between hover:bg-zinc-800/50 cursor-pointer transition-colors text-left"
							onclick={() => onopenhistory?.(item)}
						>
							<div class="flex items-center gap-4">
								<!-- Status Icon -->
								<div
									class={cn(
										'p-2 bg-zinc-800 rounded-lg',
										item.status === 'completed' ? 'text-zinc-400' : 'text-red-400'
									)}
								>
									{#if item.status === 'completed'}
										<CheckCircleIcon class="w-4 h-4" />
									{:else}
										<XCircleIcon class="w-4 h-4" />
									{/if}
								</div>

								<!-- Item Info -->
								<div>
									<div class="text-sm text-white font-medium">{item.title}</div>
									<div class="text-xs text-zinc-500">
										{#if item.status === 'completed'}
											Completed {item.completedAt}
										{:else}
											Failed{#if item.error} - {item.error}{/if}
										{/if}
									</div>
								</div>
							</div>

							<!-- Duration -->
							<div class="text-xs text-zinc-500 font-mono">{item.duration} duration</div>
						</button>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Empty State -->
		{#if activeMissions.length === 0 && historyItems.length === 0}
			<div class="flex flex-col items-center justify-center py-16 text-center">
				<div class="w-16 h-16 rounded-full bg-zinc-800 flex items-center justify-center mb-4">
					<svg
						width="32"
						height="32"
						viewBox="0 0 100 100"
						fill="none"
						class="text-zinc-600"
					>
						<path
							d="M50 20 L85 40 L85 75 L50 95 L15 75 L15 40 Z"
							stroke="currentColor"
							stroke-width="6"
						/>
					</svg>
				</div>
				<h3 class="text-lg font-medium text-white mb-2">No Active Missions</h3>
				<p class="text-sm text-zinc-500 max-w-sm">
					Start a new mission to get your agent working on a task. Your active and recent missions will appear here.
				</p>
			</div>
		{/if}
	</div>
</div>
