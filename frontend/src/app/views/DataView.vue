<template>
  <main class="shell page data-page">
    <section class="section-head">
      <p class="eyebrow">数据</p>
      <h1>数据视图</h1>
      <p>沉淀净值、收益、日历和导出相关的数据能力。</p>
    </section>

    <section class="panel content-panel">
      <h2>页面预留</h2>
      <p>这里会继续接入数据列表、图表或导入导出能力。当前标签已可直接跳转到本页面。</p>
    </section>
  </main>
</template>

<style scoped>
.data-page {
  display: grid;
  align-content: start;
  gap: 18px;
  padding-top: 142px;
}

.section-head {
  max-width: 720px;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 820;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: 34px;
  line-height: 1.12;
}

.section-head p,
.content-panel p {
  margin-top: 10px;
  max-width: 64ch;
  color: var(--muted);
}

.content-panel {
  padding: 22px;
}

.content-panel h2 {
  font-size: 18px;
}
</style>
