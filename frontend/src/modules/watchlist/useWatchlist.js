import { computed, ref } from 'vue'

const FAVORITES_KEY = 'fund:favorites'
const RECENTS_KEY = 'fund:recents'
const MAX_RECENTS = 8

function read(key) {
  try {
    return JSON.parse(window.localStorage.getItem(key) || '[]')
  } catch {
    return []
  }
}

function write(key, value) {
  window.localStorage.setItem(key, JSON.stringify(value))
}

const favorites = ref(read(FAVORITES_KEY))
const recents = ref(read(RECENTS_KEY))

function normalize(item) {
  return {
    code: String(item.code),
    name: item.name || String(item.code),
    type: item.type || '',
  }
}

export function useWatchlist() {
  function addRecent(item) {
    const next = normalize(item)
    recents.value = [next, ...recents.value.filter((x) => x.code !== next.code)].slice(0, MAX_RECENTS)
    favorites.value = favorites.value.map((x) => (x.code === next.code ? normalize({ ...x, ...next }) : x))
    write(RECENTS_KEY, recents.value)
    write(FAVORITES_KEY, favorites.value)
  }

  function toggleFavorite(item) {
    const next = normalize(item)
    if (favorites.value.some((x) => x.code === next.code)) {
      favorites.value = favorites.value.filter((x) => x.code !== next.code)
    } else {
      favorites.value = [next, ...favorites.value]
    }
    write(FAVORITES_KEY, favorites.value)
  }

  function isFavorite(code) {
    return favorites.value.some((x) => x.code === String(code))
  }

  return {
    favorites: computed(() => favorites.value),
    recents: computed(() => recents.value),
    addRecent,
    toggleFavorite,
    isFavorite,
  }
}
