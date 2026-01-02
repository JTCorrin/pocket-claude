<script lang="ts">
	import { cn } from '$lib/utils.js';
	import UserIcon from '@lucide/svelte/icons/user';
	import BrainCircuitIcon from '@lucide/svelte/icons/brain-circuit';
	import TerminalSquareIcon from '@lucide/svelte/icons/terminal-square';
	import TerminalBlock from './terminal-block.svelte';
	import type { ChatMessage } from './types.js';

	interface Props {
		/** The message data to display */
		message: ChatMessage;
		/** Additional CSS classes */
		class?: string;
	}

	let { message, class: className }: Props = $props();

	const isUser = $derived(message.type === 'user');
	const hasTerminal = $derived(!!message.terminal);
	const hasThought = $derived(!!message.thought);
</script>

<div class={cn('flex gap-4 max-w-4xl mx-auto', className)}>
	<!-- Avatar -->
	<div
		class={cn(
			'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
			isUser
				? 'bg-zinc-800 border border-zinc-700'
				: 'bg-teal-400/10 border border-teal-400/20'
		)}
	>
		{#if isUser}
			<UserIcon class="w-4 h-4 text-zinc-400" />
		{:else if hasTerminal && message.isLive}
			<TerminalSquareIcon class="w-4 h-4 text-teal-400" />
		{:else}
			<BrainCircuitIcon class="w-4 h-4 text-teal-400" />
		{/if}
	</div>

	<!-- Content -->
	<div class="space-y-2 w-full min-w-0">
		<!-- Sender Name -->
		<div class={cn('text-sm font-medium', isUser ? 'text-white' : 'text-teal-400')}>
			{isUser ? 'User' : 'Near Orbit Agent'}
		</div>

		<!-- Thought Process (Agent only) -->
		{#if hasThought && !isUser}
			<div class="text-sm text-zinc-500 italic border-l-2 border-zinc-800 pl-3 py-1">
				{message.thought}
			</div>
		{/if}

		<!-- Terminal Block (Agent only) -->
		{#if hasTerminal && message.terminal}
			<TerminalBlock
				lines={message.terminal.lines}
				title={message.terminal.title}
				cwd={message.terminal.cwd}
				isActive={message.terminal.isActive || message.isLive}
				class="mt-2"
			/>
		{/if}

		<!-- Message Content -->
		{#if message.content}
			<div class={cn('leading-relaxed', isUser ? 'text-zinc-300' : 'text-zinc-300 pt-1')}>
				<!-- Support for inline code blocks -->
				{@html message.content.replace(
					/<code>(.*?)<\/code>/g,
					'<code class="bg-zinc-800 px-1.5 py-0.5 rounded text-sm font-mono text-teal-400">$1</code>'
				)}
			</div>
		{/if}
	</div>
</div>
