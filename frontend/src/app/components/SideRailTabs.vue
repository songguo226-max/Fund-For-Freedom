<script setup>
const tabs = [
  {
    label: '\u4fe1\u606f',
    to: '/information',
    ariaLabel: '\u8df3\u8f6c\u5230\u4fe1\u606f\u9875\u9762',
    tone: 'oklch(44% 0.12 255)',
    line: 'oklch(77% 0.072 249)',
  },
  {
    label: '\u6570\u636e',
    to: '/data',
    ariaLabel: '\u8df3\u8f6c\u5230\u6570\u636e\u9875\u9762',
    tone: 'oklch(49% 0.074 248)',
    line: 'oklch(74% 0.066 172)',
  },
  {
    label: '\u65b9\u6cd5\u8bba',
    to: '/methodology',
    ariaLabel: '\u8df3\u8f6c\u5230\u65b9\u6cd5\u8bba\u9875\u9762',
    tone: 'oklch(54% 0.052 244)',
    line: 'oklch(75% 0.09 35)',
  },
]
</script>

<template>
  <nav class="side-rail-tabs" aria-label="页面快捷导航">
    <RouterLink
      v-for="(tab, index) in tabs"
      :key="tab.to"
      class="rail-tab"
      active-class="is-active"
      :to="tab.to"
      :aria-label="tab.ariaLabel"
      :style="{ '--tab-index': index + 1, '--tab-tone': tab.tone, '--tab-line': tab.line }"
    >
      <span>{{ tab.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.side-rail-tabs {
  position: fixed;
  z-index: 60;
  top: 45%;
  left: 0;
  display: flex;
  flex-direction: column;
  transform: translateY(-50%);
  filter: drop-shadow(0 18px 28px rgba(47, 68, 92, 0.13));
}

.rail-tab {
  position: relative;
  display: grid;
  width: 30px;
  height: 132px;
  place-items: center;
  margin-top: -23px;
  color: oklch(96% 0.008 248);
  isolation: isolate;
  outline: none;
  text-decoration: none;
  z-index: var(--tab-index);
  transition:
    color 180ms cubic-bezier(0.19, 1, 0.22, 1),
    transform 180ms cubic-bezier(0.19, 1, 0.22, 1);
}

.rail-tab:first-child {
  margin-top: 0;
}

.rail-tab::before {
  position: absolute;
  inset: 0;
  z-index: -2;
  background:
    linear-gradient(
      180deg,
      var(--tab-line) 0%,
      color-mix(in oklch, var(--tab-line) 70%, var(--tab-tone)) 44%,
      color-mix(in oklch, var(--tab-line) 58%, oklch(96% 0.006 248)) 100%
    );
  clip-path: polygon(0 0, 100% 0, 100% 74%, 0 100%, 0 74%);
  content: "";
  transition:
    background 180ms cubic-bezier(0.19, 1, 0.22, 1),
    box-shadow 180ms cubic-bezier(0.19, 1, 0.22, 1);
}

.rail-tab::after {
  content: "";
  display: none;
}

.rail-tab span {
  position: absolute;
  top: 50%;
  left: 50%;
  display: block;
  width: 1em;
  text-align: center;
  writing-mode: vertical-rl;
  text-orientation: upright;
  letter-spacing: 0.24em;
  font-size: 14px;
  font-weight: 820;
  line-height: 1;
  transform: translate(-50%, calc(-50% - 13px));
}

.rail-tab:hover,
.rail-tab:focus-visible {
  z-index: 30;
  transform: translateY(-6px);
}

.rail-tab:hover::after,
.rail-tab:focus-visible::after,
.rail-tab.is-active::after {
  display: none;
}

.rail-tab.is-active {
  color: oklch(98% 0.006 248);
}

.rail-tab.is-active::before {
  background:
    linear-gradient(
      180deg,
      var(--tab-line) 0%,
      color-mix(in oklch, var(--tab-line) 76%, var(--tab-tone)) 48%,
      color-mix(in oklch, var(--tab-line) 64%, oklch(96% 0.006 248)) 100%
    );
  box-shadow:
    inset 0 1px 0 oklch(100% 0 0 / 0.18),
    0 10px 20px color-mix(in oklch, var(--tab-line) 18%, transparent);
}

.rail-tab:focus-visible::before {
  outline: 3px solid color-mix(in oklch, var(--tab-line) 30%, transparent);
  outline-offset: 3px;
}

@media (max-width: 760px) {
  .side-rail-tabs {
    top: 132px;
    transform: none;
  }

  .rail-tab {
    width: 29px;
    height: 112px;
    margin-top: -19px;
  }

  .rail-tab span {
    letter-spacing: 0.2em;
    font-size: 13px;
    transform: translate(-50%, calc(-50% - 9px));
  }

  .rail-tab::after {
    display: none;
  }

  :global(.page) {
    padding-left: 44px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .rail-tab,
  .rail-tab::after {
    transition: none;
  }
}
</style>
