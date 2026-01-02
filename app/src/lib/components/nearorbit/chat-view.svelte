<script lang="ts">
	import { cn } from '$lib/utils.js';
	import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';
	import ArrowUpIcon from '@lucide/svelte/icons/arrow-up';
	import OctagonIcon from '@lucide/svelte/icons/octagon';
	import FileCodeIcon from '@lucide/svelte/icons/file-code';
	import { Button } from '$lib/components/ui/button/index.js';
	import ChatMessage from './chat-message.svelte';
	import type { ChatMessage as ChatMessageType, Mission, ContextFile } from './types.js';

	interface Props {
		/** Current mission being viewed */
		mission?: Mission;
		/** Messages in the chat */
		messages?: ChatMessageType[];
		/** Context files attached to the chat */
		contextFiles?: ContextFile[];
		/** Current input value */
		inputValue?: string;
		/** Whether the agent is currently running */
		isAgentRunning?: boolean;
		/** Handler for going back to dashboard */
		onback?: () => void;
		/** Handler for sending a message */
		onsend?: (message: string) => void;
		/** Handler for stopping the agent */
		onstop?: () => void;
		/** Handler for input changes */
		oninput?: (value: string) => void;
		/** Additional CSS classes */
		class?: string;
	}

	let {
		mission,
		messages = [],
		contextFiles = [],
		inputValue = '',
		isAgentRunning = false,
		onback,
		onsend,
		onstop,
		oninput,
		class: className
	}: Props = $props();

	let textareaRef: HTMLTextAreaElement | null = $state(null);

	/**
	 * Handle form submission
	 */
	function handleSubmit(e: Event) {
		e.preventDefault();
		if (inputValue.trim()) {
			onsend?.(inputValue);
		}
	}

	/**
	 * Handle textarea keydown for Enter to submit
	 */
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit(e);
		}
	}

	/**
	 * Get status indicator for breadcrumb
	 */
	const statusIndicator = $derived(() => {
		if (!mission) return null;
		switch (mission.status) {
			case 'active':
				return { color: 'bg-green-500', label: 'Running', animate: true };
			case 'paused':
				return { color: 'bg-yellow-500', label: 'Paused', animate: false };
			default:
				return null;
		}
	});
</script>

<div class={cn('flex flex-col flex-1 h-full bg-[#09090b]', className)}>
	<!-- Breadcrumb Navigation -->
	<div class="h-10 bg-zinc-800/30 border-b border-zinc-800 flex items-center px-4 gap-2 text-xs shrink-0">
		<button
			type="button"
			class="text-zinc-400 hover:text-white flex items-center gap-1 transition-colors"
			onclick={onback}
		>
			<ArrowLeftIcon class="w-3 h-3" />
			Back
		</button>
		<span class="text-zinc-600">/</span>
		<span class="text-teal-400 truncate">{mission?.title || 'Mission'}</span>
		{#if statusIndicator()}
			{@const status = statusIndicator()}
			<span class="ml-auto flex items-center gap-2 text-zinc-500">
				<span
					class={cn('w-1.5 h-1.5 rounded-full', status?.color, status?.animate && 'animate-pulse')}
				></span>
				{status?.label}
			</span>
		{/if}
	</div>

	<!-- Chat Scroll Area -->
	<div class="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
		{#each messages as message (message.id)}
			<ChatMessage {message} />
		{/each}

		<!-- Bottom spacer for input area -->
		<div class="h-24"></div>
	</div>

	<!-- Input Area -->
	<div class="p-4 border-t border-zinc-800 bg-[#09090b]/95 backdrop-blur shrink-0 relative">
		<div class="max-w-4xl mx-auto relative">
			<!-- Context Pills -->
			{#if contextFiles.length > 0}
				<div class="absolute -top-10 left-0 flex gap-2 flex-wrap">
					{#each contextFiles as file (file.path)}
						<div
							class="bg-zinc-900 border border-zinc-800 text-xs text-zinc-400 px-2 py-1 rounded-md flex items-center gap-1"
						>
							<FileCodeIcon class="w-3 h-3" />
							{file.name}
						</div>
					{/each}
				</div>
			{/if}

			<!-- Input Form -->
			<form onsubmit={handleSubmit}>
				<div
					class="relative bg-zinc-900 border border-zinc-800 rounded-xl shadow-lg focus-within:ring-1 focus-within:ring-teal-400/50 transition-all"
				>
					<textarea
						bind:this={textareaRef}
						placeholder="Reply to agent or give new command..."
						class="w-full bg-transparent text-white placeholder-zinc-600 px-4 py-3 pr-12 rounded-xl focus:outline-none resize-none h-12 max-h-32"
						value={inputValue}
						oninput={(e) => oninput?.(e.currentTarget.value)}
						onkeydown={handleKeydown}
					></textarea>
					<Button
						type="submit"
						size="icon-sm"
						class="absolute right-2 bottom-2 bg-teal-400 text-zinc-900 hover:bg-teal-300"
						disabled={!inputValue.trim()}
					>
						<ArrowUpIcon class="w-5 h-5" />
					</Button>
				</div>
			</form>

			<!-- Stop Agent Button -->
			{#if isAgentRunning}
				<div class="text-center mt-2">
					<button
						type="button"
						class="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 mx-auto transition-colors"
						onclick={onstop}
					>
						<OctagonIcon class="w-3 h-3" />
						Stop Agent
					</button>
				</div>
			{/if}
		</div>
	</div>
</div>
