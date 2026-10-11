// Live demo step 4: register → login → submit real diagnosis task → poll
const BASE = 'http://127.0.0.1:3210';
const j = (r) => r.json();

const reg = await fetch(BASE + '/api/auth/register', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'live_demo_1005', password: 'Demo-1005-Live!', email: 'demo1005@example.com' }),
}).then(j).catch((e) => ({ error: String(e) }));
console.log('register:', JSON.stringify(reg).slice(0, 120));

const login = await fetch(BASE + '/api/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'live_demo_1005', password: 'Demo-1005-Live!' }),
}).then(j);
const tok = login?.data?.session_token || login?.data?.token || login?.token;
console.log('login:', tok ? 'OK (Bearer ' + String(tok).slice(0, 18) + '...)' : 'FAIL ' + JSON.stringify(login).slice(0, 160));

const t = await fetch(BASE + '/api/diagnosis/tasks', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok },
  body: JSON.stringify({
    folderPath: 'D:/codes/industrial-deep-diagnostic/data/paper_machine_headbox',
    harness: 'omp', language: 'zh',
  }),
}).then(j);
console.log('task:', JSON.stringify(t).slice(0, 240));
const taskId = t?.data?.task_id;
if (!taskId) process.exit(1);

// poll a few times to show live progression
for (let i = 0; i < 6; i++) {
  await new Promise((r) => setTimeout(r, 20000));
  const v = await fetch(BASE + '/api/diagnosis/tasks/' + taskId, {
    headers: { Authorization: 'Bearer ' + tok },
  }).then(j).catch(() => null);
  const d = v?.data || {};
  console.log(`poll ${i + 1}: status=${d.status} stage=${d.stage || d.current_step || '-'} progress=${d.progress ?? '-'}`);
}
console.log('TASK_ID=' + taskId);
