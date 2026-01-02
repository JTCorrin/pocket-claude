<script lang="ts">
	import { cn } from '$lib/utils.js';
	import type { TerminalLine } from './types.js';

	interface Props {
		/** Terminal lines to display */
		lines: TerminalLine[];
		/** Optional title for the terminal header */
		title?: string;
		/** Current working directory to display */
		cwd?: string;
		/** Whether the terminal is currently active/running */
		isActive?: boolean;
		/** Additional CSS classes */
		class?: string;
	}

	let { lines, title = 'Terminal', cwd, isActive = false, class: className }: Props = $props();

	/**
	 * Get the appropriate color class for a terminal line type
	 */
	function getLineColor(type: TerminalLine['type']): string {
		switch (type) {
			case 'command':
				return 'text-zinc-300';
			case 'output':
				return 'text-zinc-400';
			case 'success':
				return 'text-green-400';
			case 'error':
				return 'text-red-400';
			case 'info':
				return 'text-zinc-500';
			default:
				return 'text-zinc-400';
		}
	}
</script>

<div
	class={cn(
		'rounded-lg border border-zinc-800 bg-[#0d0d0f] overflow-hidden font-mono text-sm',
		isActive && 'shadow-lg shadow-teal-400/5',
		className
	)}
>
	<!-- Terminal Header -->
	<div
		class="px-3 py-1.5 bg-white/5 border-b border-white/5 flex items-center justify-between"
	>
		<span class="text-xs text-zinc-500">
			{title}{isActive ? ' - Active' : ''}
		</span>
		{#if cwd}
			<span class="text-xs text-zinc-600">{cwd}</span>
		{/if}
		{#if isActive}
			<div class="flex gap-1.5">
				<span class="w-2 h-2 rounded-full bg-red-500/50"></span>
				<span class="w-2 h-2 rounded-full bg-yellow-500/50"></span>
				<span class="w-2 h-2 rounded-full bg-green-500/50"></span>
			</div>
		{/if}
	</div>

	<!-- Terminal Content -->
	<div class="p-3 space-y-1 overflow-x-auto">
		{#each lines as line, index (index)}
			<div class={cn('flex gap-2', getLineColor(line.type))}>
				{#if line.type === 'command'}
					<span class="text-teal-400 shrink-0">-></span>
				{/if}
				<span class={line.type === 'command' && isActive && index === lines.length - 1 ? 'typing-cursor' : ''}>
					{line.content}
				</span>
			</div>
		{/each}
	</div>
</div>

<style>
	.typing-cursor::after {
		content: '\25CB';
		animation: blink 1s step-end infinite;
		color: #2dd4bf;
	}

	@keyframes blink {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0;
		}
	}
</style>
