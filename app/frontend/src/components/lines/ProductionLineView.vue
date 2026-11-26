<template>
  <div class="line-workspace">
    <aside class="work-panel line-register">
      <header class="panel-head">
        <div><p class="eyebrow">01 / {{ $t('lines.register') }}</p><h2>{{ $t('lines.lineList') }}</h2></div>
        <button class="btn btn-sm" type="button" :disabled="loading || creatingLine" @click="loadLines">{{ $t('common.refresh') }}</button>
      </header>
      <form class="line-form" @submit.prevent="createLine">
        <label>{{ $t('lines.name') }}<input v-model.trim="name" required maxlength="120" /></label>
        <button class="btn btn-primary" type="submit" :disabled="creatingLine || !name">{{ $t('lines.createLine') }}</button>
      </form>
      <p v-if="lineError" class="error" role="alert">{{ lineError }}</p>
      <p v-if="loading" role="status">{{ $t('common.loading') }}</p>
      <p v-else-if="!lineError && !lines.length">{{ $t('lines.emptyLines') }}</p>
      <ul class="line-list">
        <li v-for="line in lines" :key="line.line_id">
          <button type="button" :aria-pressed="lineId === line.line_id" :disabled="assetBusy" @click="selectLine(line.line_id)">
            <span><strong>{{ line.name }}</strong><small v-if="line.member_role">{{ $t(`lines.rights.${line.member_role}`) }}</small></span>
            <code>{{ line.line_id }}</code>
          </button>
        </li>
      </ul>
    </aside>

    <div class="workspace-body">
      <section v-if="selectedLine" class="work-panel" :aria-label="$t('lines.assetDesk')">
        <header class="panel-head">
          <div><p class="eyebrow">02 / {{ $t('lines.assetDesk') }}</p><h2>{{ selectedLine.name }}</h2><code>{{ selectedLine.line_id }}</code></div>
          <button v-if="selectedLine.member_role !== 'read'" type="button" class="btn btn-sm" :disabled="assetBusy"
            @click="$emit('prepare-run', selectedLine.line_id)">{{ $t('lines.prepareRun') }}</button>
        </header>
        <p v-if="!canManage">{{ $t('lines.manageRequired') }}</p>
        <template v-else>
          <details class="editor" open>
            <summary>{{ $t('lines.createDraft') }}</summary>
            <p>{{ $t('lines.draftBoundary') }}</p>
            <form @submit.prevent="createDraft">
              <fieldset :disabled="assetBusy">
                <div class="field-grid">
                  <label>{{ $t('lines.kind') }}<select v-model="draft.kind">
                    <option v-for="kind in kinds" :key="kind" :value="kind">{{ $t(`lines.kinds.${kind}`) }}</option>
                  </select></label>
                  <label>{{ $t('lines.title') }}<input v-model.trim="draft.title" required maxlength="120" /></label>
                </div>
                <label>{{ $t('lines.summary') }}<textarea v-model.trim="draft.summary" rows="2" required maxlength="240"></textarea></label>
                <template v-if="draft.kind === 'dataset'">
                  <label>{{ $t('lines.csv') }}<textarea v-model="draft.csv" rows="4" required spellcheck="false"></textarea></label>
                  <p>{{ $t('lines.fieldsHint') }}</p>
                  <div v-for="(field, idx) in draft.fields" :key="field.key" class="field-grid dataset-field">
                    <label>{{ $t('lines.fieldName') }}<input v-model.trim="field.name" required maxlength="120" /></label>
                    <label>{{ $t('lines.fieldDescription') }}<input v-model.trim="field.description" required maxlength="500" /></label>
                    <button v-if="draft.fields.length > 1" type="button" class="btn btn-sm" @click="draft.fields.splice(idx, 1)">{{ $t('lines.remove') }}</button>
                  </div>
                  <button type="button" class="btn btn-sm" :disabled="draft.fields.length >= 128" @click="draft.fields.push(newField())">{{ $t('lines.addField') }}</button>
                  <label>{{ $t('lines.useRestrictions') }}<textarea v-model.trim="draft.use_restrictions" rows="2" required maxlength="1000"></textarea></label>
                </template>
                <template v-else>
                  <label>{{ $t('lines.content') }}<textarea v-model.trim="draft.content" rows="4" required maxlength="1600"></textarea></label>
                  <label>{{ $t('lines.applicability') }}<textarea v-model.trim="draft.applicability" rows="2" maxlength="240"></textarea></label>
                </template>
                <button type="submit" class="btn btn-primary">{{ $t('lines.saveDraft') }}</button>
              </fieldset>
            </form>
          </details>

          <div class="version-desk">
            <h3>{{ $t('lines.manageVersions') }}</h3>
            <p>{{ $t('lines.manageHint') }}</p>
            <ul v-if="lineVersions.length" class="recent-versions">
              <li v-for="item in lineVersions" :key="keyFor(item)">
                <button type="button" class="btn btn-sm" :aria-pressed="activeVersion && keyFor(activeVersion) === keyFor(item)"
                  :disabled="assetBusy" @click="selectVersion(item)">
                  {{ item.title || item.asset_id }} · {{ $t('lines.version', { version: item.version }) }} · {{ $t(`lines.states.${item.state}`) }}
                </button>
              </li>
            </ul>
            <details class="editor">
              <summary>{{ $t('lines.manageById') }}</summary>
              <form class="field-grid manual" @submit.prevent="openManualVersion">
                <label>{{ $t('lines.assetId') }}<input v-model.trim="manual.asset_id" required maxlength="36" /></label>
                <label>{{ $t('lines.versionNumber') }}<input v-model="manual.version" type="number" required min="1" step="1" /></label>
                <label>{{ $t('lines.kind') }}<select v-model="manual.kind">
                  <option v-for="kind in kinds" :key="kind" :value="kind">{{ $t(`lines.kinds.${kind}`) }}</option>
                </select></label>
                <button class="btn btn-sm" type="submit" :disabled="assetBusy">{{ $t('lines.openVersion') }}</button>
              </form>
            </details>

            <section v-if="activeVersion" class="version-actions" :aria-label="$t('lines.manageVersions')">
              <div class="version-header">
                <strong>{{ activeVersion.title || $t(`lines.kinds.${activeVersion.kind}`) }} · {{ $t('lines.version', { version: activeVersion.version }) }} · {{ $t(`lines.states.${activeVersion.state}`) }}</strong>
                <code>{{ activeVersion.asset_id }}</code>
              </div>
              <form v-if="['draft', 'unknown'].includes(activeVersion.state)" @submit.prevent="publish">
                <fieldset :disabled="assetBusy">
                  <legend>{{ $t('lines.publish') }}</legend>
                  <label>{{ $t('lines.visibility') }}<select v-model="visibility">
                    <option value="private">{{ $t('lines.private') }}</option>
                    <option value="catalog">{{ $t('lines.catalogVisibility') }}</option>
                  </select></label>
                  <label v-if="visibility === 'catalog'" class="check"><input v-model="publicRead" type="checkbox" /> {{ $t('lines.publicRead') }}</label>
                  <label class="check"><input v-model="confirmed" type="checkbox" required /> {{ $t('lines.confirmRedaction') }}</label>
                  <button class="btn btn-primary" type="submit" :disabled="!confirmed">{{ $t('lines.publish') }}</button>
                </fieldset>
              </form>
              <template v-if="['published', 'unknown'].includes(activeVersion.state)">
                <form @submit.prevent="changeGrant(false)">
                  <fieldset :disabled="assetBusy">
                    <legend>{{ $t('lines.grants') }}</legend>
                    <p>{{ $t('lines.grantHint') }} <template v-if="userId">{{ $t('lines.ownUserId', { id: userId }) }}</template></p>
                    <label>{{ $t('lines.grantee') }}<input v-model="grantee" type="number" min="1" step="1" required /></label>
                    <div class="controls">
                      <label v-for="right in availableRights" :key="right" class="check">
                        <input v-model="rights" type="checkbox" :value="right" /> {{ $t(`lines.rights.${right}`) }}
                      </label>
                    </div>
                    <div class="controls">
                      <button type="submit" class="btn btn-sm" :disabled="!validGrantee || !rights.length">{{ $t('lines.saveGrant') }}</button>
                      <button type="button" class="btn btn-sm" :disabled="!validGrantee" @click="changeGrant(true)">{{ $t('lines.revokeGrant') }}</button>
                    </div>
                  </fieldset>
                </form>
                <form class="withdraw" @submit.prevent="withdraw">
                  <label class="check"><input v-model="withdrawConfirmed" type="checkbox" required :disabled="assetBusy" /> {{ $t('lines.withdrawHint') }}</label>
                  <button type="submit" class="btn btn-sm btn-danger" :disabled="assetBusy || !withdrawConfirmed">{{ $t('lines.withdraw') }}</button>
                </form>
              </template>
            </section>
            <p v-if="assetNotice" role="status">{{ assetNotice }}</p>
            <p v-if="assetError" class="error" role="alert">{{ assetError }}</p>
          </div>
        </template>
      </section>
      <KnowledgeReferencePicker :revision="catalogRevision" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { api } from '../../api/index.js';
import KnowledgeReferencePicker from './KnowledgeReferencePicker.vue';

const props = defineProps({ userId: [Number, String], initialLineId: String, versions: { type: Array, default: () => [] } });
const emit = defineEmits(['prepare-run', 'update:versions']);
const { t } = useI18n();
const kinds = ['experience', 'memory_excerpt', 'dataset'];
const lines = ref([]);
const lineId = ref(props.initialLineId || '');
const selectedLine = computed(() => lines.value.find((line) => line.line_id === lineId.value));
// An omitted membership role is not proof of permission; the server still checks every action.
const canManage = computed(() => !!selectedLine.value && !['read', 'run'].includes(selectedLine.value.member_role));
const name = ref('');
const loading = ref(false);
const creatingLine = ref(false);
const lineError = ref('');
const assetBusy = ref(false);
const assetError = ref('');
const assetNotice = ref('');
const catalogRevision = ref(0);
const activeVersion = ref(null);
const lineVersions = computed(() => props.versions.filter((item) => item.line_id === lineId.value));
const keyFor = (item) => `${item.asset_id}:${item.version}`;
let fieldSequence = 0;
const newField = () => ({ key: fieldSequence++, name: '', description: '' });
const newDraft = () => ({ kind: 'experience', title: '', summary: '', content: '', applicability: '', csv: '', fields: [newField()], use_restrictions: '' });
const draft = reactive(newDraft());
const manual = reactive({ asset_id: '', version: 1, kind: 'experience' });
const visibility = ref('private');
const confirmed = ref(false);
const publicRead = ref(false);
const withdrawConfirmed = ref(false);
const grantee = ref('');
const rights = ref([]);
const availableRights = computed(() => activeVersion.value?.kind === 'dataset' ? ['read', 'download', 'analyze'] : ['read', 'reuse']);
const validGrantee = computed(() => Number.isSafeInteger(Number(grantee.value)) && Number(grantee.value) > 0);

async function loadLines() {
  loading.value = true;
  lineError.value = '';
  try {
    const result = await api.listProductionLines();
    lines.value = Array.isArray(result) ? result : result.items ?? result.lines;
    if (!selectedLine.value) selectLine(lines.value[0]?.line_id || '');
  } catch {
    lineError.value = t('lines.loadLinesError');
  } finally {
    loading.value = false;
  }
}

async function createLine() {
  if (creatingLine.value || !name.value) return;
  creatingLine.value = true;
  lineError.value = '';
  try {
    const created = await api.createProductionLine({ name: name.value });
    name.value = '';
    lines.value = [...lines.value, created];
    selectLine(created.line_id);
    await loadLines();
  } catch (err) {
    lineError.value = errorText(err);
  } finally {
    creatingLine.value = false;
  }
}

function selectLine(id) {
  if (lineId.value === id) return;
  lineId.value = id;
  Object.assign(draft, newDraft());
  Object.assign(manual, { asset_id: '', version: 1, kind: 'experience' });
  selectVersion(null);
}

function selectVersion(item) {
  activeVersion.value = item;
  assetError.value = '';
  assetNotice.value = '';
  visibility.value = 'private';
  confirmed.value = false;
  publicRead.value = false;
  withdrawConfirmed.value = false;
  grantee.value = '';
  rights.value = [];
}

function openManualVersion() {
  const asset_id = manual.asset_id.toLowerCase();
  const version = Number(manual.version);
  if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(asset_id) || !Number.isSafeInteger(version) || version < 1) {
    assetError.value = t('lines.invalidRef');
    return;
  }
  selectVersion(lineVersions.value.find((item) => keyFor(item) === keyFor({ asset_id, version }))
    ?? { asset_id, version, kind: manual.kind, state: 'unknown' });
}

function updateVersion(item) {
  // No management-list API is available. Keep only server-issued receipts in this session.
  // A manually entered ID has no verified association to the currently displayed line.
  if (item.line_id) emit('update:versions', [item, ...props.versions.filter((v) => keyFor(v) !== keyFor(item))]);
  selectVersion(item);
}

function errorText(err) {
  if (err.code === 'KNOWLEDGE_GRANTEE_NOT_FOUND') return t('lines.granteeMissing');
  if (err.status === 403 || err.status === 404 || err.status === 401) return t('lines.actionUnavailable');
  return `${t('lines.actionError')}${err.status === 400 || err.status === 409 ? ` — ${err.message}` : ''}`;
}

async function act(fn, notice) {
  if (assetBusy.value) return;
  assetBusy.value = true;
  assetError.value = '';
  assetNotice.value = '';
  try {
    await fn();
    assetNotice.value = t(`lines.${notice}`);
  } catch (err) {
    assetError.value = errorText(err);
  } finally {
    assetBusy.value = false;
  }
}

function createDraft() {
  const { kind, title, summary, csv, fields, use_restrictions, content, applicability } = draft;
  const id = lineId.value;
  const body = kind === 'dataset' ? { kind, title, summary, csv, fields: fields.map(({ name, description }) => ({ name, description })), use_restrictions }
    : { kind, title, summary, content, applicability };
  return act(async () => {
    const result = await api.createKnowledgeAsset(id, body);
    Object.assign(draft, newDraft());
    updateVersion({ ...result, line_id: id });
  }, 'draftSaved');
}

function publish() {
  if (!confirmed.value) return;
  const target = activeVersion.value;
  return act(async () => {
    const result = await api.publishKnowledgeVersion(target, { confirmed: true, visibility: visibility.value, public_read: visibility.value === 'catalog' && publicRead.value });
    updateVersion({ ...target, ...result });
    catalogRevision.value++;
  }, 'published');
}

function withdraw() {
  if (!withdrawConfirmed.value) return;
  const target = activeVersion.value;
  return act(async () => {
    updateVersion({ ...target, ...await api.withdrawKnowledgeVersion(target) });
    catalogRevision.value++;
  }, 'withdrawn');
}

function changeGrant(revoke) {
  if (!validGrantee.value || (!revoke && !rights.value.length)) return;
  const target = activeVersion.value;
  const id = Number(grantee.value);
  return act(async () => {
    if (revoke) await api.revokeKnowledgeGrant(target, id);
    else await api.setKnowledgeGrant(target, id, rights.value);
    catalogRevision.value++;
  }, revoke ? 'grantRevoked' : 'grantSaved');
}

onMounted(loadLines);
</script>

<style scoped>
.line-workspace { display: grid; grid-template-columns: minmax(14rem, .8fr) minmax(0, 2fr); gap: 1rem; align-items: start; }
.workspace-body, .work-panel, .version-desk, .version-actions { display: grid; gap: .8rem; min-width: 0; }
.work-panel { padding: 1rem; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface); }
.panel-head, .controls, .withdraw { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .5rem; }
.work-panel :is(h2, h3, p, ul) { margin: 0; }
.work-panel p { color: var(--text2); font-size: .85rem; }
.panel-head .eyebrow { color: var(--accent); letter-spacing: .08em; font: .72rem var(--font-mono); }
.panel-head h2 { margin-top: .3rem; overflow-wrap: anywhere; }
.line-list, .recent-versions { list-style: none; padding: 0; display: grid; gap: .4rem; }
.line-list button { display: grid; gap: .32rem; width: 100%; padding: .65rem; text-align: start; color: var(--text); background: var(--surface-soft); border: 1px solid var(--border); border-radius: 5px; cursor: pointer; }
.line-list button > span { display: flex; flex-wrap: wrap; justify-content: space-between; gap: .3rem; overflow-wrap: anywhere; }
[aria-pressed='true'] { border-color: var(--border-accent) !important; background: var(--accent-soft) !important; }
code, small { color: var(--text2); font: .75rem var(--font-mono); overflow-wrap: anywhere; }
.line-form, fieldset, label { display: grid; gap: .45rem; min-width: 0; }
fieldset { margin: 0; padding: 0; border: 0; }
legend { padding: 0 0 .4rem; font-weight: 600; }
label { font-size: .85rem; }
label :is(input:not([type='checkbox']), select, textarea) { width: 100%; min-width: 0; color: var(--text); background: var(--surface-soft); border: 1px solid var(--border-strong); border-radius: 5px; padding: .45rem .55rem; font: inherit; }
textarea { resize: vertical; }
.field-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 10rem), 1fr)); gap: .5rem; align-items: end; }
.dataset-field { grid-template-columns: repeat(auto-fit, minmax(min(100%, 9rem), 1fr)); }
.controls { justify-content: flex-start; }
.check { display: flex; align-items: baseline; gap: .4rem; }
.work-panel .btn { justify-self: start; }
.editor { border-top: 1px solid var(--border-strong); padding-block: .6rem; }
.editor summary { cursor: pointer; font-weight: 600; }
.editor > :not(summary) { margin-top: .6rem; }
.version-actions { padding: .75rem; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface-muted); }
.version-header { display: grid; gap: .3rem; overflow-wrap: anywhere; }
.version-actions form { border-top: 1px solid var(--border-strong); padding-top: .65rem; }
.recent-versions button { white-space: normal; overflow-wrap: anywhere; text-align: start; }
.work-panel .error { color: var(--red); }
@media (max-width: 840px) { .line-workspace { grid-template-columns: minmax(0, 1fr); } }
</style>
