<script lang="ts">
	import { cn } from '$lib/utils.js';
	import IntegrationCard from './integration-card.svelte';
	import type { Integration, IntegrationProvider } from './types.js';

	interface Props {
		/** List of integrations to display */
		integrations?: Integration[];
		/** Whether auto-commit is enabled */
		autoCommit?: boolean;
		/** Budget limit value */
		budgetLimit?: string;
		/** Handler for integration actions */
		onintegrationaction?: (
			provider: IntegrationProvider,
			action: 'connect' | 'disconnect' | 'save'
		) => void;
		/** Handler for integration input changes */
		onintegrationinput?: (provider: IntegrationProvider, field: string, value: string) => void;
		/** Handler for auto-commit toggle */
		onautocommittoggle?: (enabled: boolean) => void;
		/** Handler for budget limit change */
		onbudgetchange?: (value: string) => void;
		/** Additional CSS classes */
		class?: string;
	}

	let {
		integrations = [],
		autoCommit = false,
		budgetLimit = '$5.00',
		onintegrationaction,
		onintegrationinput,
		onautocommittoggle,
		onbudgetchange,
		class: className
	}: Props = $props();

	// Track configuring integration input values
	let giteaInstanceUrl = $state('');
	let giteaAccessToken = $state('');
</script>

<div class={cn('flex-1 overflow-y-auto p-6', className)}>
	<div class="max-w-3xl mx-auto w-full space-y-8">
		<!-- Integrations Section -->
		<div>
			<h3 class="text-xl font-medium text-white mb-2">Integrations</h3>
			<p class="text-sm text-zinc-500 mb-6">
				Connect your git providers to allow agents to clone, push, and create PRs.
			</p>

			<div class="space-y-4">
				{#each integrations as integration (integration.provider)}
					<IntegrationCard
						{integration}
						onaction={onintegrationaction}
						oninputchange={(provider, field, value) => {
							if (provider === 'gitea') {
								if (field === 'instanceUrl') giteaInstanceUrl = value;
								if (field === 'accessToken') giteaAccessToken = value;
							}
							onintegrationinput?.(provider, field, value);
						}}
						instanceUrl={integration.provider === 'gitea' ? giteaInstanceUrl : undefined}
						accessToken={integration.provider === 'gitea' ? giteaAccessToken : undefined}
					/>
				{/each}
			</div>
		</div>

		<!-- Agent Behavior Section -->
		<div>
			<h3 class="text-xl font-medium text-white mb-2">Agent Behavior</h3>
			<div class="p-4 bg-zinc-900 border border-zinc-800 rounded-xl space-y-4">
				<!-- Auto-Commit Toggle -->
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-white">Auto-Commit</div>
						<div class="text-xs text-zinc-500">
							Allow agent to commit changes without approval
						</div>
					</div>
					<button
						type="button"
						class={cn(
							'w-10 h-5 rounded-full relative transition-colors',
							autoCommit ? 'bg-teal-400' : 'bg-zinc-700 hover:bg-zinc-600'
						)}
						onclick={() => onautocommittoggle?.(!autoCommit)}
						role="switch"
						aria-checked={autoCommit}
						aria-label="Toggle auto-commit"
					>
						<div
							class={cn(
								'absolute top-1 w-3 h-3 bg-white rounded-full transition-all',
								autoCommit ? 'left-6' : 'left-1'
							)}
						></div>
					</button>
				</div>

				<!-- Budget Limit -->
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-white">Budget Limit</div>
						<div class="text-xs text-zinc-500">Max API spend per session</div>
					</div>
					<div class="text-sm text-white font-mono bg-zinc-800 px-2 py-1 rounded">
						{budgetLimit}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
