<script lang="ts">
	import { cn } from '$lib/utils';

	type MessageProps = {
		role: 'user' | 'assistant';
		content: string;
		timestamp?: Date;
	};

	let { role, content, timestamp }: MessageProps = $props();

	const isUser = $derived(role === 'user');
</script>

<div class={cn('flex gap-3 p-4', isUser && 'flex-row-reverse')}>
	<!-- Avatar -->
	<div
		class={cn(
			'flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-medium',
			isUser ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'
		)}
	>
		{isUser ? 'U' : 'C'}
	</div>

	<!-- Message content -->
	<div class={cn('flex max-w-[70%] flex-col gap-1', isUser && 'items-end')}>
		<div
			class={cn(
				'rounded-lg px-4 py-2',
				isUser ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-900'
			)}
		>
			<pre class="whitespace-pre-wrap font-sans text-sm">{content}</pre>
		</div>

		{#if timestamp}
			<span class="text-xs text-gray-500">
				{timestamp.toLocaleTimeString()}
			</span>
		{/if}
	</div>
</div>
