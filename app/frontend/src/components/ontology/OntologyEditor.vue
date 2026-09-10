<template>
  <div class="onto-editor">
    <div class="onto-editor-rail">
      <button
        v-for="s in sections"
        :key="s.key"
        type="button"
        class="onto-editor-rail-btn"
        :class="{ active: section === s.key }"
        @click="section = s.key"
      >
        <span class="onto-editor-rail-icon">{{ s.icon }}</span>
        <span class="onto-editor-rail-label">{{ $t(s.label) }}</span>
        <span class="onto-editor-rail-count">{{ countFor(s.key) }}</span>
      </button>
    </div>

    <div class="onto-editor-pane">
      <!-- ── 场景 ── -->
      <template v-if="section === 'scene'">
        <div class="onto-field-grid">
          <label class="onto-field">
            <span>{{ $t('ontology.editor.sceneName') }}</span>
            <input :value="scene.name" @input="setScene('name', $event.target.value)" />
          </label>
          <label class="onto-field">
            <span>{{ $t('ontology.editor.processType') }}</span>
            <input :value="scene.process_type" @input="setScene('process_type', $event.target.value)" />
          </label>
          <label class="onto-field wide">
            <span>{{ $t('ontology.editor.productionGoal') }}</span>
            <input :value="scene.production_goal" @input="setScene('production_goal', $event.target.value)" />
          </label>
        </div>

        <div class="onto-list-block">
          <div class="onto-list-head">
            <h4>{{ $t('ontology.editor.objectives') }}</h4>
            <button type="button" class="onto-mini-btn" @click="addObjective">+</button>
          </div>
          <div v-for="(o, i) in scene.objectives || []" :key="`obj-${i}`" class="onto-row">
            <input
              class="grow" :value="o"
              @input="setIndexed('scene', 'objectives', i, $event.target.value)"
            />
            <button type="button" class="onto-icon-btn" :title="$t('ontology.editor.remove')" @click="removeIndexed('scene', 'objectives', i)">✕</button>
          </div>
              <p v-if="!(scene.objectives || []).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
        </div>
      </template>

      <!-- ── 设备 ── -->
      <template v-else-if="section === 'equipment'">
        <div class="onto-list-head">
          <h4>{{ $t('ontology.editor.equipment') }}</h4>
          <button type="button" class="onto-mini-btn" @click="addItem('scene.equipment', newEquipment())">
            + {{ $t('ontology.editor.addEquipment') }}
          </button>
        </div>
        <div v-for="(eq, i) in scene.equipment || []" :key="`eq-${i}`" class="onto-card">
          <div class="onto-card-head">
            <span class="onto-card-title">{{ eq.name || eq.id || `#${i + 1}` }}</span>
            <span class="onto-card-actions">
              <button type="button" class="onto-icon-btn" :title="$t('ontology.editor.moveUp')" @click="move('scene.equipment', i, -1)">↑</button>
              <button type="button" class="onto-icon-btn" :title="$t('ontology.editor.moveDown')" @click="move('scene.equipment', i, 1)">↓</button>
              <button type="button" class="onto-icon-btn danger" :title="$t('ontology.editor.remove')" @click="removeItem('scene.equipment', i, eq.name)">✕</button>
            </span>
          </div>
          <div class="onto-field-grid">
            <label class="onto-field"><span>{{ $t('ontology.editor.equipId') }}</span>
              <input :value="eq.id" @input="setItem('scene.equipment', i, 'id', $event.target.value)" /></label>
            <label class="onto-field"><span>name</span>
              <input :value="eq.name" @input="setItem('scene.equipment', i, 'name', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.equipType') }}</span>
              <input :value="eq.type" @input="setItem('scene.equipment', i, 'type', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.equipFunction') }}</span>
              <input :value="eq.function" @input="setItem('scene.equipment', i, 'function', $event.target.value)" /></label>
          </div>
        </div>
        <p v-if="!(scene.equipment || []).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>

      <!-- ── 阶段 ── -->
      <template v-else-if="section === 'stages'">
        <div class="onto-list-head">
          <h4>{{ $t('ontology.editor.stages') }}</h4>
          <button type="button" class="onto-mini-btn" @click="addItem('scene.stages', newStage())">
            + {{ $t('ontology.editor.addStage') }}
          </button>
        </div>
        <div v-for="(st, i) in scene.stages || []" :key="`st-${i}`" class="onto-card">
          <div class="onto-card-head">
            <span class="onto-card-title">#{{ st.sequence ?? i }} · {{ st.name || st.id || '' }}</span>
            <span class="onto-card-actions">
              <button type="button" class="onto-icon-btn" @click="move('scene.stages', i, -1)">↑</button>
              <button type="button" class="onto-icon-btn" @click="move('scene.stages', i, 1)">↓</button>
              <button type="button" class="onto-icon-btn danger" @click="removeItem('scene.stages', i, st.name)">✕</button>
            </span>
          </div>
          <div class="onto-field-grid">
            <label class="onto-field"><span>{{ $t('ontology.editor.stageId') }}</span>
              <input :value="st.id" @input="setItem('scene.stages', i, 'id', $event.target.value)" /></label>
            <label class="onto-field"><span>name</span>
              <input :value="st.name" @input="setItem('scene.stages', i, 'name', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.stageSeq') }}</span>
              <input type="number" :value="st.sequence" @input="setItem('scene.stages', i, 'sequence', Number($event.target.value))" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.stagePhysics') }}</span>
              <input :value="st.key_physics" @input="setItem('scene.stages', i, 'key_physics', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.parameters') }}</span>
              <input :value="(st.key_parameters || []).join(', ')" @input="setItem('scene.stages', i, 'key_parameters', splitList($event.target.value))" /></label>
          </div>
        </div>
        <p v-if="!(scene.stages || []).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>

      <!-- ── 信号 ── -->
      <template v-else-if="section === 'signals'">
        <div class="onto-list-head">
          <h4>
            {{ $t('ontology.editor.signals') }}
            <span class="onto-count-badge">{{ signalRows.length }}</span>
          </h4>
          <span class="onto-head-actions">
            <select v-model="signalFilter" class="onto-select">
              <option value="all">{{ $t('ontology.showAll') }}</option>
              <option v-for="b in buckets" :key="b.key" :value="b.key">{{ b.label }} ({{ bucketCount(b.key) }})</option>
            </select>
            <button type="button" class="onto-mini-btn" @click="addSignal">{{ $t('ontology.editor.addSignal') }}</button>
          </span>
        </div>
        <div v-for="row in signalRows" :key="`${row.bucket}-${row.index}`" class="onto-card signal">
          <div class="onto-card-head">
            <span class="onto-card-title mono">{{ row.sig.column || row.sig.name || '(unnamed)' }}</span>
            <span class="onto-badge-row">
              <span class="onto-badge" :class="bucketClass(row.bucket)">{{ bucketLabel(row.bucket) }}</span>
              <span class="onto-badge role">{{ row.sig.role || '—' }}</span>
              <span class="onto-badge" :class="`conf-${(row.sig.physical_meaning_confidence || 'UNKNOWN').toLowerCase()}`">
                {{ row.sig.physical_meaning_confidence || 'UNKNOWN' }}
              </span>
              <span v-if="row.sig.behavior_match" class="onto-badge" :class="`bhv-${row.sig.behavior_match.toLowerCase()}`">
                {{ row.sig.behavior_match }}
              </span>
            </span>
            <span class="onto-card-actions">
              <button type="button" class="onto-icon-btn" @click="move(`signals.${row.bucket}`, row.index, -1)">↑</button>
              <button type="button" class="onto-icon-btn" @click="move(`signals.${row.bucket}`, row.index, 1)">↓</button>
              <button type="button" class="onto-icon-btn danger" @click="removeItem(`signals.${row.bucket}`, row.index, row.sig.column)">✕</button>
            </span>
          </div>

          <div class="onto-field-grid">
            <label class="onto-field"><span>{{ $t('ontology.editor.column') }}</span>
              <input class="mono" :value="row.sig.column" @input="setItem(`signals.${row.bucket}`, row.index, 'column', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.displayName') }}</span>
              <input :value="row.sig.display_name" @input="setItem(`signals.${row.bucket}`, row.index, 'display_name', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.unit') }}</span>
              <input :value="row.sig.unit" @input="setItem(`signals.${row.bucket}`, row.index, 'unit', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.role') }}</span>
              <select :value="row.sig.role" @change="setItem(`signals.${row.bucket}`, row.index, 'role', $event.target.value)">
                <option v-for="r in roles" :key="r" :value="r">{{ r }}</option>
              </select></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.physicalMeaning') }}</span>
              <textarea rows="2" :value="row.sig.physical_meaning" @input="setItem(`signals.${row.bucket}`, row.index, 'physical_meaning', $event.target.value)"></textarea></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.confidence') }}</span>
              <select :value="row.sig.physical_meaning_confidence" @change="setItem(`signals.${row.bucket}`, row.index, 'physical_meaning_confidence', $event.target.value)">
                <option value="">—</option>
                <option v-for="c in confidences" :key="c" :value="c">{{ c }}</option>
              </select></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.knowledgeSource') }}</span>
              <select :value="row.sig.knowledge_source" @change="setItem(`signals.${row.bucket}`, row.index, 'knowledge_source', $event.target.value)">
                <option value="">—</option>
                <option v-for="k in knowledgeSources" :key="k" :value="k">{{ k }}</option>
              </select></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.inferenceBasis') }}</span>
              <input :value="row.sig.inference_basis" @input="setItem(`signals.${row.bucket}`, row.index, 'inference_basis', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.behaviorMatch') }}</span>
              <select :value="row.sig.behavior_match" @change="setItem(`signals.${row.bucket}`, row.index, 'behavior_match', $event.target.value)">
                <option value="">—</option>
                <option v-for="b in behaviorMatches" :key="b" :value="b">{{ b }}</option>
              </select></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.normalRange') }} ({{ $t('ontology.editor.min') }})</span>
              <input type="number" :value="rangeOf(row.sig)[0]" @input="setRange(`signals.${row.bucket}`, row.index, 0, $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.normalRange') }} ({{ $t('ontology.editor.max') }})</span>
              <input type="number" :value="rangeOf(row.sig)[1]" @input="setRange(`signals.${row.bucket}`, row.index, 1, $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.stageRef') }}</span>
              <input class="mono" :value="row.sig.stage_ref" list="onto-stage-ids" @input="setItem(`signals.${row.bucket}`, row.index, 'stage_ref', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.equipmentRef') }}</span>
              <input class="mono" :value="row.sig.equipment_ref" list="onto-equipment-ids" @input="setItem(`signals.${row.bucket}`, row.index, 'equipment_ref', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.governingLaw') }}</span>
              <input :value="row.sig.governing_law" @input="setItem(`signals.${row.bucket}`, row.index, 'governing_law', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.expectedBehavior') }}</span>
              <input :value="row.sig.expected_data_behavior" @input="setItem(`signals.${row.bucket}`, row.index, 'expected_data_behavior', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.observedBehavior') }}</span>
              <input :value="row.sig.observed_data_behavior" @input="setItem(`signals.${row.bucket}`, row.index, 'observed_data_behavior', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.discrepancySignal') }}</span>
              <input :value="row.sig.discrepancy_signal" @input="setItem(`signals.${row.bucket}`, row.index, 'discrepancy_signal', $event.target.value)" /></label>
          </div>
        </div>
        <p v-if="!signalRows.length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>

      <!-- ── 关系 ── -->
      <template v-else-if="section === 'relationships'">
        <div class="onto-list-head">
          <h4>{{ $t('ontology.editor.relationships') }} <span class="onto-count-badge">{{ (ontology.relationships || []).length }}</span></h4>
          <button type="button" class="onto-mini-btn" @click="addItem('relationships', newRelationship())">
            + {{ $t('ontology.editor.addRelationship') }}
          </button>
        </div>
        <div v-for="(r, i) in ontology.relationships || []" :key="`rel-${i}`" class="onto-card">
          <div class="onto-card-head">
            <span class="onto-card-title mono">{{ r.from || '?' }} → {{ r.to || '?' }}</span>
            <span class="onto-badge-row">
              <span class="onto-badge" :class="`rel-${r.type || 'unspecified'}`">{{ r.type || '—' }}</span>
              <span class="onto-badge">{{ r.strength || '—' }}</span>
              <span v-if="r.inferred" class="onto-badge inferred">{{ $t('ontology.editor.inferred') }}</span>
            </span>
            <span class="onto-card-actions">
              <button type="button" class="onto-icon-btn danger" @click="removeItem('relationships', i, `${r.from}→${r.to}`)">✕</button>
            </span>
          </div>
          <div class="onto-field-grid">
            <label class="onto-field"><span>{{ $t('ontology.editor.from') }}</span>
              <input class="mono" :value="r.from" list="onto-columns" @input="setItem('relationships', i, 'from', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.to') }}</span>
              <input class="mono" :value="r.to" list="onto-columns" @input="setItem('relationships', i, 'to', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.relType') }}</span>
              <select :value="r.type" @change="setItem('relationships', i, 'type', $event.target.value)">
                <option v-for="t in relTypes" :key="t" :value="t">{{ t }}</option>
              </select></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.strength') }}</span>
              <select :value="r.strength" @change="setItem('relationships', i, 'strength', $event.target.value)">
                <option value="">—</option>
                <option v-for="s in strengths" :key="s" :value="s">{{ s }}</option>
              </select></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.mechanism') }}</span>
              <textarea rows="2" :value="r.mechanism" @input="setItem('relationships', i, 'mechanism', $event.target.value)"></textarea></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.equation') }}</span>
              <input class="mono" :value="r.governing_equation" @input="setItem('relationships', i, 'governing_equation', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.functionalForm') }}</span>
              <select :value="r.predicted_functional_form" @change="setItem('relationships', i, 'predicted_functional_form', $event.target.value)">
                <option value="">—</option>
                <option v-for="f in functionalForms" :key="f" :value="f">{{ f }}</option>
              </select></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.timeLag') }}</span>
              <input :value="r.time_lag" @input="setItem('relationships', i, 'time_lag', $event.target.value)" /></label>
            <label class="onto-field checkbox">
              <input type="checkbox" :checked="!!r.inferred" @change="setItem('relationships', i, 'inferred', $event.target.checked)" />
              <span>{{ $t('ontology.editor.inferred') }}</span>
            </label>
          </div>
        </div>
        <p v-if="!(ontology.relationships || []).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>

      <!-- ── 混杂因子 ── -->
      <template v-else-if="section === 'confounders'">
        <div class="onto-list-head">
          <h4>{{ $t('ontology.editor.confounders') }}</h4>
          <button type="button" class="onto-mini-btn" @click="addItem('confounders', { variable: '', why: '', controlled: false })">
            + {{ $t('ontology.editor.addConfounder') }}
          </button>
        </div>
        <div v-for="(c, i) in ontology.confounders || []" :key="`cf-${i}`" class="onto-card">
          <div class="onto-card-head">
            <span class="onto-card-title">{{ c.variable || `#${i + 1}` }}</span>
            <span class="onto-card-actions">
              <button type="button" class="onto-icon-btn danger" @click="removeItem('confounders', i, c.variable)">✕</button>
            </span>
          </div>
          <div class="onto-field-grid">
            <label class="onto-field"><span>{{ $t('ontology.editor.confVariable') }}</span>
              <input :value="c.variable" @input="setItem('confounders', i, 'variable', $event.target.value)" /></label>
            <label class="onto-field checkbox">
              <input type="checkbox" :checked="c.controlled === true" @change="setItem('confounders', i, 'controlled', $event.target.checked)" />
              <span>{{ $t('ontology.editor.confControlled') }}</span>
            </label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.confWhy') }}</span>
              <textarea rows="2" :value="c.why" @input="setItem('confounders', i, 'why', $event.target.value)"></textarea></label>
          </div>
        </div>
        <p v-if="!(ontology.confounders || []).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>

      <!-- ── 参数组 ── -->
      <template v-else-if="section === 'groups'">
        <div class="onto-list-head">
          <h4>{{ $t('ontology.editor.groups') }}</h4>
          <span class="onto-head-actions">
            <input v-model="newGroupName" class="onto-input-inline" placeholder="group_name" />
            <button type="button" class="onto-mini-btn" @click="addGroup">+</button>
          </span>
        </div>
        <div v-for="(members, gname) in ontology.parameter_groups || {}" :key="`grp-${gname}`" class="onto-card">
          <div class="onto-card-head">
            <span class="onto-card-title mono">{{ gname }}</span>
            <span class="onto-card-actions">
              <button type="button" class="onto-icon-btn danger" @click="removeGroup(gname)">✕</button>
            </span>
          </div>
          <label class="onto-field wide"><span>{{ $t('ontology.editor.groupMembers') }}</span>
            <input class="mono" :value="(members || []).join(', ')"
              @input="setGroupMembers(gname, splitList($event.target.value))" /></label>
        </div>
        <p v-if="!Object.keys(ontology.parameter_groups || {}).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>

      <!-- ── 物理原理 ── -->
      <template v-else-if="section === 'principles'">
        <div class="onto-list-head">
          <h4>{{ $t('ontology.editor.principles') }}</h4>
          <button type="button" class="onto-mini-btn" @click="addItem('physical_principles', { principle: '', equation: '', parameters: [], direction: '' })">
            + {{ $t('ontology.editor.addPrinciple') }}
          </button>
        </div>
        <div v-for="(p, i) in ontology.physical_principles || []" :key="`pp-${i}`" class="onto-card">
          <div class="onto-card-head">
            <span class="onto-card-title">{{ p.principle || `#${i + 1}` }}</span>
            <span class="onto-card-actions">
              <button type="button" class="onto-icon-btn danger" @click="removeItem('physical_principles', i, p.principle)">✕</button>
            </span>
          </div>
          <div class="onto-field-grid">
            <label class="onto-field wide"><span>{{ $t('ontology.editor.principleName') }}</span>
              <input :value="p.principle" @input="setItem('physical_principles', i, 'principle', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.equation') }}</span>
              <input class="mono" :value="p.equation" @input="setItem('physical_principles', i, 'equation', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.parameters') }}</span>
              <input class="mono" :value="(p.parameters || []).join(', ')" @input="setItem('physical_principles', i, 'parameters', splitList($event.target.value))" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.direction') }}</span>
              <input :value="p.direction" @input="setItem('physical_principles', i, 'direction', $event.target.value)" /></label>
          </div>
        </div>
        <p v-if="!(ontology.physical_principles || []).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>

      <!-- ── 失效模式 ── -->
      <template v-else-if="section === 'failures'">
        <div class="onto-list-head">
          <h4>{{ $t('ontology.editor.failureModes') }}</h4>
          <button type="button" class="onto-mini-btn" @click="addItem('known_failure_modes', { mode: '', signature: '', relevance: '', source: '' })">
            + {{ $t('ontology.editor.addFailureMode') }}
          </button>
        </div>
        <div v-for="(m, i) in ontology.known_failure_modes || []" :key="`fm-${i}`" class="onto-card">
          <div class="onto-card-head">
            <span class="onto-card-title">{{ m.mode || `#${i + 1}` }}</span>
            <span class="onto-card-actions">
              <button type="button" class="onto-icon-btn danger" @click="removeItem('known_failure_modes', i, m.mode)">✕</button>
            </span>
          </div>
          <div class="onto-field-grid">
            <label class="onto-field wide"><span>{{ $t('ontology.editor.failureMode') }}</span>
              <input :value="m.mode" @input="setItem('known_failure_modes', i, 'mode', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.signature') }}</span>
              <textarea rows="2" :value="m.signature" @input="setItem('known_failure_modes', i, 'signature', $event.target.value)"></textarea></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.relevance') }}</span>
              <textarea rows="2" :value="m.relevance" @input="setItem('known_failure_modes', i, 'relevance', $event.target.value)"></textarea></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.source') }}</span>
              <input :value="m.source" @input="setItem('known_failure_modes', i, 'source', $event.target.value)" /></label>
          </div>
        </div>
        <p v-if="!(ontology.known_failure_modes || []).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>

      <!-- ── 差异信号 ── -->
      <template v-else-if="section === 'discrepancies'">
        <div class="onto-list-head">
          <h4>{{ $t('ontology.editor.discrepancies') }}</h4>
          <button type="button" class="onto-mini-btn" @click="addItem('discrepancy_signals', newDiscrepancy())">
            + {{ $t('ontology.editor.addDiscrepancy') }}
          </button>
        </div>
        <div v-for="(d, i) in ontology.discrepancy_signals || []" :key="`ds-${i}`" class="onto-card">
          <div class="onto-card-head">
            <span class="onto-card-title">{{ d.id || `#${i + 1}` }} · {{ d.type || '' }}</span>
            <span class="onto-badge-row">
              <span v-if="d.severity" class="onto-badge" :class="`sev-${String(d.severity).toLowerCase()}`">{{ d.severity }}</span>
            </span>
            <span class="onto-card-actions">
              <button type="button" class="onto-icon-btn danger" @click="removeItem('discrepancy_signals', i, d.id)">✕</button>
            </span>
          </div>
          <div class="onto-field-grid">
            <label class="onto-field"><span>{{ $t('ontology.editor.dsId') }}</span>
              <input :value="d.id" @input="setItem('discrepancy_signals', i, 'id', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.dsType') }}</span>
              <input :value="d.type" @input="setItem('discrepancy_signals', i, 'type', $event.target.value)" /></label>
            <label class="onto-field"><span>{{ $t('ontology.editor.dsSeverity') }}</span>
              <select :value="d.severity" @change="setItem('discrepancy_signals', i, 'severity', $event.target.value)">
                <option value="">—</option>
                <option v-for="s in severities" :key="s" :value="s">{{ s }}</option>
              </select></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.dsColumns') }}</span>
              <input class="mono" :value="(d.columns || []).join(', ')" @input="setItem('discrepancy_signals', i, 'columns', splitList($event.target.value))" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.dsExpectation') }}</span>
              <input :value="d.ontology_expectation" @input="setItem('discrepancy_signals', i, 'ontology_expectation', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.dsObservation') }}</span>
              <input :value="d.data_observation" @input="setItem('discrepancy_signals', i, 'data_observation', $event.target.value)" /></label>
            <label class="onto-field wide"><span>{{ $t('ontology.editor.dsMeaning') }}</span>
              <textarea rows="2" :value="d.diagnostic_meaning" @input="setItem('discrepancy_signals', i, 'diagnostic_meaning', $event.target.value)"></textarea></label>
          </div>
        </div>
        <p v-if="!(ontology.discrepancy_signals || []).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>

      <!-- ── 元数据 ── -->
      <template v-else-if="section === 'metadata'">
        <div class="onto-field-grid">
          <label class="onto-field"><span>{{ $t('ontology.editor.samplingRate') }}</span>
            <input :value="meta.sampling_rate" @input="setMeta('sampling_rate', $event.target.value)" /></label>
          <label class="onto-field"><span>{{ $t('ontology.editor.timezone') }}</span>
            <input :value="meta.timezone" @input="setMeta('timezone', $event.target.value)" /></label>
          <label class="onto-field"><span>{{ $t('ontology.editor.startTime') }}</span>
            <input :value="meta.start_time" @input="setMeta('start_time', $event.target.value)" /></label>
          <label class="onto-field"><span>{{ $t('ontology.editor.endTime') }}</span>
            <input :value="meta.end_time" @input="setMeta('end_time', $event.target.value)" /></label>
        </div>
        <div class="onto-list-block">
          <div class="onto-list-head"><h4>{{ $t('ontology.editor.unitMap') }}</h4></div>
          <div class="onto-unit-grid">
            <label v-for="(unit, col) in meta.units || {}" :key="`u-${col}`" class="onto-field unit">
              <span class="mono">{{ col }}</span>
              <input :value="unit" @input="setUnit(col, $event.target.value)" />
            </label>
          </div>
          <p v-if="!Object.keys(meta.units || {}).length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
        </div>
      </template>

      <!-- ── 扩展键 ── -->
      <template v-else-if="section === 'advanced'">
        <p class="onto-hint">{{ $t('ontology.editor.unknownKey') }}</p>
        <div v-for="k in extensionKeys" :key="`ext-${k}`" class="onto-card">
          <div class="onto-card-head"><span class="onto-card-title mono">{{ k }}</span></div>
          <textarea rows="4" class="mono grow" :value="jsonOf(ontology[k])" @change="setJsonKey(k, $event.target.value)"></textarea>
        </div>
        <p v-if="!extensionKeys.length" class="onto-empty">{{ $t('ontology.editor.noItems') }}</p>
      </template>
    </div>

    <datalist id="onto-columns">
      <option v-for="c in allColumns" :key="c" :value="c" />
    </datalist>
    <datalist id="onto-stage-ids">
      <option v-for="s in stageIds" :key="s" :value="s" />
    </datalist>
    <datalist id="onto-equipment-ids">
      <option v-for="e in equipmentIds" :key="e" :value="e" />
    </datalist>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = defineProps({
  ontology: { type: Object, required: true },
  schemaKeys: { type: Array, default: () => [] },
});
const emit = defineEmits(['update:ontology']);

const KNOWN_TOP_KEYS = new Set([
  'ontology_version', 'created_at', 'provenance', 'scene', 'signals', 'relationships',
  'confounders', 'parameter_groups', 'physical_principles', 'known_failure_modes',
  'discrepancy_signals', 'metadata', 'excluded_columns', 'excluded_columns_note',
  'quality_target_causal_map', 'relationships_note',
]);

const roles = ['target', 'predictor', 'confounder', 'control', 'metadata'];
const confidences = ['KNOWN', 'INFERRED', 'UNKNOWN'];
const knowledgeSources = ['rag_retrieval', 'reference_doc', 'web_research', 'auto_inferred', 'user_provided'];
const behaviorMatches = ['CONSISTENT', 'CONTRADICTED', 'UNVERIFIED'];
const relTypes = ['causal', 'correlative', 'control', 'physical'];
const strengths = ['strong', 'moderate', 'weak'];
const functionalForms = ['linear', 'exponential', 'polynomial', 'inverse', 'monotonic', 'threshold', 'delayed_response', 'unknown'];
const severities = ['HIGH', 'MEDIUM', 'LOW', 'INFO'];
const buckets = [
  { key: 'inspection_signals', label: 'inspection' },
  { key: 'process_parameters', label: 'process' },
  { key: 'control_variables', label: 'control' },
  { key: 'events', label: 'events' },
  { key: 'metadata_columns', label: 'metadata' },
];

const sections = [
  { key: 'scene', icon: '◈', label: 'ontology.editor.scene' },
  { key: 'equipment', icon: '⛭', label: 'ontology.editor.equipment' },
  { key: 'stages', icon: '⇥', label: 'ontology.editor.stages' },
  { key: 'signals', icon: '∿', label: 'ontology.editor.signals' },
  { key: 'relationships', icon: '⇄', label: 'ontology.editor.relationships' },
  { key: 'confounders', icon: '⊗', label: 'ontology.editor.confounders' },
  { key: 'groups', icon: '▤', label: 'ontology.editor.groups' },
  { key: 'principles', icon: '∑', label: 'ontology.editor.principles' },
  { key: 'failures', icon: '⚠', label: 'ontology.editor.failureModes' },
  { key: 'discrepancies', icon: '◬', label: 'ontology.editor.discrepancies' },
  { key: 'metadata', icon: '⌗', label: 'ontology.editor.metadata' },
  { key: 'advanced', icon: '⋯', label: 'ontology.editor.advanced' },
];

const section = ref('signals');
const signalFilter = ref('all');
const newGroupName = ref('');

const scene = computed(() => props.ontology.scene || {});
const meta = computed(() => props.ontology.metadata || {});

const signalRows = computed(() => {
  const rows = [];
  for (const b of buckets) {
    if (signalFilter.value !== 'all' && signalFilter.value !== b.key) continue;
    const list = props.ontology.signals?.[b.key];
    if (!Array.isArray(list)) continue;
    list.forEach((sig, index) => rows.push({ bucket: b.key, index, sig: sig || {} }));
  }
  return rows;
});

const allColumns = computed(() =>
  buckets.flatMap((b) => (props.ontology.signals?.[b.key] || []).map((s) => s?.column).filter(Boolean)));
const stageIds = computed(() => (scene.value.stages || []).map((s) => s?.id).filter(Boolean));
const equipmentIds = computed(() => (scene.value.equipment || []).map((e) => e?.id).filter(Boolean));
const extensionKeys = computed(() =>
  Object.keys(props.ontology).filter((k) => !KNOWN_TOP_KEYS.has(k))
    .concat(Object.keys(props.ontology).filter((k) => k === 'excluded_columns')));

function countFor(key) {
  const o = props.ontology;
  switch (key) {
    case 'equipment': return (scene.value.equipment || []).length;
    case 'stages': return (scene.value.stages || []).length;
    case 'signals': return buckets.reduce((n, b) => n + (o.signals?.[b.key]?.length || 0), 0);
    case 'relationships': return (o.relationships || []).length;
    case 'confounders': return (o.confounders || []).length;
    case 'groups': return Object.keys(o.parameter_groups || {}).length;
    case 'principles': return (o.physical_principles || []).length;
    case 'failures': return (o.known_failure_modes || []).length;
    case 'discrepancies': return (o.discrepancy_signals || []).length;
    case 'advanced': return extensionKeys.value.length;
    default: return '';
  }
}

function bucketCount(key) { return props.ontology.signals?.[key]?.length || 0; }
function bucketLabel(key) { return buckets.find((b) => b.key === key)?.label || key; }
function bucketClass(key) { return `bucket-${key}`; }

/**
 * 所有编辑都通过「结构化克隆 + 整树替换」提交给父组件。
 * 这样父组件拥有唯一的 draft 真相，撤销/差异/校验都基于同一份快照。
 * structuredClone 不可用于含函数的对象 —— 本体是纯 JSON，安全。
 */
function commit(mutator) {
  const next = JSON.parse(JSON.stringify(props.ontology));
  mutator(next);
  emit('update:ontology', next);
}

function ensurePath(obj, path) {
  const parts = path.split('.');
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const k = parts[i];
    if (cur[k] === undefined || cur[k] === null) cur[k] = {};
    cur = cur[k];
  }
  const last = parts[parts.length - 1];
  if (!Array.isArray(cur[last])) cur[last] = [];
  return cur[last];
}

function setScene(field, value) {
  commit((o) => { o.scene = { ...(o.scene || {}), [field]: value }; });
}
function setMeta(field, value) {
  commit((o) => { o.metadata = { ...(o.metadata || {}), [field]: value }; });
}
function setUnit(col, value) {
  commit((o) => {
    o.metadata = o.metadata || {};
    o.metadata.units = { ...(o.metadata.units || {}), [col]: value };
  });
}
function setIndexed(rootKey, field, index, value) {
  commit((o) => {
    const list = Array.isArray(o[rootKey]?.[field]) ? [...o[rootKey][field]] : [];
    list[index] = value;
    o[rootKey] = { ...(o[rootKey] || {}), [field]: list };
  });
}
function removeIndexed(rootKey, field, index) {
  commit((o) => {
    const list = Array.isArray(o[rootKey]?.[field]) ? [...o[rootKey][field]] : [];
    list.splice(index, 1);
    o[rootKey] = { ...(o[rootKey] || {}), [field]: list };
  });
}
function setItem(path, index, field, value) {
  commit((o) => {
    const list = ensurePath(o, path);
    list[index] = { ...(list[index] || {}), [field]: value };
  });
}
function setRange(path, index, pos, raw) {
  commit((o) => {
    const list = ensurePath(o, path);
    const cur = Array.isArray(list[index]?.normal_range) ? [...list[index].normal_range] : [null, null];
    cur[pos] = raw === '' ? null : Number(raw);
    list[index] = { ...(list[index] || {}), normal_range: cur };
  });
}
function rangeOf(sig) {
  const r = Array.isArray(sig?.normal_range) ? sig.normal_range : [];
  return [r[0] ?? '', r[1] ?? ''];
}
function addItem(path, item) {
  commit((o) => { ensurePath(o, path).push(item); });
}
function removeItem(path, index, name) {
  const label = name || `#${index + 1}`;
  if (!window.confirm(t('ontology.editor.removeConfirm', { name: label }))) return;
  commit((o) => { ensurePath(o, path).splice(index, 1); });
}
function move(path, index, delta) {
  commit((o) => {
    const list = ensurePath(o, path);
    const target = index + delta;
    if (target < 0 || target >= list.length) return;
    const [item] = list.splice(index, 1);
    list.splice(target, 0, item);
  });
}
function addObjective() { commit((o) => { o.scene = o.scene || {}; (o.scene.objectives = o.scene.objectives || []).push(''); }); }
function addGroup() {
  const name = newGroupName.value.trim();
  if (!name) return;
  commit((o) => { o.parameter_groups = { ...(o.parameter_groups || {}), [name]: [] }; });
  newGroupName.value = '';
}
function removeGroup(name) {
  if (!window.confirm(t('ontology.editor.removeConfirm', { name }))) return;
  commit((o) => { const g = { ...(o.parameter_groups || {}) }; delete g[name]; o.parameter_groups = g; });
}
function setGroupMembers(name, members) {
  commit((o) => { o.parameter_groups = { ...(o.parameter_groups || {}), [name]: members }; });
}
function setJsonKey(key, raw) {
  try {
    const parsed = JSON.parse(raw);
    commit((o) => { o[key] = parsed; });
  } catch { /* 非法 JSON：保持原值，由 JSON 视图呈现错误 */ }
}
function jsonOf(v) { return JSON.stringify(v ?? null, null, 2); }

function splitList(s) {
  return String(s || '').split(',').map((x) => x.trim()).filter(Boolean);
}

function addSignal() {
  const bucket = signalFilter.value === 'all' ? 'process_parameters' : signalFilter.value;
  commit((o) => {
    o.signals = o.signals || {};
    o.signals[bucket] = o.signals[bucket] || [];
    o.signals[bucket].push({
      name: 'new_column', column: 'new_column', role: bucket === 'control_variables' ? 'control' : 'predictor',
      physical_meaning_confidence: 'UNKNOWN',
    });
  });
  section.value = 'signals';
}
function newEquipment() {
  return { id: `EQ-${Date.now().toString(36).slice(-4)}`, name: t('ontology.editor.newEquipment'), type: t('ontology.editor.unspecifed'), function: '' };
}
function newStage() {
  const seq = (scene.value.stages || []).length;
  return { id: `ST-${seq + 1}`, name: `${t('ontology.editor.newStage')} ${seq + 1}`, sequence: seq, key_physics: '', key_parameters: [] };
}
function newRelationship() {
  const cols = allColumns.value;
  return { from: cols[0] || '', to: cols[1] || cols[0] || '', type: 'correlative', strength: 'moderate', mechanism: '', inferred: true };
}
function newDiscrepancy() {
  const n = (props.ontology.discrepancy_signals || []).length + 1;
  return { id: `DS-${n}`, type: 'range_violation', columns: [], ontology_expectation: '', data_observation: '', diagnostic_meaning: '', severity: 'MEDIUM' };
}
</script>

<style scoped>
.onto-editor {
  display: grid;
  grid-template-columns: 196px minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
  height: 100%;
}
.onto-editor-rail {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  border-right: 1px solid var(--border);
  padding-right: 8px;
}
.onto-editor-rail-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: none;
  color: var(--text2);
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}
.onto-editor-rail-btn:hover { background: var(--surface); color: var(--text); }
.onto-editor-rail-btn.active {
  background: var(--accent-soft);
  border-color: var(--border-accent);
  color: var(--accent-bright);
}
.onto-editor-rail-icon { width: 15px; flex: none; text-align: center; opacity: 0.8; font-size: 12px; }
.onto-editor-rail-label {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.onto-editor-rail-count {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text3);
  flex: none;
  margin-left: 4px;
}
.onto-editor-pane { min-width: 0; overflow-y: auto; padding-right: 4px; }

.onto-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 4px 0 10px;
  flex-wrap: wrap;
}
.onto-list-head h4 { margin: 0; font-size: 12.5px; font-weight: 600; color: var(--text); }
.onto-head-actions { display: flex; align-items: center; gap: 6px; }
.onto-count-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text3);
  margin-left: 4px;
}

.onto-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  padding: 9px 10px;
  margin-bottom: 8px;
}
.onto-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.onto-card-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  flex: 0 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 280px;
}
.onto-card-title.mono { font-family: var(--font-mono); }
.onto-card-actions { margin-left: auto; display: flex; gap: 3px; }
.onto-badge-row { display: flex; gap: 4px; flex-wrap: wrap; }
.onto-badge {
  font-size: 9.5px;
  font-family: var(--font-mono);
  padding: 1px 6px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  color: var(--text2);
  background: var(--surface-soft);
  white-space: nowrap;
}
.onto-badge.conf-known { color: var(--green); border-color: rgba(143,191,106,0.35); }
.onto-badge.conf-inferred { color: var(--yellow); border-color: rgba(212,169,61,0.35); }
.onto-badge.conf-unknown { color: var(--text3); }
.onto-badge.bhv-consistent { color: var(--green); border-color: rgba(143,191,106,0.35); }
.onto-badge.bhv-contradicted { color: var(--red); border-color: rgba(212,93,61,0.4); }
.onto-badge.bhv-unverified { color: var(--text3); }
.onto-badge.rel-causal { color: #f97362; border-color: rgba(249,115,98,0.35); }
.onto-badge.rel-correlative { color: #4ea8f5; border-color: rgba(78,168,245,0.35); }
.onto-badge.rel-control { color: #31c9a8; border-color: rgba(49,201,168,0.35); }
.onto-badge.rel-physical { color: #c9a227; border-color: rgba(201,162,39,0.35); }
.onto-badge.inferred { color: var(--cyan); border-color: rgba(107,168,184,0.35); }
.onto-badge.sev-high { color: var(--red); border-color: rgba(212,93,61,0.4); }
.onto-badge.sev-medium { color: var(--yellow); border-color: rgba(212,169,61,0.35); }
.onto-badge.sev-low, .onto-badge.sev-info { color: var(--text3); }
.onto-badge.bucket-inspection_signals { color: #f97362; }
.onto-badge.bucket-control_variables { color: #31c9a8; }
.onto-badge.bucket-events { color: #b98cf0; }
.onto-badge.bucket-metadata_columns { color: #8b93a7; }

.onto-field-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 7px;
}
.onto-field { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.onto-field.wide { grid-column: 1 / -1; }
.onto-field > span {
  font-size: 10px;
  letter-spacing: 0.03em;
  color: var(--text3);
  text-transform: uppercase;
}
.onto-field input, .onto-field select, .onto-field textarea {
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  color: var(--text);
  font-size: 12px;
  padding: 4px 7px;
  font-family: inherit;
  min-width: 0;
}
.onto-field input.mono, .onto-field textarea.mono, textarea.mono { font-family: var(--font-mono); }
.onto-field input:focus, .onto-field select:focus, .onto-field textarea:focus {
  outline: none;
  border-color: var(--border-accent);
  background: var(--surface);
}
.onto-field.checkbox { flex-direction: row; align-items: center; gap: 6px; padding-top: 14px; }
.onto-field.checkbox input { accent-color: var(--accent); }
.onto-field.checkbox > span { text-transform: none; font-size: 11.5px; color: var(--text2); }

.onto-row { display: flex; gap: 6px; margin-bottom: 5px; align-items: center; }
.onto-row input.grow, input.grow, textarea.grow {
  flex: 1;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  color: var(--text);
  font-size: 12px;
  padding: 4px 7px;
}
.onto-icon-btn {
  border: 1px solid var(--border);
  background: var(--surface-soft);
  color: var(--text3);
  border-radius: var(--radius-xs);
  width: 22px; height: 22px;
  font-size: 11px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.onto-icon-btn:hover { color: var(--text); border-color: var(--border-strong); }
.onto-icon-btn.danger:hover { color: var(--red); border-color: rgba(212,93,61,0.45); }
.onto-mini-btn {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text2);
  border-radius: 999px;
  font-size: 11px;
  padding: 3px 10px;
  cursor: pointer;
}
.onto-mini-btn:hover { border-color: var(--border-accent); color: var(--accent-bright); }
.onto-select, .onto-input-inline {
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  color: var(--text2);
  font-size: 11px;
  padding: 3px 6px;
}
.onto-empty, .onto-hint { font-size: 11.5px; color: var(--text3); margin: 6px 0; }
.onto-unit-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 6px; }
.onto-field.unit { flex-direction: row; align-items: center; gap: 6px; }
.onto-field.unit > span { flex: 0 0 45%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 10.5px; }
</style>
