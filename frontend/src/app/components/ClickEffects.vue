<script setup lang="ts">
import { gsap } from 'gsap'
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

type ClickEffect = {
  id: string
  x: number
  y: number
}

const color = '#52A270'
const duration = 0.3
const effectSize = 90
const rotation = 0
const strokeWidth = 2
const maxEffects = 24
const sniperAngles = [0, 90, 180, 270]
const particleAngles = [
  Math.PI / 3,
  (2 * Math.PI) / 3,
  (4 * Math.PI) / 3,
  (5 * Math.PI) / 3,
  Math.PI / 6,
  (5 * Math.PI) / 6,
  (7 * Math.PI) / 6,
  (11 * Math.PI) / 6,
]

const containerRef = ref<HTMLDivElement | null>(null)
const effects = ref<ClickEffect[]>([])
const cleanupTimers = new Map<string, number>()

function handleClick(event: MouseEvent) {
  if (event.button !== 0) return

  const container = containerRef.value
  if (!container) return

  const rect = container.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const id = `${event.timeStamp}-${Math.round(x)}-${Math.round(y)}`

  effects.value = [...effects.value.slice(-(maxEffects - 1)), { id, x, y }]
  void nextTick(() => animateSniper(id))

  const timer = window.setTimeout(() => removeEffect(id), duration * 1000 + 120)
  cleanupTimers.set(id, timer)
}

function removeEffect(id: string) {
  const timer = cleanupTimers.get(id)
  if (timer) window.clearTimeout(timer)
  cleanupTimers.delete(id)
  effects.value = effects.value.filter((effect) => effect.id !== id)
}

function animateSniper(id: string) {
  const root = containerRef.value?.querySelector<HTMLElement>(`[data-effect-id="${CSS.escape(id)}"]`)
  if (!root) return

  const lines = root.querySelectorAll<SVGLineElement>('[data-sniper-line]')
  lines.forEach((line, index) => {
    const angle = sniperAngles[index] * (Math.PI / 180)
    const centerX = effectSize / 2
    const centerY = effectSize / 2
    const lineLength = effectSize * 0.2
    const startX = centerX + 5 * Math.cos(angle)
    const startY = centerY - 5 * Math.sin(angle)
    const endX = centerX + (5 + lineLength) * Math.cos(angle)
    const endY = centerY - (5 + lineLength) * Math.sin(angle)

    gsap.set(line, {
      attr: {
        x1: startX,
        y1: startY,
        x2: endX,
        y2: endY,
      },
      strokeWidth,
    })

    gsap
      .timeline()
      .to(line, {
        attr: {
          x1: endX,
          y1: endY,
          x2: endX,
          y2: endY,
        },
        translateX: (5 + lineLength) * Math.cos(angle),
        translateY: -(5 + lineLength) * Math.sin(angle),
        duration,
        ease: 'power2.out',
      })
      .to(
        line,
        {
          strokeWidth: 0,
          duration: duration * 0.4,
          ease: 'linear',
        },
        duration * 0.6,
      )
  })

  const particles = root.querySelectorAll<HTMLElement>('[data-sniper-particle]')
  particles.forEach((particle, index) => {
    const angle = particleAngles[index]

    gsap.set(particle, {
      x: 0,
      y: 0,
      width: strokeWidth,
      height: strokeWidth,
    })

    gsap
      .timeline()
      .to(particle, {
        x: Math.cos(angle) * (effectSize * 0.4),
        y: Math.sin(angle) * (effectSize * 0.4),
        duration,
        ease: 'power2.out',
      })
      .to(
        particle,
        {
          width: 0,
          height: 0,
          duration: duration * 0.4,
          ease: 'linear',
        },
        duration * 0.6,
      )
  })
}

onMounted(() => {
  document.addEventListener('click', handleClick, { passive: true })
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClick)
  cleanupTimers.forEach((timer) => window.clearTimeout(timer))
  cleanupTimers.clear()
  if (containerRef.value) {
    gsap.killTweensOf(containerRef.value.querySelectorAll('*'))
  }
})
</script>

<template>
  <div ref="containerRef" class="click-effects" aria-hidden="true">
    <div
      v-for="effect in effects"
      :key="effect.id"
      class="click-effects__sniper"
      :data-effect-id="effect.id"
      :style="{
        '--x': `${effect.x}px`,
        '--y': `${effect.y}px`,
        '--size': `${effectSize}px`,
        '--color': color,
        '--rotation': `${rotation}deg`,
        '--stroke-width': `${strokeWidth}px`,
      }"
    >
      <svg class="click-effects__svg" :width="effectSize" :height="effectSize" viewBox="0 0 90 90">
        <line
          v-for="angle in sniperAngles"
          :key="angle"
          data-sniper-line
          x1="45"
          y1="45"
          x2="45"
          y2="45"
          :stroke="color"
          :stroke-width="strokeWidth"
          stroke-linecap="square"
        />
      </svg>

      <span
        v-for="angle in particleAngles"
        :key="angle"
        data-sniper-particle
        class="click-effects__particle"
      ></span>
    </div>
  </div>
</template>

<style scoped>
.click-effects {
  position: fixed;
  inset: 0;
  z-index: 2147483647;
  overflow: visible;
  pointer-events: none;
}

.click-effects__sniper {
  position: absolute;
  left: var(--x);
  top: var(--y);
  width: var(--size);
  height: var(--size);
  transform: translate(-50%, -50%) rotate(var(--rotation));
  transform-origin: center;
  pointer-events: none;
}

.click-effects__svg {
  position: absolute;
  inset: 0;
  overflow: visible;
  pointer-events: none;
}

.click-effects__svg line {
  vector-effect: non-scaling-stroke;
}

.click-effects__particle {
  position: absolute;
  left: calc(50% - var(--stroke-width) / 2);
  top: calc(50% - var(--stroke-width) / 2);
  width: var(--stroke-width);
  height: var(--stroke-width);
  background: var(--color);
  pointer-events: none;
  transform-origin: center;
}
</style>
