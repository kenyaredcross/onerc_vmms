import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

export function useScreenSize() {
	const size = reactive({
		width: window.innerWidth,
		height: window.innerHeight,
	})

	const isMobile = computed(() => size.width < 640)

	const onResize = () => {
		size.width = window.innerWidth
		size.height = window.innerHeight
	}

	onMounted(() => {
		window.addEventListener('resize', onResize)
	})

	onUnmounted(() => {
		window.removeEventListener('resize', onResize)
	})

	return {
		size,
		isMobile,
	}
}
