<script lang="ts">
	import { cn } from '$lib/utils.js';
	import GithubIcon from '@lucide/svelte/icons/github';
	import GitlabIcon from '@lucide/svelte/icons/gitlab';
	import GitBranchIcon from '@lucide/svelte/icons/git-branch';
	import CheckIcon from '@lucide/svelte/icons/check';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import type { Integration, IntegrationProvider, IntegrationStatus } from './types.js';

	interface Props {
		/** The integration data to display */
		integration: Integration;
		/** Handler for connect/disconnect action */
		onaction?: (provider: IntegrationProvider, action: 'connect' | 'disconnect' | 'save') => void;
		/** Handler for input changes (for configuring integrations) */
		oninputchange?: (provider: IntegrationProvider, field: string, value: string) => void;
		/** Instance URL value for configuring providers like Gitea */
		instanceUrl?: string;
		/** Access token value for configuring providers */
		accessToken?: string;
		/** Additional CSS classes */
		class?: string;
	}

	let {
		integration,
		onaction,
		oninputchange,
		instanceUrl = '',
		accessToken = '',
		class: className
	}: Props = $props();

	/**
	 * Get the icon component for a provider
	 */
	function getProviderIcon(provider: IntegrationProvider) {
		switch (provider) {
			case 'github':
				return GithubIcon;
			case 'gitlab':
				return GitlabIcon;
			case 'gitea':
				return GitBranchIcon;
		}
	}

	/**
	 * Get the icon color class for a provider
	 */
	function getProviderIconClass(provider: IntegrationProvider): string {
		switch (provider) {
			case 'github':
				return 'text-white';
			case 'gitlab':
				return 'text-orange-500';
			case 'gitea':
				return 'text-green-500';
		}
	}

	const ProviderIcon = $derived(getProviderIcon(integration.provider));
	const iconClass = $derived(getProviderIconClass(integration.provider));
	const isConfiguring = $derived(integration.status === 'configuring');
	const isConnected = $derived(integration.status === 'connected');
</script>

<div class={cn('p-4 bg-zinc-900 border border-zinc-800 rounded-xl', className)}>
	<!-- Header Row -->
	<div
		class={cn(
			'flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between',
			isConfiguring && 'mb-4'
		)}
	>
		<div class="flex items-center gap-4">
			<!-- Provider Icon -->
			<div class="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center">
				<ProviderIcon class={cn('w-5 h-5', iconClass)} />
			</div>

			<!-- Provider Info -->
			<div>
				<div class="text-sm font-medium text-white">{integration.name}</div>
				{#if isConnected && integration.username}
					<div class="text-xs text-green-400 flex items-center gap-1">
						<CheckIcon class="w-3 h-3" />
						Connected as @{integration.username}
					</div>
				{:else if isConfiguring}
					<div class="text-xs text-zinc-500">Self-hosted instance</div>
				{:else}
					<div class="text-xs text-zinc-500">Not connected</div>
				{/if}
			</div>
		</div>

		<!-- Action Button or Status Badge -->
		{#if isConfiguring}
			<div class="px-2 py-0.5 rounded bg-zinc-800 text-[10px] text-zinc-400 border border-zinc-700">
				CONFIGURING
			</div>
		{:else if isConnected}
			<Button
				variant="outline"
				size="sm"
				class="text-xs border-zinc-700 text-zinc-400 hover:bg-zinc-800 hover:text-white"
				onclick={() => onaction?.(integration.provider, 'disconnect')}
			>
				Re-authenticate
			</Button>
		{:else}
			<Button
				variant="secondary"
				size="sm"
				class="text-xs bg-zinc-800 text-white hover:bg-zinc-700"
				onclick={() => onaction?.(integration.provider, 'connect')}
			>
				Connect
			</Button>
		{/if}
	</div>

	<!-- Configuration Form (for self-hosted providers) -->
	{#if isConfiguring}
		<div class="space-y-3 pl-0 sm:pl-14">
			<div>
				<label for="{integration.provider}-url" class="block text-xs text-zinc-500 mb-1">
					Instance URL
				</label>
				<Input
					id="{integration.provider}-url"
					type="text"
					value={instanceUrl}
					placeholder="https://git.example.com"
					class="w-full bg-[#09090b] border-zinc-800 text-white focus:border-teal-400"
					oninput={(e) => oninputchange?.(integration.provider, 'instanceUrl', e.currentTarget.value)}
				/>
			</div>
			<div>
				<label for="{integration.provider}-token" class="block text-xs text-zinc-500 mb-1">
					Personal Access Token
				</label>
				<Input
					id="{integration.provider}-token"
					type="password"
					value={accessToken}
					placeholder="Enter your access token"
					class="w-full bg-[#09090b] border-zinc-800 text-white focus:border-teal-400"
					oninput={(e) => oninputchange?.(integration.provider, 'accessToken', e.currentTarget.value)}
				/>
			</div>
			<div class="flex justify-end pt-2">
				<Button
					class="bg-white text-black hover:bg-zinc-200"
					onclick={() => onaction?.(integration.provider, 'save')}
				>
					Save & Connect
				</Button>
			</div>
		</div>
	{/if}
</div>
