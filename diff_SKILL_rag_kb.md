# Diff .omp vs .claude SKILL.md

## Path Resolution Section

### .omp version (lines ~63-69):
```
When loaded from OMP harness (`.omp/skills/rag-knowledge-builder/`), resources resolve via:
```
SKILL_PATH   = <this-skill-directory>/../../../.omp/skills/rag-knowledge-builder
SHARED_PATH  = <this-skill-directory>/../../../.omp/shared
PROJECT_ROOT = cd $SKILL_PATH/../../.. && pwd
```
In standalone/Claude harness mode, SKILL_PATH is the deployment directory directly.
```

### .claude version (lines ~62-65):
```
SKILL_PATH   = <skill 部署位置>
PROJECT_ROOT = cd $SKILL_PATH/../../.. && pwd
```
(No SHARED_PATH, no dual-mode description)
