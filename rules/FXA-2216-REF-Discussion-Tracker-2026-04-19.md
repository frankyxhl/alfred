# REF-2216: Discussion Tracker 2026-04-19

**Applies to:** FXA project
**Last updated:** 2026-04-19
**Last reviewed:** 2026-04-19
**Status:** Active

---

## Active Items

| DN | Status | Parent | Source | Created | Updated | Topic                                                                                    |
|----|--------|--------|--------|---------|---------|------------------------------------------------------------------------------------------|
| D1 | Open   | —      | Claude | 11:00   | —       | Cross-SOP loop metadata — parser regex validation (layer 1)                              |
| D2 | Open   | —      | Claude | 11:00   | —       | Cross-SOP loop metadata — `af validate` target-SOP-exists check (layer 2a)               |
| D3 | Open   | —      | Claude | 11:00   | —       | Cross-SOP loop metadata — `af validate` step-index-in-range check (layer 2b)             |
| D4 | Open   | —      | Claude | 11:00   | —       | Cross-SOP loop metadata — `af plan` runtime errors (target-not-composed + forward-loop)  |

## Archived Items

| DN | Parent | Source | Topic |
|----|--------|--------|-------|

## Discussion Notes

### D1: Parser-level validation (layer 1)

The Parser 是"读 SOP 文件的那一层"。今天 `parser.py` 碰到 `Workflow loops:` 的 `to` 字段只处理 int。新版本要让它也能处理形如 `"COR-1500.3"` 的字符串。

**做什么：** 在 `core/parser.py` 里加一个正则：
```python
CROSS_SOP_REF = re.compile(r"^(?P<prefix>[A-Z]{3})-(?P<acid>\d{4})\.(?P<step>\d+)$")
```

**检查什么：** 读 SOP 的时候，如果 `to` 是字符串，就得长得像 `COR-1500.3`——三个大写字母 + 4 位数字 + 点 + 步骤号。符合 → 通过；不符合 → 直接抛 `MalformedDocumentError`，读不进来。

**不能通过的例子：**
- `"COR-1500"`（缺 `.step`）
- `"cor-1500.3"`（前缀小写）
- `"1500.3"`（没 prefix）

**好处：** 最早发现错误。SOP 写错了立刻知道，不会等到 plan 或 validate 才暴露。

### D2: Static SOP existence check (layer 2a)

`af validate` 是你随时跑的那个命令，检查所有文档结构合法。今天它**只看每个文档自己**（格式、metadata、Change History）。新增的检查会让它第一次**跨文档**看。

**做什么：** 当 `af validate` 遇到一个 SOP 有 `Workflow loops.to = "COR-1500.3"` 这种引用时，它需要：
1. 扫一遍 PKG / USR / PRJ 三层所有文档
2. 找有没有 `COR-1500` 这个 SOP
3. 找不到就报错：
   ```
   ERROR: FXA-2149 Workflow loops[0].to references COR-1500 — no such SOP in corpus
   ```

**好处：** 你改 SOP 的时候手滑打错 ACID（比如把 `COR-1500` 写成 `COR-1005`），`af validate` 当场抓出来。不然这个错到 `af plan` 才爆，或者更糟 —— 图画错了你也看不出来。

### D3: Static step-index-in-range check (layer 2b)

紧跟 D2 的第二个检查。D2 确认目标 SOP 存在；D3 确认目标**步骤**存在。

**做什么：** `Workflow loops.to = "COR-1500.3"` 意思是"跳回 COR-1500 的第 3 步"。`af validate` 需要：
1. 读 COR-1500 的 body
2. 用 `_parse_steps_for_json` 数它有几个编号步骤（比如 10 个）
3. 检查 3 ≤ 10 → OK；如果是 `"COR-1500.99"` → 报错：
   ```
   ERROR: COR-1500.99 — step index 99 out of range (COR-1500 has 10 steps)
   ```

**好处：** 防止"SOP 存在但步骤号越界"。比如你引用了 COR-1500 的第 3 步，后来 COR-1500 被重写步骤变少了，这时 `af validate` 能告诉你 SOP A 里的引用已经 dangling，要更新。

### D4: Plan-time composition + direction checks (layer 3)

这一层是跑 `af plan` 时才检查的。D2/D3 是静态检查；D4 是**动态检查**——取决于你这次 plan 把哪些 SOP 组合在一起。

**为什么要跑时才检查：**
- `Workflow loops.to = "COR-1500.3"` 静态上没问题（COR-1500 存在、第 3 步也存在）
- 但你这次 `af plan` 只带了 COR-1602，没带 COR-1500 —— 这时跨 SOP 的 loop 指向了一个"不在这次 plan 里"的目标，画不出线
- 或者你把 COR-1500 放在了 COR-1602 **后面** —— 从后面跳回前面才合理（back-edge），反过来就没语义

**两个具体错误：**

1. **target SOP 没在 composed plan 里：**
   ```
   ERROR: FXA-2149 Workflow loops[0].to = "COR-1500.3"
          — COR-1500 not in composed plan (add positionally: af plan FXA-2149 COR-1500 ...)
   ```
   告诉你怎么修：把 COR-1500 也加进 plan 参数。

2. **方向反了（forward loop）：**
   ```
   ERROR: FXA-2149 Workflow loops[0].to = "COR-1500.3"
          — target SOP precedes source; back-edges only
   ```
   这个比较罕见，但防止你意外画出"从前往后"的循环（没意义）。

**好处：** `af validate` 管不到的"组合合不合理"这层，在 `af plan` 运行时当场挡住。

---

## Change History

| Date       | Change                                                                                  | By             |
|------------|-----------------------------------------------------------------------------------------|----------------|
| 2026-04-19 | Initial version                                                                         | —              |
| 2026-04-19 | D1–D4 opened: cross-SOP loop metadata validation layers (PRP draft for FXA-2212 scope) | Frank + Claude |
