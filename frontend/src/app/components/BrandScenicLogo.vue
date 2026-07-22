<script setup>
const homeLabel = '\u56de\u5230\u9996\u9875'
const logoAlt = '\u57fa\u91d1\u4e4b\u8def'
const logoSrc = '/brand/fund-road-logo.png'
</script>

<template>
  <RouterLink class="brand-logo" to="/" :aria-label="homeLabel">
    <img class="brand-image" :src="logoSrc" :alt="logoAlt" decoding="async" draggable="false" />
  </RouterLink>
</template>

<style scoped>
.brand-logo {
  position: absolute;
  z-index: 50;
  top: 14px;
  left: 18px;
  display: flex;
  width: 238px;
  height: 76px;
  align-items: center;
  text-decoration: none;
  transition:
    transform 170ms cubic-bezier(0.19, 1, 0.22, 1),
    filter 170ms cubic-bezier(0.19, 1, 0.22, 1);
}

.brand-logo:hover,
.brand-logo:focus-visible {
  outline: none;
  transform: translateY(-1px);
  filter: drop-shadow(0 12px 18px oklch(58% 0.055 248 / 0.12));
}

.brand-logo:focus-visible {
  box-shadow: none;
}

.brand-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  user-select: none;
}

@media (max-width: 760px) {
  .brand-logo {
    top: 10px;
    left: 40px;
    width: 190px;
    height: 62px;
  }
}
</style>
