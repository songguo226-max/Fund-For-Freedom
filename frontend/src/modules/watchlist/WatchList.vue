<script setup>
import { ChevronRight, Clock3, Star } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

defineProps({
  favorites: { type: Array, default: () => [] },
  recents: { type: Array, default: () => [] },
})

const router = useRouter()

function open(code) {
  router.push(`/fund/${encodeURIComponent(code)}`)
}

function displayName(item) {
  return item.name && item.name !== item.code ? item.name : `基金 ${item.code}`
}

function displayType(item) {
  return item.type || '基金'
}
</script>

<template>
  <section class="watch-grid">
    <div class="panel list">
      <header><span class="icon-mark"><Star /></span><h2>自选</h2></header>
      <button v-for="item in favorites" :key="item.code" class="row" type="button" @click="open(item.code)">
        <span class="fund-id">
          <strong>{{ displayName(item) }}</strong>
          <small>{{ item.code }}</small>
        </span>
        <span class="row-meta">
          <span class="fund-type">{{ displayType(item) }}</span>
          <ChevronRight class="row-cue" />
        </span>
      </button>
      <p v-if="!favorites.length" class="empty">收藏后会显示在这里</p>
    </div>
    <div class="panel list">
      <header><span class="icon-mark"><Clock3 /></span><h2>最近查看</h2></header>
      <button v-for="item in recents" :key="item.code" class="row" type="button" @click="open(item.code)">
        <span class="fund-id">
          <strong>{{ displayName(item) }}</strong>
          <small>{{ item.code }}</small>
        </span>
        <span class="row-meta">
          <span class="fund-type">{{ displayType(item) }}</span>
          <ChevronRight class="row-cue" />
        </span>
      </button>
      <p v-if="!recents.length" class="empty">打开基金详情后会记录最近查看</p>
    </div>
  </section>
</template>

<style scoped>
.watch-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.list {
  min-height: 220px;
  padding: 16px;
}
header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.icon-mark {
  display: inline-grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-soft);
  color: var(--accent);
}
.icon-mark svg {
  width: 16px;
  height: 16px;
  stroke-width: 1.9;
}
h2 {
  margin: 0;
  font-size: 15px;
}
.row {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 11px 2px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  color: var(--text);
  text-align: left;
}
.row:hover strong {
  color: var(--accent);
}
.row:hover .row-cue {
  color: var(--accent);
  transform: translateX(2px);
}
.fund-id {
  min-width: 0;
}
.row strong,
.row small {
  display: block;
}
.row strong {
  overflow: hidden;
  font-size: 14px;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row small {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.15;
}
.fund-type {
  flex: 0 0 auto;
  max-width: 112px;
  overflow: hidden;
  padding: 4px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row-meta {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
}
.row-cue {
  width: 16px;
  height: 16px;
  color: var(--muted-2);
  stroke-width: 1.9;
  transition: color 160ms ease-out, transform 160ms ease-out;
}
.row:hover .fund-type {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
}
.empty {
  margin: 18px 0 0;
  color: var(--muted);
  font-size: 13px;
}
@media (max-width: 780px) {
  .watch-grid {
    grid-template-columns: 1fr;
  }
}
</style>
