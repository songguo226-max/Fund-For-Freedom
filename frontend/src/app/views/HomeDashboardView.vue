<script setup>
import FundSearch from '../../modules/fund-search/FundSearch.vue'
import WatchList from '../../modules/watchlist/WatchList.vue'
import { useWatchlist } from '../../modules/watchlist/useWatchlist'

const { favorites, recents } = useWatchlist()
</script>

<template>
  <main class="shell page home">
    <FundSearch />
    <WatchList :favorites="favorites" :recents="recents" />
  </main>
</template>

<style scoped>
.home {
  display: grid;
  align-content: start;
  gap: 22px;
  padding-top: 142px;
}
</style>
