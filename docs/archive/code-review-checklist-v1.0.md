# Code Review Checklist v2.0

> 目标：让每次 code review 都有同一套顺序、同一套标准、同一套质量门禁。  
> 核心原则：**工具能自动检查的，不要靠 reviewer 手工记；reviewer 主要看工具看不懂的设计、业务、安全上下文和风险。**

---

## 0. 使用方式

### 0.1 检查项类型

- **G / Gate**：质量门禁。必须由工具、CI、配置或流程保证。
- **A / Automated**：应该由 formatter、linter、type checker、test runner、SAST、SCA、secret scanner 等工具自动检查。
- **H / Human Review**：需要 reviewer 判断，工具不能完全替代。

### 0.2 评论等级

- **P0 / Blocker**：必须修。不修不能合并。
- **P1 / Should Fix**：本次强烈建议修；如果不修，必须有 follow-up issue 和 owner。
- **P2 / Nit**：小问题、风格、可读性建议，不阻塞合并。
- **N/A**：本次不适用。

### 0.3 合并最低标准

- [ ] 0.3.1 所有 **G / Gate** 都通过。
- [ ] 0.3.2 **P0 = 0**。
- [ ] 0.3.3 涉及安全、权限、数据库、依赖、CI/CD、生产配置、隐私数据的变更，必须有对应 owner 或专家 review。
- [ ] 0.3.4 核心功能有测试；没有测试时，PR/MR 必须说明原因、风险和补救计划。
- [ ] 0.3.5 高风险变更有发布、灰度、回滚或 feature flag 方案。

---

# 1. 工具与质量门禁

## 1.1 仓库必须具备的基础质量门禁

### 1.1.1 本地和 CI 使用同一套命令

- [ ] G-1.1.1.1 仓库根目录有统一入口，例如 `make check`、`npm run check`、`pnpm check`、`poetry run poe check`、`./scripts/check.sh`。
- [ ] G-1.1.1.2 至少包含：format check、lint、type check、unit test。
- [ ] G-1.1.1.3 CI 中运行的命令和本地命令一致。
- [ ] G-1.1.1.4 README 或 CONTRIBUTING 中写清楚如何安装和运行这些工具。
- [ ] G-1.1.1.5 工具版本被锁定，例如 lockfile、tool version manager、Docker image、CI action version。

### 1.1.2 CI 必须 fail closed

- [ ] G-1.1.2.1 formatter 不通过时 CI 失败。
- [ ] G-1.1.2.2 linter 不通过时 CI 失败。
- [ ] G-1.1.2.3 type checker 不通过时 CI 失败。
- [ ] G-1.1.2.4 test 不通过时 CI 失败。
- [ ] G-1.1.2.5 secret scan 命中高危 secret 时 CI 失败。
- [ ] G-1.1.2.6 dependency scan 命中高危漏洞时 CI 失败，或必须有明确例外审批。
- [ ] G-1.1.2.7 SAST 命中高危安全问题时 CI 失败，或必须有安全 owner 批准。

### 1.1.3 工具例外必须可追踪

- [ ] G-1.1.3.1 `eslint-disable`、`# noqa`、`# type: ignore`、`// @ts-ignore` 等 suppressions 必须有原因。
- [ ] G-1.1.3.2 例外最好指向 issue、ticket 或代码注释中的业务原因。
- [ ] G-1.1.3.3 禁止为了合并而整文件关闭 lint/type/security 检查，除非 owner 明确批准。
- [ ] G-1.1.3.4 生成代码、第三方 vendored code、migration dump 等应有明确 exclude 规则。

### 1.1.4 Reviewer 不应该手工重复工具工作

- [ ] H-1.1.4.1 如果 reviewer 发现“单行超过 120 列”“函数超过 100 行”“复杂度过高”等问题，优先评论：**请把这个规则加入工具/CI**。
- [ ] H-1.1.4.2 对单个违反风格的点，不应逐行 nitpick；应该要求配置 formatter/linter。
- [ ] H-1.1.4.3 已由工具检查的项目，reviewer 只看例外是否合理。

---

## 1.2 推荐安装的工具类型

> 下面是类型，不要求所有项目使用同一个品牌。按技术栈选择。

| 领域 | 必备工具类型 | 例子 |
|---|---|---|
| 格式化 | Formatter | Prettier、Black、Ruff format、gofmt、rustfmt、ktlint、dotnet format |
| 静态检查 | Linter | ESLint、Ruff、golangci-lint、Checkstyle、PMD、Detekt、Clippy |
| 类型检查 | Type Checker | TypeScript compiler、mypy、pyright、javac/kotlinc、go test/build、Roslyn analyzers |
| 单元测试 | Test Runner | Jest、Vitest、pytest、JUnit、Go test、xUnit、cargo test |
| 覆盖率 | Coverage | c8/nyc、coverage.py、JaCoCo、go test cover、cargo tarpaulin |
| Secret 扫描 | Secret Scanner | Gitleaks、TruffleHog、GitHub secret scanning、GitLab secret detection |
| 依赖扫描 | SCA | Dependabot、Renovate、npm audit、pip-audit、OSV-Scanner、OWASP Dependency-Check、Snyk |
| 安全扫描 | SAST | Semgrep、CodeQL、Bandit、SonarQube/SonarCloud |
| 容器/IaC | Image/IaC Scanner | Trivy、Grype、Checkov、tfsec、Terrascan |
| API 契约 | Contract/Schema Check | OpenAPI validator、GraphQL schema check、Pact |

### 1.2.1 JavaScript / TypeScript 项目

- [ ] G-1.2.1.1 已安装并配置 formatter，例如 Prettier。
- [ ] G-1.2.1.2 已安装并配置 ESLint。
- [ ] G-1.2.1.3 TypeScript 项目必须运行 `tsc --noEmit` 或等价 type check。
- [ ] G-1.2.1.4 React/Vue/Next/Nuxt 等项目启用对应 plugin。
- [ ] G-1.2.1.5 测试工具已接入 CI，例如 Jest、Vitest、Playwright、Cypress。
- [ ] G-1.2.1.6 package manager lockfile 被提交，例如 `package-lock.json`、`pnpm-lock.yaml`、`yarn.lock`。

### 1.2.2 Python 项目

- [ ] G-1.2.2.1 已安装并配置 formatter，例如 Black 或 Ruff format。
- [ ] G-1.2.2.2 已安装并配置 linter，例如 Ruff。
- [ ] G-1.2.2.3 已安装并配置 type checker，例如 mypy 或 pyright。
- [ ] G-1.2.2.4 已安装并配置 test runner，例如 pytest。
- [ ] G-1.2.2.5 已配置 coverage。
- [ ] G-1.2.2.6 已配置依赖和安全扫描，例如 pip-audit、OSV-Scanner、Bandit、Semgrep。
- [ ] G-1.2.2.7 `requirements.txt`、`poetry.lock`、`uv.lock`、`Pipfile.lock` 等 lockfile 管理清楚。

### 1.2.3 Go 项目

- [ ] G-1.2.3.1 `gofmt` 或 `go fmt` 在 CI 中运行。
- [ ] G-1.2.3.2 `go vet` 在 CI 中运行。
- [ ] G-1.2.3.3 已配置 `golangci-lint` 或等价 linter。
- [ ] G-1.2.3.4 `go test ./...` 在 CI 中运行。
- [ ] G-1.2.3.5 `go.mod` 和 `go.sum` 正确提交。

### 1.2.4 Java / Kotlin 项目

- [ ] G-1.2.4.1 已配置 formatter 或 style check。
- [ ] G-1.2.4.2 已配置 Checkstyle、PMD、SpotBugs、Error Prone、Detekt、ktlint 等至少一种质量检查。
- [ ] G-1.2.4.3 JUnit 或等价测试在 CI 中运行。
- [ ] G-1.2.4.4 Maven/Gradle dependency lock 或版本管理清楚。

### 1.2.5 Rust 项目

- [ ] G-1.2.5.1 `cargo fmt --check` 在 CI 中运行。
- [ ] G-1.2.5.2 `cargo clippy` 在 CI 中运行。
- [ ] G-1.2.5.3 `cargo test` 在 CI 中运行。
- [ ] G-1.2.5.4 `Cargo.lock` 是否提交符合项目类型约定。

---

## 1.3 建议自动化阈值

> 阈值不是绝对真理。建议先作为默认值，再根据团队和语言调整。重点是：**阈值要写进工具配置，并由 CI 执行。**

| 项目 | 建议阈值 | 类型 | 说明 |
|---|---:|---|---|
| 单行长度 | hard max 120 列 | A/G | 超过 120 通常影响并排 review；formatter 的 print width 不一定等于硬性上限。 |
| 函数/方法长度 | hard max 100 行，prefer 20–50 行 | A/G + H | 超过 100 行通常需要拆分，例外需说明。 |
| 文件长度 | source prefer < 500 行 | A/G + H | 大文件通常意味着职责过多；测试文件可适度放宽。 |
| 类长度 | prefer < 300–500 行 | A/G + H | 超过时检查是否 God class。 |
| 参数个数 | prefer ≤ 3，hard max 5 | A/G + H | 参数过多时考虑参数对象、DTO、builder。 |
| 嵌套深度 | hard max 3–4 层 | A/G + H | 深嵌套优先用 early return、guard clause、拆函数。 |
| 圈复杂度 | prefer ≤ 10 | A/G + H | 超过时拆分分支、策略模式、表驱动。 |
| 认知复杂度 | prefer ≤ 15 | A/G + H | 比圈复杂度更贴近阅读难度。 |
| 函数语句数 | prefer ≤ 30–50 | A/G + H | 比行数更稳定，适合 JS/TS、Python。 |
| TODO 数量 | 不新增无 owner 的 TODO | A/H | TODO 必须有 owner 或 issue。 |
| 测试覆盖率 | 不低于主分支 baseline | G | 不建议盲目追求固定百分比，但不应下降。 |

---

# 2. PR/MR 入口检查

## 2.1 变更意图

- [ ] H-2.1.1 PR/MR 标题清楚描述变更。
- [ ] H-2.1.2 描述中说明：为什么改、改了什么、怎么验证。
- [ ] H-2.1.3 有关联 issue、ticket、需求、设计文档或事故复盘。
- [ ] H-2.1.4 Reviewer 不需要靠猜来理解业务背景。

## 2.2 变更范围

- [ ] H-2.2.1 变更聚焦在一个主题。
- [ ] H-2.2.2 没有混入无关格式化、重构、依赖升级、实验代码。
- [ ] H-2.2.3 大 PR 是否能拆成多个小 PR。
- [ ] H-2.2.4 删除代码是否确认没有调用方、没有灰度依赖、没有历史数据依赖。

## 2.3 作者自检

- [ ] G-2.3.1 作者已运行统一 check 命令。
- [ ] H-2.3.2 作者说明了测试方式。
- [ ] H-2.3.3 作者说明了风险、已知限制和回滚方式。
- [ ] H-2.3.4 作者标注了需要重点 review 的文件或逻辑。

---

# 3. 架构与设计

## 3.1 设计位置

- [ ] H-3.1.1 代码放在正确模块、目录、层级中。
- [ ] H-3.1.2 没有把业务逻辑放进 controller、view、route handler 或脚本入口中。
- [ ] H-3.1.3 没有把基础设施细节泄漏到领域层。
- [ ] H-3.1.4 没有为了一个临时需求污染公共抽象。

## 3.2 依赖方向

- [ ] H-3.2.1 依赖方向符合架构，例如外层依赖内层，内层不依赖外层。
- [ ] H-3.2.2 没有引入循环依赖。
- [ ] H-3.2.3 没有通过全局变量、单例、静态状态绕过依赖边界。
- [ ] H-3.2.4 外部服务调用封装在清晰边界中，便于测试和替换。

## 3.3 抽象程度

- [ ] H-3.3.1 没有过度设计。
- [ ] H-3.3.2 没有为了“未来也许会用”提前创建复杂框架。
- [ ] H-3.3.3 没有复制粘贴已有逻辑。
- [ ] H-3.3.4 新抽象有明确当前使用场景。
- [ ] H-3.3.5 抽象命名和业务概念一致。

## 3.4 兼容性

- [ ] H-3.4.1 对外 API、事件、数据库 schema 是否向后兼容。
- [ ] H-3.4.2 是否支持新旧版本服务同时运行。
- [ ] H-3.4.3 是否需要 feature flag 或双写/双读。
- [ ] H-3.4.4 是否考虑旧客户端、移动端、缓存、CDN、队列积压消息。

---

# 4. 文件与模块级检查

## 4.1 文件职责

- [ ] H-4.1.1 一个文件是否主要表达一个概念或职责。
- [ ] H-4.1.2 文件名是否准确表达内容。
- [ ] H-4.1.3 文件中是否混合了业务逻辑、I/O、格式化、配置、测试数据等不同职责。
- [ ] H-4.1.4 是否应该拆分为 domain、service、repository、adapter、schema、test fixture 等。

## 4.2 文件大小与组织

- [ ] A-4.2.1 文件长度超过阈值时工具报警。
- [ ] H-4.2.2 大文件是否仍然结构清晰，还是已经变成 God file。
- [ ] H-4.2.3 文件顶部 import 是否清晰，没有重复和无用 import。
- [ ] A-4.2.4 import 顺序由工具自动整理。
- [ ] H-4.2.5 public API 和 private helper 是否分区清楚。

## 4.3 模块边界

- [ ] H-4.3.1 模块导出的东西是否必要。
- [ ] H-4.3.2 没有导出内部 helper。
- [ ] H-4.3.3 没有通过相对路径穿透内部实现，例如跨层 `../../internal/...`。
- [ ] H-4.3.4 没有新增难以测试的模块级副作用。

## 4.4 生成代码和第三方代码

- [ ] G-4.4.1 生成代码不应人工修改。
- [ ] G-4.4.2 生成代码有生成命令和来源说明。
- [ ] H-4.4.3 Reviewer 主要 review 生成配置、schema 或模板，不逐行 review 生成结果。
- [ ] G-4.4.4 第三方 vendored code 有来源、版本、license 记录。

---

# 5. 函数与方法级检查

## 5.1 函数职责

- [ ] H-5.1.1 函数是否只做一件主要事情。
- [ ] H-5.1.2 函数名是否能概括真实行为。
- [ ] H-5.1.3 函数名是否包含动词或明确意图，例如 `calculateTotal`、`validateRequest`、`loadUserById`。
- [ ] H-5.1.4 函数没有同时做：校验、查询、计算、写库、发消息、格式化响应。
- [ ] H-5.1.5 如果函数有多个阶段，阶段是否可以拆成私有 helper。

## 5.2 函数长度

- [ ] A-5.2.1 函数/方法行数由工具检查。
- [ ] G-5.2.2 默认 hard max：100 行。
- [ ] H-5.2.3 超过 50 行时 reviewer 应主动判断是否能拆分。
- [ ] H-5.2.4 超过 100 行仍不拆分时，PR/MR 必须说明原因。
- [ ] H-5.2.5 例外场景可以包括：简单字段映射、测试 fixture、生成代码、非常线性的脚本步骤，但仍应可读。

## 5.3 复杂度

- [ ] A-5.3.1 圈复杂度由工具检查，默认建议 ≤ 10。
- [ ] A-5.3.2 认知复杂度由工具检查，默认建议 ≤ 15。
- [ ] A-5.3.3 嵌套深度由工具检查，默认建议 ≤ 3–4。
- [ ] H-5.3.4 是否存在多层 `if/else`、`switch`、循环嵌套。
- [ ] H-5.3.5 是否可以用 guard clause / early return 减少嵌套。
- [ ] H-5.3.6 是否可以用表驱动、策略模式、多态、map dispatch 或拆函数降低复杂度。
- [ ] H-5.3.7 是否存在多个布尔 flag 控制不同流程。

## 5.4 参数

- [ ] A-5.4.1 参数数量由工具检查，默认建议 ≤ 5，prefer ≤ 3。
- [ ] H-5.4.2 参数顺序是否容易混淆。
- [ ] H-5.4.3 多个同类型参数是否应该改成对象、DTO、named arguments 或 builder。
- [ ] H-5.4.4 布尔参数是否导致函数有两种行为；如果是，考虑拆成两个函数。
- [ ] H-5.4.5 可选参数是否有清楚默认值。
- [ ] H-5.4.6 参数是否被函数内部意外修改。

## 5.5 返回值

- [ ] H-5.5.1 返回值类型清楚，不需要调用方猜。
- [ ] H-5.5.2 不要混合返回 `null`、`undefined`、空数组、异常、特殊字符串表示同一类失败。
- [ ] H-5.5.3 成功和失败路径是否清楚区分。
- [ ] H-5.5.4 是否需要 Result/Either/Option、错误对象、状态码或领域异常。
- [ ] H-5.5.5 返回集合时是否说明排序、去重、分页、最大数量。

## 5.6 副作用

- [ ] H-5.6.1 函数是否有隐藏副作用，例如写数据库、发消息、改全局状态、改输入对象。
- [ ] H-5.6.2 函数名是否反映副作用，例如 `save...`、`send...`、`update...`。
- [ ] H-5.6.3 纯计算函数是否保持纯，不依赖当前时间、随机数、环境变量、全局配置。
- [ ] H-5.6.4 需要时间、随机数、外部服务时，是否通过参数或依赖注入，便于测试。

## 5.7 错误处理

- [ ] H-5.7.1 失败路径是否完整。
- [ ] H-5.7.2 没有吞异常。
- [ ] H-5.7.3 没有捕获过宽异常后继续执行，例如裸 `except`、`catch (Exception)`、`catch (Throwable)`。
- [ ] H-5.7.4 错误信息足够定位，但不泄漏敏感信息。
- [ ] H-5.7.5 是否区分业务错误、输入错误、权限错误、外部服务错误、系统错误。
- [ ] H-5.7.6 retry 是否有上限、退避、幂等保护。
- [ ] H-5.7.7 timeout 是否设置在外部调用上。
- [ ] H-5.7.8 finally/defer/cleanup 是否保证资源释放。

## 5.8 输入校验

- [ ] H-5.8.1 函数是否说明输入前置条件。
- [ ] H-5.8.2 外部输入在边界层校验。
- [ ] H-5.8.3 内部函数是否避免重复校验，或清楚表达调用约束。
- [ ] H-5.8.4 是否检查空值、长度、范围、格式、枚举、时区、编码。
- [ ] H-5.8.5 不可信输入不会直接进入 SQL、shell、HTML、日志、路径、模板。

## 5.9 状态与可变性

- [ ] H-5.9.1 变量作用域尽可能小。
- [ ] H-5.9.2 避免不必要的可变变量。
- [ ] H-5.9.3 避免在循环中修改外部状态导致难以理解。
- [ ] H-5.9.4 共享状态有并发保护。
- [ ] H-5.9.5 函数不依赖隐式执行顺序。

## 5.10 异步与并发

- [ ] H-5.10.1 promise/future/coroutine 是否正确 await。
- [ ] H-5.10.2 并发任务是否有取消、timeout、错误传播。
- [ ] H-5.10.3 并发写入是否有锁、事务、唯一约束或乐观锁。
- [ ] H-5.10.4 是否存在 race condition。
- [ ] H-5.10.5 是否存在死锁风险。
- [ ] H-5.10.6 批量并发是否有限流，避免打爆下游。

## 5.11 可测试性

- [ ] H-5.11.1 函数是否容易单元测试。
- [ ] H-5.11.2 是否避免直接依赖当前时间、随机数、网络、文件系统、环境变量。
- [ ] H-5.11.3 依赖是否可注入或 mock。
- [ ] H-5.11.4 分支是否能被测试覆盖。
- [ ] H-5.11.5 复杂私有逻辑是否应该提取成可测试模块。

## 5.12 性能

- [ ] H-5.12.1 函数中是否有不必要的重复计算。
- [ ] H-5.12.2 循环中是否调用数据库、网络或昂贵 I/O。
- [ ] H-5.12.3 是否对大数组、大对象、大文件做了全量加载。
- [ ] H-5.12.4 是否需要分页、流式处理、批处理或缓存。
- [ ] H-5.12.5 是否避免在热路径中做日志字符串拼接、JSON stringify、大对象复制。

## 5.13 函数注释

- [ ] H-5.13.1 注释解释“为什么”，而不是重复“做了什么”。
- [ ] H-5.13.2 复杂业务规则有注释或文档链接。
- [ ] H-5.13.3 public API 函数有必要的参数、返回值、异常说明。
- [ ] H-5.13.4 注释没有过期。
- [ ] H-5.13.5 TODO 有 owner 和 issue。

---

# 6. 类、组件与对象

## 6.1 类职责

- [ ] H-6.1.1 类是否有单一清晰职责。
- [ ] H-6.1.2 没有 God class。
- [ ] H-6.1.3 类名是否表达领域概念，而不是泛化的 `Manager`、`Helper`、`Util`。
- [ ] H-6.1.4 方法数量是否合理。
- [ ] H-6.1.5 状态和行为是否放在同一个合理抽象中。

## 6.2 封装

- [ ] H-6.2.1 内部状态没有不必要暴露。
- [ ] H-6.2.2 public 方法数量控制合理。
- [ ] H-6.2.3 不变量在 constructor、factory 或 validation 中建立。
- [ ] H-6.2.4 对象创建后是否可能处于非法状态。
- [ ] H-6.2.5 setter 是否会破坏不变量。

## 6.3 继承与组合

- [ ] H-6.3.1 是否真的需要继承。
- [ ] H-6.3.2 是否可以用组合替代继承。
- [ ] H-6.3.3 子类是否遵守父类契约。
- [ ] H-6.3.4 抽象类、接口、泛型是否降低复杂度，而不是增加复杂度。

## 6.4 依赖注入

- [ ] H-6.4.1 依赖是否通过构造函数或明确参数传入。
- [ ] H-6.4.2 类内部是否直接 new 外部服务，导致难以测试。
- [ ] H-6.4.3 是否避免 service locator、全局单例造成隐藏依赖。
- [ ] H-6.4.4 mock/stub 是否容易替换。

---

# 7. 变量、数据结构与模型

## 7.1 命名

- [ ] H-7.1.1 变量名准确表达含义。
- [ ] H-7.1.2 避免 `data`、`info`、`item`、`obj`、`tmp` 等模糊名字，除非作用域极小。
- [ ] H-7.1.3 布尔变量使用 `is`、`has`、`can`、`should`、`requires` 等前缀。
- [ ] H-7.1.4 单位写进变量名，例如 `timeoutMs`、`sizeBytes`、`amountCents`。
- [ ] H-7.1.5 业务术语和产品、文档、数据库字段一致。

## 7.2 类型与空值

- [ ] H-7.2.1 类型尽可能具体。
- [ ] H-7.2.2 避免过度使用 `any`、`object`、`dict`、`Map<String, Object>`。
- [ ] H-7.2.3 可空字段清楚标注。
- [ ] H-7.2.4 调用方知道什么时候返回空、什么时候抛错。
- [ ] H-7.2.5 Optional/nullable/default value 的语义一致。

## 7.3 数据结构选择

- [ ] H-7.3.1 List、Set、Map、Queue、Tree 等选择符合访问模式。
- [ ] H-7.3.2 查找密集场景是否避免 O(n) 反复扫描。
- [ ] H-7.3.3 数据结构是否表达唯一性、顺序、不可变性。
- [ ] H-7.3.4 大对象是否避免不必要深拷贝。

## 7.4 常量与枚举

- [ ] H-7.4.1 魔法数字、魔法字符串提取成常量或枚举。
- [ ] H-7.4.2 常量命名表达业务含义。
- [ ] H-7.4.3 枚举新增值是否考虑所有 switch/match 分支。
- [ ] A-7.4.4 穷尽性检查由 type checker 或 linter 保证。

---

# 8. API、接口与契约

## 8.1 请求输入

- [ ] H-8.1.1 请求 schema 清楚。
- [ ] H-8.1.2 输入验证在服务端执行。
- [ ] H-8.1.3 长度、范围、格式、枚举、必填字段有验证。
- [ ] H-8.1.4 文件上传有大小、类型、内容、病毒/恶意文件风险检查。
- [ ] H-8.1.5 请求中的 ID 是否做权限校验，避免 IDOR。

## 8.2 响应输出

- [ ] H-8.2.1 response schema 向后兼容。
- [ ] H-8.2.2 不暴露内部字段、权限字段、debug 字段、PII。
- [ ] H-8.2.3 错误码、状态码、错误消息符合约定。
- [ ] H-8.2.4 分页、排序、过滤语义清楚。
- [ ] H-8.2.5 字段新增、删除、改名是否影响旧客户端。

## 8.3 API 文档与契约测试

- [ ] H-8.3.1 OpenAPI/GraphQL schema/SDK 类型定义已更新。
- [ ] G-8.3.2 schema 校验在 CI 中执行。
- [ ] H-8.3.3 需要 contract test 的接口已补测试。
- [ ] H-8.3.4 API 版本策略清楚。

---

# 9. 数据库与持久化

## 9.1 Migration

- [ ] H-9.1.1 migration 可回滚，或明确不可回滚原因。
- [ ] H-9.1.2 migration 支持新旧代码同时运行。
- [ ] H-9.1.3 大表变更是否避免长锁表。
- [ ] H-9.1.4 新增 NOT NULL 字段是否处理历史数据。
- [ ] H-9.1.5 删除字段是否分阶段：先停止写、停止读、确认无依赖、再删除。
- [ ] H-9.1.6 索引创建是否考虑 online/concurrent。

## 9.2 查询

- [ ] H-9.2.1 没有 N+1 查询。
- [ ] H-9.2.2 where/order/group/join 使用合适索引。
- [ ] H-9.2.3 没有无分页全表查询。
- [ ] H-9.2.4 没有在循环里执行查询。
- [ ] H-9.2.5 ORM lazy loading 行为是否明确。
- [ ] H-9.2.6 SQL 参数化，禁止拼接不可信输入。

## 9.3 事务与一致性

- [ ] H-9.3.1 事务边界正确。
- [ ] H-9.3.2 事务中没有慢 I/O、外部 API、长时间计算。
- [ ] H-9.3.3 并发写入是否有唯一约束、锁或幂等键。
- [ ] H-9.3.4 失败时是否回滚或补偿。
- [ ] H-9.3.5 跨服务一致性是否有 saga、outbox、事件补偿或明确策略。

## 9.4 数据完整性

- [ ] H-9.4.1 业务不变量由数据库约束、领域逻辑或二者共同保证。
- [ ] H-9.4.2 外键、唯一约束、check constraint 是否合理。
- [ ] H-9.4.3 软删除是否影响唯一约束、查询过滤、权限检查。
- [ ] H-9.4.4 历史数据、审计字段、created/updated/deleted 时间处理正确。

---

# 10. 安全

## 10.1 输入与注入

- [ ] H-10.1.1 所有不可信输入已识别。
- [ ] H-10.1.2 使用 allowlist，而不是只依赖 denylist。
- [ ] H-10.1.3 SQL、NoSQL、shell、LDAP、XML、模板、路径、日志都不直接拼接不可信输入。
- [ ] H-10.1.4 HTML/JS/CSS/URL 输出使用上下文相关编码。
- [ ] H-10.1.5 文件路径做规范化和目录限制，防止 path traversal。

## 10.2 认证与授权

- [ ] H-10.2.1 认证在服务端执行。
- [ ] H-10.2.2 授权在每个敏感入口执行。
- [ ] H-10.2.3 不依赖前端隐藏按钮作为权限控制。
- [ ] H-10.2.4 资源 ID 访问检查 owner/tenant/role/scope。
- [ ] H-10.2.5 管理员能力、服务账号、后台任务遵循最小权限。
- [ ] H-10.2.6 多租户系统没有跨 tenant 数据泄漏。

## 10.3 Secret 与敏感数据

- [ ] G-10.3.1 secret scanner 在 CI 中运行。
- [ ] H-10.3.2 不提交 token、密码、私钥、连接串、cookie、测试真实凭证。
- [ ] H-10.3.3 secret 来自 secret manager、环境变量或安全配置中心。
- [ ] H-10.3.4 日志、错误、URL、埋点、导出文件不包含敏感信息。
- [ ] H-10.3.5 测试数据不使用真实用户 PII。

## 10.4 Session、Token、Cookie

- [ ] H-10.4.1 token/session 随机性和有效期合理。
- [ ] H-10.4.2 token 可撤销或有合理失效机制。
- [ ] H-10.4.3 Cookie 设置 Secure、HttpOnly、SameSite。
- [ ] H-10.4.4 登录、登出、权限变更、密码变更后 session 处理正确。
- [ ] H-10.4.5 CSRF 防护符合项目约定。

## 10.5 加密

- [ ] H-10.5.1 不自己实现加密算法。
- [ ] H-10.5.2 使用成熟库和安全默认配置。
- [ ] H-10.5.3 随机数使用密码学安全随机源。
- [ ] H-10.5.4 密码使用安全 password hashing，不用明文、MD5、SHA1、普通 hash。
- [ ] H-10.5.5 TLS 失败不降级到不安全连接。

## 10.6 错误与日志安全

- [ ] H-10.6.1 用户可见错误不暴露 stack trace、内部路径、SQL、secret。
- [ ] H-10.6.2 安全事件有审计日志，例如登录失败、权限失败、敏感操作。
- [ ] H-10.6.3 日志中的用户输入已处理，避免日志注入。
- [ ] H-10.6.4 安全失败默认拒绝访问。

---

# 11. 隐私与数据保护

## 11.1 数据最小化

- [ ] H-11.1.1 只收集必要数据。
- [ ] H-11.1.2 只返回调用方需要的数据字段。
- [ ] H-11.1.3 不把内部字段、权限字段、风控字段、PII 透出。
- [ ] H-11.1.4 埋点和 analytics 不包含敏感数据。

## 11.2 数据存储与传输

- [ ] H-11.2.1 敏感数据存储加密或有等价保护。
- [ ] H-11.2.2 敏感数据传输使用 TLS。
- [ ] H-11.2.3 缓存、临时文件、导出文件有过期和访问控制。
- [ ] H-11.2.4 客户端不明文存储敏感凭证。

## 11.3 合规

- [ ] H-11.3.1 是否涉及 GDPR、CCPA、HIPAA、PCI DSS、公司内部合规要求。
- [ ] H-11.3.2 是否需要用户同意、隐私政策、数据处理记录更新。
- [ ] H-11.3.3 删除、脱敏、匿名化、保留期限策略正确。
- [ ] H-11.3.4 需要法务、安全或隐私 owner review 时已邀请。

---

# 12. 依赖与供应链

## 12.1 新增依赖

- [ ] H-12.1.1 新依赖是否真的必要。
- [ ] H-12.1.2 是否能用标准库、已有依赖或更小实现替代。
- [ ] H-12.1.3 包名、作者、仓库、下载源确认可信，避免 typosquatting。
- [ ] H-12.1.4 依赖维护活跃。
- [ ] H-12.1.5 license 兼容。

## 12.2 依赖安全

- [ ] G-12.2.1 SCA 工具在 CI 中运行。
- [ ] H-12.2.2 无高危 CVE，或有例外审批和缓解方案。
- [ ] H-12.2.3 transitive dependency 风险已检查。
- [ ] H-12.2.4 lockfile 更新合理，没有异常大范围升级。
- [ ] H-12.2.5 自动依赖更新策略明确，例如 Dependabot/Renovate。

## 12.3 构建与制品

- [ ] H-12.3.1 生产制品来自受控 CI，不来自个人本地构建。
- [ ] H-12.3.2 能追踪制品对应 commit、依赖版本、构建环境。
- [ ] H-12.3.3 Docker image base image 可信且定期更新。
- [ ] H-12.3.4 CI/CD 脚本不使用未校验下载、`curl | bash`、硬编码 secret。
- [ ] H-12.3.5 必要时生成 SBOM、签名或 provenance。

---

# 13. 测试

## 13.1 测试覆盖

- [ ] H-13.1.1 核心业务逻辑有单元测试。
- [ ] H-13.1.2 跨模块、数据库、消息队列、外部服务有集成测试。
- [ ] H-13.1.3 关键用户流程有 E2E 或端到端验证。
- [ ] H-13.1.4 bug fix 有回归测试。
- [ ] H-13.1.5 边界条件和异常路径有测试。

## 13.2 测试质量

- [ ] H-13.2.1 测试验证行为，而不是只测实现细节。
- [ ] H-13.2.2 测试名说明场景、动作、期望。
- [ ] H-13.2.3 测试数据清晰，不堆无关字段。
- [ ] H-13.2.4 mock 不过度，关键集成路径有真实依赖或合理替身。
- [ ] H-13.2.5 测试不依赖执行顺序。
- [ ] H-13.2.6 测试不依赖真实当前时间、随机值、外部网络。

## 13.3 测试稳定性

- [ ] G-13.3.1 CI 测试必须通过。
- [ ] H-13.3.2 flaky test 已修复或隔离，并有 owner。
- [ ] H-13.3.3 慢测试是否需要标记、拆分或并行。
- [ ] H-13.3.4 覆盖率不应低于主分支 baseline。

## 13.4 测试可维护性

- [ ] H-13.4.1 测试 helper 不隐藏关键断言。
- [ ] H-13.4.2 fixture 可读。
- [ ] H-13.4.3 snapshot 测试没有无意义大 snapshot。
- [ ] H-13.4.4 测试失败信息能帮助定位问题。

---

# 14. 性能、扩展性与成本

## 14.1 计算复杂度

- [ ] H-14.1.1 算法复杂度合理。
- [ ] H-14.1.2 大输入下不会指数级、平方级爆炸，除非有明确上限。
- [ ] H-14.1.3 循环中没有重复昂贵计算。
- [ ] H-14.1.4 批量操作有 size limit。

## 14.2 I/O 与网络

- [ ] H-14.2.1 外部调用有 timeout。
- [ ] H-14.2.2 retry 有上限、退避、幂等保护。
- [ ] H-14.2.3 关键路径中没有不必要同步阻塞。
- [ ] H-14.2.4 批量外部调用有限流和并发控制。

## 14.3 缓存

- [ ] H-14.3.1 是否需要缓存。
- [ ] H-14.3.2 cache key 正确包含 tenant、user、locale、permission 等影响结果的维度。
- [ ] H-14.3.3 TTL 和失效策略合理。
- [ ] H-14.3.4 不缓存敏感数据，或有严格访问隔离。
- [ ] H-14.3.5 防止缓存击穿、穿透、雪崩。

## 14.4 成本

- [ ] H-14.4.1 是否增加云资源、API 调用、存储、带宽成本。
- [ ] H-14.4.2 是否有成本上限或预算报警。
- [ ] H-14.4.3 是否避免重复写入、重复任务、重复扫描。

---

# 15. 可观测性、发布与运维

## 15.1 日志

- [ ] H-15.1.1 日志足够排障。
- [ ] H-15.1.2 日志包含 request id、trace id、tenant id、业务 id 等必要上下文。
- [ ] H-15.1.3 日志不包含 secret、PII、token、密码、完整请求体。
- [ ] H-15.1.4 日志量可控。

## 15.2 Metrics 与 tracing

- [ ] H-15.2.1 新关键路径有成功率、错误率、延迟指标。
- [ ] H-15.2.2 队列、批处理、定时任务有积压和耗时指标。
- [ ] H-15.2.3 外部服务调用有依赖级别指标。
- [ ] H-15.2.4 tracing 能串起主要调用链。

## 15.3 Alert 与 dashboard

- [ ] H-15.3.1 高风险变更是否需要新报警。
- [ ] H-15.3.2 是否需要 dashboard 验证上线效果。
- [ ] H-15.3.3 报警阈值有 owner 和处理 runbook。

## 15.4 发布控制

- [ ] H-15.4.1 是否需要 feature flag。
- [ ] H-15.4.2 是否支持灰度、canary、按租户或用户分批发布。
- [ ] H-15.4.3 是否有 rollback 方案。
- [ ] H-15.4.4 发布顺序明确，例如先 migration、再后端、再前端。
- [ ] H-15.4.5 配置变更可回滚。

---

# 16. 前端专项

## 16.1 UI 与状态

- [ ] H-16.1.1 组件职责清楚。
- [ ] H-16.1.2 状态放在正确层级。
- [ ] H-16.1.3 避免不必要的全局状态。
- [ ] H-16.1.4 loading、empty、error、success 状态完整。
- [ ] H-16.1.5 表单校验和服务端校验一致。

## 16.2 可访问性

- [ ] H-16.2.1 交互元素有语义标签。
- [ ] H-16.2.2 图片有 alt 或明确装饰性处理。
- [ ] H-16.2.3 键盘可操作。
- [ ] H-16.2.4 focus 管理正确。
- [ ] H-16.2.5 颜色、对比度、错误提示可访问。

## 16.3 性能

- [ ] H-16.3.1 避免不必要 re-render。
- [ ] H-16.3.2 大列表使用分页、虚拟列表或懒加载。
- [ ] H-16.3.3 bundle size 增长可接受。
- [ ] H-16.3.4 图片、字体、第三方脚本加载合理。
- [ ] H-16.3.5 SSR/CSR/hydration 行为正确。

## 16.4 安全

- [ ] H-16.4.1 不直接渲染不可信 HTML。
- [ ] H-16.4.2 URL、redirect、iframe、postMessage 做校验。
- [ ] H-16.4.3 前端不存储长期敏感 token，除非有明确安全设计。
- [ ] H-16.4.4 权限控制不只依赖前端。

---

# 17. 后端专项

## 17.1 服务边界

- [ ] H-17.1.1 业务逻辑不堆在 route/controller。
- [ ] H-17.1.2 repository/DAO 不包含复杂业务规则。
- [ ] H-17.1.3 service 层职责清楚。
- [ ] H-17.1.4 外部服务 client 有统一错误、timeout、retry 处理。

## 17.2 幂等性

- [ ] H-17.2.1 POST/消费消息/支付/扣库存等关键操作考虑幂等。
- [ ] H-17.2.2 幂等 key 设计清楚。
- [ ] H-17.2.3 重试不会重复产生副作用。
- [ ] H-17.2.4 去重窗口和存储策略合理。

## 17.3 任务与消息

- [ ] H-17.3.1 消息 schema 兼容。
- [ ] H-17.3.2 消费者能处理重复、乱序、延迟消息。
- [ ] H-17.3.3 失败消息进入 DLQ 或有重试策略。
- [ ] H-17.3.4 任务有超时、取消、重入保护。
- [ ] H-17.3.5 定时任务不会在多实例中重复执行，或重复执行是安全的。

---

# 18. 配置、环境与基础设施

## 18.1 配置

- [ ] H-18.1.1 配置有默认值和校验。
- [ ] H-18.1.2 环境变量缺失时失败方式清楚。
- [ ] H-18.1.3 prod/staging/dev 配置差异明确。
- [ ] H-18.1.4 secret 不写在配置文件中。
- [ ] H-18.1.5 配置变更可回滚。

## 18.2 IaC 与部署

- [ ] G-18.2.1 IaC scanner 在 CI 中运行。
- [ ] H-18.2.2 权限遵循最小权限。
- [ ] H-18.2.3 安全组、防火墙、网络暴露合理。
- [ ] H-18.2.4 资源命名、tag、owner、成本中心完整。
- [ ] H-18.2.5 生产变更有审计和审批。

---

# 19. 文档与沟通

## 19.1 文档

- [ ] H-19.1.1 README 是否需要更新。
- [ ] H-19.1.2 API 文档是否需要更新。
- [ ] H-19.1.3 用户文档、帮助中心、release notes 是否需要更新。
- [ ] H-19.1.4 runbook、dashboard、报警处理说明是否需要更新。
- [ ] H-19.1.5 重要设计权衡记录在 PR/MR 或设计文档中。

## 19.2 Review 评论质量

- [ ] H-19.2.1 评论具体指出问题位置。
- [ ] H-19.2.2 评论说明原因，而不是只说“我不喜欢”。
- [ ] H-19.2.3 评论区分 blocker、should fix、nit。
- [ ] H-19.2.4 评论给出可执行建议或替代方案。
- [ ] H-19.2.5 纯个人偏好不阻塞合并。

---

# 20. AI 生成代码专项

## 20.1 AI 代码责任

- [ ] H-20.1.1 作者对 AI 生成代码负责。
- [ ] H-20.1.2 AI 生成代码逐行 review。
- [ ] H-20.1.3 引用的库、API、版本、配置真实存在。
- [ ] H-20.1.4 没有引入过时 API、弱加密、缺少授权、错误异常处理。
- [ ] H-20.1.5 关键逻辑补充测试。

## 20.2 LLM/AI 系统变更

- [ ] H-20.2.1 说明模型、prompt、工具、数据、评测集的变更。
- [ ] H-20.2.2 评估 prompt injection、越权工具调用、敏感输出。
- [ ] H-20.2.3 有输入输出过滤、审计、速率限制。
- [ ] H-20.2.4 有模型版本、评测结果、回滚方案。
- [ ] H-20.2.5 涉及用户数据时考虑隐私、合规和数据保留。

---

# 21. 可复制的短版 PR/MR Checklist

```md
## Code Review Checklist

### 0. Quality Gates
- [ ] 0.1 formatter/linter/typecheck/test 已在本地和 CI 运行
- [ ] 0.2 secret scan / dependency scan / SAST 通过，或有 owner 批准的例外
- [ ] 0.3 suppressions 有原因，例如 eslint-disable / noqa / type-ignore

### 1. Scope & Intent
- [ ] 1.1 PR 目标和背景清楚
- [ ] 1.2 没有混入无关改动
- [ ] 1.3 作者说明测试方式、风险、回滚方式

### 2. Design
- [ ] 2.1 代码放在正确模块和层级
- [ ] 2.2 没有破坏架构边界或引入循环依赖
- [ ] 2.3 没有过度设计或复制粘贴
- [ ] 2.4 对外接口、schema、事件、数据库保持兼容

### 3. Function / Method Level
- [ ] 3.1 函数只做一件主要事情
- [ ] 3.2 函数长度 < 100 行；超过需说明
- [ ] 3.3 单行 <= 120 列，由工具保证
- [ ] 3.4 圈复杂度建议 <= 10，嵌套深度建议 <= 3–4
- [ ] 3.5 参数建议 <= 5，prefer <= 3
- [ ] 3.6 返回值、错误路径、副作用清楚
- [ ] 3.7 没有隐藏全局状态或难以测试的依赖

### 4. Correctness
- [ ] 4.1 主流程正确
- [ ] 4.2 边界条件完整：null/empty/min/max/timezone/duplicates
- [ ] 4.3 并发、幂等、事务、一致性已考虑
- [ ] 4.4 错误处理完整，不吞异常

### 5. Security & Privacy
- [ ] 5.1 不可信输入已验证
- [ ] 5.2 查询、命令、HTML、路径、日志不拼接不可信输入
- [ ] 5.3 服务端执行认证和授权
- [ ] 5.4 secret、token、PII 不进入代码、日志、URL、埋点
- [ ] 5.5 Cookie/session/token/TLS/加密处理安全

### 6. Tests
- [ ] 6.1 核心逻辑有单元测试
- [ ] 6.2 数据库/API/消息/外部依赖有集成测试
- [ ] 6.3 bug fix 有回归测试
- [ ] 6.4 边界和异常路径有测试
- [ ] 6.5 测试稳定，不依赖顺序、真实时间、外部网络

### 7. Performance & Data
- [ ] 7.1 没有明显算法复杂度问题
- [ ] 7.2 没有 N+1、慢查询、大表锁、无分页全表查询
- [ ] 7.3 外部调用有 timeout/retry/限流/降级
- [ ] 7.4 缓存 key、TTL、权限隔离正确

### 8. Observability & Release
- [ ] 8.1 日志、metrics、tracing 足够排障且不泄密
- [ ] 8.2 高风险变更有 feature flag、灰度或回滚方案
- [ ] 8.3 migration、配置、部署顺序清楚

### 9. Docs
- [ ] 9.1 README/API docs/release notes/runbook 已更新或确认不需要
- [ ] 9.2 关键权衡记录在 PR 或设计文档中
```

---

# 22. 示例工具配置片段

> 以下只是示例。不同项目需要按语言、框架和团队习惯调整。

## 22.1 ESLint 示例：函数长度、行长度、复杂度、参数数量

```js
// eslint.config.js / .eslintrc.js 示例片段
export default [
  {
    rules: {
      // 单行硬上限。注意：Prettier 的 printWidth 不是硬性最大行长。
      "max-len": ["error", { "code": 120, "ignoreUrls": true, "ignoreStrings": false }],

      // 函数最长 100 行，空行和注释不计入。
      "max-lines-per-function": ["warn", {
        "max": 100,
        "skipBlankLines": true,
        "skipComments": true
      }],

      // 圈复杂度建议阈值。
      "complexity": ["warn", 10],

      // 参数数量建议阈值。
      "max-params": ["warn", 5],

      // 嵌套深度建议阈值。
      "max-depth": ["warn", 4]
    }
  }
];
```

## 22.2 Prettier 示例：格式化倾向

```json
{
  "printWidth": 100,
  "singleQuote": true,
  "trailingComma": "all"
}
```

说明：`printWidth` 是 formatter 的换行倾向，不等于“超过就失败”的硬性规则。需要硬性上限时，用 linter 的 max line length 规则。

## 22.3 Python / Ruff 示例

```toml
# pyproject.toml 示例片段
[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = [
  "E",   # pycodestyle errors
  "F",   # pyflakes
  "I",   # import sorting
  "B",   # flake8-bugbear
  "C90", # mccabe complexity
  "UP",  # pyupgrade
  "S"    # security-related rules via flake8-bandit subset
]

[tool.ruff.lint.mccabe]
max-complexity = 10
```

## 22.4 Makefile 示例：统一入口

```makefile
.PHONY: check format-check lint typecheck test security

check: format-check lint typecheck test security

format-check:
	# replace with project command
	prettier . --check

lint:
	# replace with project command
	npm run lint

typecheck:
	# replace with project command
	npm run typecheck

test:
	# replace with project command
	npm test

security:
	# replace with project command
	gitleaks detect --no-git --redact
```

---

# 23. Reviewer 快速判断：哪些交给工具，哪些必须人工看

## 23.1 优先交给工具

- [ ] 行长度。
- [ ] 函数长度。
- [ ] 文件长度。
- [ ] import 顺序。
- [ ] 未使用变量、未使用 import。
- [ ] 基础类型错误。
- [ ] 简单复杂度阈值。
- [ ] 基础安全规则。
- [ ] 依赖漏洞。
- [ ] secret 泄漏。
- [ ] 测试是否通过。
- [ ] 覆盖率是否下降。

## 23.2 必须人工判断

- [ ] 这个设计是否应该存在。
- [ ] 代码是否放在正确层级。
- [ ] 业务规则是否正确。
- [ ] 权限边界是否正确。
- [ ] 数据一致性和并发是否正确。
- [ ] 异常路径是否符合业务预期。
- [ ] 测试是否真的测到了行为。
- [ ] 日志和指标是否能支撑生产排障。
- [ ] 发布和回滚是否安全。
- [ ] 长期维护成本是否可接受。

---

# 24. 参考资料

- Google Engineering Practices — What to look for in a code review: https://google.github.io/eng-practices/review/reviewer/looking-for.html
- Google Engineering Practices — The Standard of Code Review: https://google.github.io/eng-practices/review/reviewer/standard.html
- OWASP Secure Code Review Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html
- OWASP Secure Coding Practices Checklist: https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/stable-en/02-checklist/05-checklist
- Prettier Options — printWidth: https://prettier.io/docs/options
- ESLint max-len: https://eslint.org/docs/latest/rules/max-len
- ESLint max-lines-per-function: https://eslint.org/docs/latest/rules/max-lines-per-function
- ESLint complexity: https://eslint.org/docs/latest/rules/complexity
- ESLint max-params: https://eslint.org/docs/latest/rules/max-params
- Ruff Configuration: https://docs.astral.sh/ruff/configuration/
- Ruff Rules: https://docs.astral.sh/ruff/rules/
