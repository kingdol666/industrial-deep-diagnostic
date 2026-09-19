// E2E UI driver for the IDD web console — imported by test cells.
// The Browser bootstrap must run inline in each cell (plugin bridge checks
// the entry context); this module only supplies the driver logic.
// Usage (in a cell, after inline bootstrap):
//   const tab = <validated tab>;
//   const D = (await import('file:///D:/codes/myskills/industrial-deep-diagnostic/paper/workbench/ui-driver.mjs')).makeDriver(tab);

export function makeDriver(tab) {
  const uiClick = async (expr) => tab.playwright.evaluate(`(() => { ${expr} })()`);
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  const navTab = async (key) => uiClick(`
    const b=[...document.querySelectorAll('.app-nav-item')].find(x=>x.textContent.includes('${key}'));
    if(!b) throw new Error('nav not found: ${key}'); b.click(); 'ok';`);

  const selectEngine = async (engineName) => {
    await uiClick(`document.querySelector('.app-engine-current').click(); 'open';`);
    await sleep(300);
    const r = await uiClick(`
      const rows=[...document.querySelectorAll('.app-engine-menu .app-engine-row')];
      const row=rows.find(x=>x.querySelector('.app-engine-row-name')?.textContent.trim()==='${engineName}');
      if(!row) throw new Error('engine row not found: ${engineName}');
      if(row.disabled) throw new Error('engine disabled: ${engineName}');
      row.click(); 'selected';`);
    await sleep(300);
    await uiClick(`const m=document.querySelector('.app-engine-menu'); if(m) document.querySelector('.app-engine-current').click(); 'closed';`);
    return r;
  };

  const goHome = async () => {
    await navTab('Data');
    await sleep(400);
    await uiClick(`const b=document.querySelector('.breadcrumb-root'); if(b) b.click(); 'home';`);
    await sleep(600);
  };

  const pickFile = async (folder, file) => {
    await goHome();
    if (folder) {
      await uiClick(`
        const rows=[...document.querySelectorAll('.ip-row.manifest-cols')];
        const row=rows.find(x=>x.querySelector('.name-text')?.textContent.trim()==='${folder}');
        if(!row) throw new Error('folder not found: ${folder}');
        row.dispatchEvent(new MouseEvent('dblclick', { bubbles: true })); 'in';`);
      await sleep(800);
    }
    return uiClick(`
      const rows=[...document.querySelectorAll('.ip-row.manifest-cols')];
      const row=rows.find(x=>x.querySelector('.name-text')?.textContent.trim()==='${file}');
      if(!row) throw new Error('file not found: ${file}');
      row.querySelector('.cell-actions button').click(); 'picked';`);
  };

  const setTurns = async (v) => uiClick(`
    const sel=document.querySelector('.ctrl-select');
    if(!sel) return 'no-select';
    const opt=[...sel.options].find(o=>o.value==='${v}');
    if(opt){ sel.value=opt.value; sel.dispatchEvent(new Event('change',{bubbles:true})); }
    return 'turns='+sel.value;`);

  const startDiagnosis = async (scene, question, { turns } = {}) => {
    await navTab('Diagnose');
    await sleep(400);
    await uiClick(`const b=document.querySelector('.dv-nav button'); if(b) b.click(); 'ok';`);
    await sleep(400);
    if (turns) await setTurns(turns);
    await tab.playwright.evaluate(`(() => {
      const si = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      const st = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      const s1 = document.querySelector('.ctrl-input'); const s2 = document.querySelector('.ctrl-textarea');
      si.call(s1, '${scene}'); s1.dispatchEvent(new Event('input', { bubbles: true }));
      st.call(s2, '${question}'); s2.dispatchEvent(new Event('input', { bubbles: true }));
      return 'filled';
    })()`);
    await sleep(200);
    return uiClick(`
      const btn=document.querySelector('.ctrl-btn-go');
      if(!btn || btn.disabled) throw new Error('start unavailable');
      btn.click(); 'started';`);
  };

  const listRuns = async () => tab.playwright.evaluate(`(async () => {
    const token = localStorage.getItem('auth_token') || '';
    const r = await fetch('/api/diagnosis/list', { headers: { Authorization: 'Bearer ' + token }, cache: 'no-store' });
    const j = await r.json();
    const d = j.data; const arr = Array.isArray(d) ? d : (d.runs || []);
    return arr.map(x => ({ scene: x.scene_name, id: x.run_id, status: x.engineStatus || x.status, verdict: x.judge_verdict || null, score: x.score ?? null }));
  })()`);

  const pollRounds = async (prefixes, maxMs = 60000) => {
    const t0 = Date.now();
    let snap = [];
    while (Date.now() - t0 < maxMs) {
      snap = (await listRuns()).filter(x => prefixes.some(p => (x.scene || '').startsWith(p)));
      const unfinished = snap.filter(s => !['completed', 'failed', 'stopped'].includes(String(s.status).toLowerCase()));
      if (unfinished.length === 0) return snap;
      await sleep(4000);
    }
    return snap;
  };

  return { uiClick, sleep, navTab, selectEngine, goHome, pickFile, setTurns, startDiagnosis, listRuns, pollRounds };
}
