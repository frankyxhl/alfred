# REF-2113: Discussion Tracker 2026-03-19 D2

**Applies to:** FXA project
**Last updated:** 2026-03-19
**Last reviewed:** 2026-03-19
**Status:** Active

---

## Active Items

| DN | Status | Parent | Source | Created | Updated | Topic |
|----|--------|--------|--------|---------|---------|-------|
| D18 | Done | — | User | 15:00 | 15:05 | 每次 TDD 开始时必须读 COR-1500，不能跳过 |
| D19 | Done | — | User | 15:30 | 22:15 | 进度更新格式集成到 SOP |
| D20 | Done | — | User | 20:10 | 22:30 | 如何确保后台 agent 仍在工作 → ALF-2204 PRP |
| D21 | Done | — | User | 20:20 | 21:40 | 重派 agent 时应优先 resume 而不是全新开始 |
| D22 | Done | D21 | User | 20:45 | 21:40 | 如何让 Claude Code 用 team-xxx 方式而非 Agent 方式派发 |
| D23 | Done | — | User | 21:30 | 22:00 | af 各命令的 --help 内容太简陋，需要丰富 |

## Archived Items

(none)

## Discussion Notes

### D18: 每次 TDD 开始时必须读 COR-1500
- **Source**: User 观察到我们跳过了 COR-1500 直接开始 TDD
- **Decision**: 已存为 feedback memory，每次 TDD 前必须 `af read COR-1500`
- **Result**: feedback_read_sop_before_tdd.md

### D19: 进度更新格式集成到 SOP
- **Source**: User 喜欢 CHG 执行中的 ASCII 进度更新格式
- **Status**: 待讨论如何集成到 COR-1500 Progress Tracker 或 COR-1601/1602

### D20: 如何确保后台 agent 仍在工作
- **Source**: User 问后台 agent 是否还在跑
- **Decision**: 3 种方式：tail output file、等 task-notification、检查是否卡住
- **Result**: 已讨论完毕

### D21 + D22: /team skill session 管理改进（合并讨论）

**问题：**
1. Leader 直接用 `Agent(subagent_type="team-glm")` 跳过 /team skill 的 session 管理
2. Agent 被停掉后重派是全新 context，无法 resume

**决定：**
1. Leader 必须始终用 `Skill("team", ...)` 派发，不得直接用 Agent
2. `/team` 语法改为显式 new/resume，废弃隐式模式：
   - `/team new glm "task"` — 强制新 session
   - `/team resume glm` — resume 上次任务
   - `/team resume glm "追加指令"` — resume + 追加
   - `/team glm "task"` — 报错，要求明确 new/resume
3. `new`、`resume` 加入 reserved words（与 status/clear/plan/help 同级）
4. resume 机制：读 sessions.json → 注入上次 context → 传 session ID 给外部 CLI

**Status**: 方案确定，待实现（改 /team skill）
- **Source**: User 多次因误按 Esc 停掉后台 agent，重派时全新开始浪费 context
- **Decision**: 记为后续改进项，可能需要 PRP
- **Result**: 已存 project_team_resume_improvement.md，待创建 PRP

---

## Change History

| Date | Change | By |
|------|--------|----|
| 2026-03-19 | Initial version — D18~D21 from session 2 | Claude Code |
