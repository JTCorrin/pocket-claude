<script lang="ts">
	import type { Session } from '$lib/api/endpoints/claude';
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { cn } from '$lib/utils';

	type SessionSelectorProps = {
		sessions: Session[];
		selectedSession: Session | null;
		onSelectSession: (session: Session | null) => void;
		loading?: boolean;
	};

	let { sessions, selectedSession, onSelectSession, loading = false }: SessionSelectorProps =
		$props();

	function formatDate(dateStr: string) {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return 'Just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;
		return date.toLocaleDateString();
	}
</script>

<Card class="h-full">
	<CardHeader>
		<CardTitle class="flex items-center justify-between">
			<span>Sessions</span>
			<Button size="sm" variant="outline" onclick={() => onSelectSession(null)}>
				New Chat
			</Button>
		</CardTitle>
	</CardHeader>
	<CardContent class="p-2">
		{#if loading}
			<div class="flex items-center justify-center p-8">
				<div class="text-sm text-gray-500">Loading sessions...</div>
			</div>
		{:else if sessions.length === 0}
			<div class="flex items-center justify-center p-8">
				<div class="text-sm text-gray-500">No sessions found</div>
			</div>
		{:else}
			<div class="space-y-2">
				{#each sessions as session (session.session_id)}
					<button
						onclick={() => onSelectSession(session)}
						class={cn(
							'w-full rounded-lg p-3 text-left transition-colors hover:bg-gray-100',
							selectedSession?.session_id === session.session_id && 'bg-blue-50 hover:bg-blue-100'
						)}
					>
						<div class="mb-1 flex items-start justify-between">
							<span class="text-sm font-medium text-gray-900">{session.project}</span>
							<span class="text-xs text-gray-500">{formatDate(session.last_active)}</span>
						</div>
						<p class="line-clamp-2 text-xs text-gray-600">{session.preview}</p>
						<div class="mt-1 text-xs text-gray-400">{session.message_count} messages</div>
					</button>
				{/each}
			</div>
		{/if}
	</CardContent>
</Card>
