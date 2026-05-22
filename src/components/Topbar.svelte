<script>
	import { onMount } from 'svelte';
	import { fade } from 'svelte/transition';
	import { page } from '$app/stores';
	import InputForm from '~/components/InputForm.svelte';
	import { ga } from '~/utils/event';
	import Sampling from '~/components/Sampling.svelte';

	export let isActive;

	// Check if current page is about page
	$: isAboutPage = $page.url.pathname === '/about';
</script>

<div class="top-bar flex w-full items-center gap-4 px-10 py-2 pb-3" class:active={isActive}>
	<div class="logo text-bold text-gray-700" data-click="logo">
		SW T<span class="small">RANSFORMER</span> E<span class="small">XPLAINER</span>
	</div>
	<div class="inputs flex grow items-center">
		<div class="input-wrapper w-full" class:active={isActive}>
			{#if !isAboutPage}
				<InputForm />
			{/if}
		</div>
	</div>
</div>

<style lang="scss">
	.top-bar {
		background: linear-gradient(to bottom, rgba(255, 255, 255, 1) 60%, rgba(255, 255, 255, 0) 100%);
		.input-wrapper {
			&.active {
				opacity: 1;
				pointer-events: initial;
			}
			opacity: 0;
			transition: opacity 0.2s;
			pointer-events: none;
		}
		.logo {
			flex-shrink: 0;
			white-space: nowrap;
			font-family: 'Jersey 10', sans-serif;

			font-optical-sizing: auto;
			font-style: normal;

			font-size: 2rem;
			// color: theme('colors.blue.800');

			background: linear-gradient(
				to right,
				#012e57 0%,
				#0063fc 100%
			);
			-webkit-background-clip: text;
			-webkit-text-fill-color: transparent;

			.small {
				font-size: 1.8rem;
			}
		}
		.icons {
			flex-shrink: 0;
			svg {
				fill: theme('colors.gray.600');
			}
		}
	}
</style>
