<template>
  <main class="shell page methodology-page">
    <section class="section-head">
      <p class="eyebrow">方法论</p>
      <h1>分析方法论</h1>
      <p>说明收益计算、数据口径和分析判断的基础规则。</p>
    </section>

    <section class="panel content-panel">
      <h2>页面预留</h2>
      <p>这里会沉淀指标定义、计算逻辑和数据来源说明。左侧标签会保持固定，方便跨页面切换。</p>
    </section>
  </main>
</template>

<style scoped>
.methodology-page {
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
