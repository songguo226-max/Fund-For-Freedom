<script setup>
import FundSearch from '../../modules/fund-search/FundSearch.vue'
import WatchList from '../../modules/watchlist/WatchList.vue'
import { useWatchlist } from '../../modules/watchlist/useWatchlist'

const { favorites, recents } = useWatchlist()
</script>

<template>
  <main class="shell page home">
    <section class="intro">
      <h1>基金查询</h1>
      <p>收益日历、月度表现、净值走势集中查看。</p>
    </section>
    <FundSearch />
    <WatchList :favorites="favorites" :recents="recents" />
  </main>
</template>

<style scoped>
.home {
  display: grid;
  align-content: start;
  gap: 22px;
  padding-top: 52px;
}
.intro {
  max-width: 720px;
}
h1 {
  margin: 0;
  font-size: 38px;
  line-height: 1.1;
}
p {
  margin: 10px 0 0;
  color: var(--muted);
}
</style>
