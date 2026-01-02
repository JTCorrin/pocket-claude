<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	type ChatInputProps = {
		onSendMessage: (message: string) => void;
		disabled?: boolean;
	};

	let { onSendMessage, disabled = false }: ChatInputProps = $props();

	let message = $state('');
	let textareaRef: HTMLTextAreaElement;

	function handleSubmit(e: Event) {
		e.preventDefault();
		if (!message.trim() || disabled) return;

		onSendMessage(message.trim());
		message = '';

		// Reset textarea height
		if (textareaRef) {
			textareaRef.style.height = 'auto';
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		// Send on Enter, but allow Shift+Enter for new lines
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit(e);
		}
	}

	function autoResize(e: Event) {
		const textarea = e.target as HTMLTextAreaElement;
		textarea.style.height = 'auto';
		textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
	}
</script>

<form onsubmit={handleSubmit} class="flex gap-2 border-t bg-white p-4">
	<div class="flex-1">
		<textarea
			bind:this={textareaRef}
			bind:value={message}
			oninput={autoResize}
			onkeydown={handleKeyDown}
			{disabled}
			placeholder="Type a message... (Enter to send, Shift+Enter for new line)"
			class="min-h-[44px] max-h-[200px] w-full resize-none rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
			rows="1"
		></textarea>
	</div>

	<Button type="submit" {disabled} class="self-end">Send</Button>
</form>
