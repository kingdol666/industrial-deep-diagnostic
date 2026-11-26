import { lstatSync, realpathSync, readdirSync } from 'node:fs';
import { isAbsolute, join } from 'node:path';
import { stmts } from '../db/database.mjs';
import { PROJECT_ROOT, DATA_DIR } from '../engine/claude-client.mjs';
import { isInside } from '../utils/pathGuard.mjs';

const denied = () => Object.assign(new Error('产线作业输入必须来自当前作业所有者有权使用的数据目录'), {
  code: 'LINE_INPUT_UNAVAILABLE', status: 404,
});

export function authorizeBoundInputs(run) {
  if (!run.line_id || run.harness === 'mock') return;
  if (typeof run.data_path !== 'string') throw denied();
  let stated;
  try { stated = run.data_path.startsWith('[') ? JSON.parse(run.data_path) : [run.data_path]; } catch { throw denied(); }
  if (!Array.isArray(stated) || !stated.length || stated.length > 100) throw denied();
  const roots = stmts.getAllFolders.all().flatMap((folder) => {
    if (Number(folder.owner_user_id) !== Number(run.owner_user_id)) return [];
    try { return [realpathSync(folder.path)]; } catch { return []; }
  });
  let remaining = 10000;
  const verify = (path, root) => {
    if (--remaining < 0) throw denied();
    const stat = lstatSync(path);
    if (stat.isSymbolicLink() || !isInside(root, realpathSync(path))) throw denied();
    if (stat.isDirectory()) {
      for (const child of readdirSync(path)) verify(join(path, child), root);
    } else if (!stat.isFile()) throw denied();
  };
  const check = (file) => {
    if (typeof file !== 'string' || !file) throw denied();
    for (const candidate of isAbsolute(file) ? [file] : [join(PROJECT_ROOT, file), join(DATA_DIR, file)]) {
      let canonical;
      try { canonical = realpathSync(candidate); } catch (err) {
        if (err.code === 'ENOENT' || err.code === 'ENOTDIR') continue;
        throw denied();
      }
      const root = roots.find((dir) => isInside(dir, canonical));
      if (!root) throw denied();
      try { verify(candidate, root); } catch { throw denied(); }
      return canonical;
    }
    throw denied();
  };
  return stated.map(check);
}
