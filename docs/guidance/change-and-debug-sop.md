# 固定作业规程:改代码 / 排查问题前必读(L3)

> 这不是某个任务的一次性计划(那属于 `docs/plans/`),而是**每次动手前照走的固定流程**。
> 对齐 Harness Engineering:先建上下文 → 在约束内改 → 结果导向验收 → 用 Problem Taxonomy 归因。
> 所有命令在仓库根、`.venv` 环境下执行。

## 阶段 0:定位上下文(先读,再动手)

按"我要做什么"决定读哪份 L3 文档,≤3 跳:

1. 读根 `ARCHITECTURE.md` 确认涉及哪个模块、有没有踩到架构不变式。
2. 按需读 `docs/reference/`:
   - 改数据形态 → `reference/data-contracts.md`
   - 改主题/研报路由 → `reference/theme-pool-and-reports.md`
   - 改目录/依赖边界 → `reference/repo-layout.md`
   - 改/加校验 → `reference/harness-checks.md`
3. 需要操作步骤 → 对应 `docs/guidance/*`。
4. 复杂改动 → 从 `docs/plans/TEMPLATE.md` 开一份 ExecPlan,放 `docs/plans/proposal/`。

## 阶段 1:先复现基线(排查问题时必做)

- 先跑一遍,确认当前**可观测**状态,别凭猜测改:
  ```bash
  python -m pytest -q
  python scripts/run_harness.py
  ```
- 记录基线(几个用例过、harness 有哪些 warn),作为改动前后的对照。

## 阶段 2:在约束内修改(不变式红线)

改动不得违反(全部由 harness 守护,见 `reference/harness-checks.md`):

- `loop_os/*` 不得 `import external/*`;external 只经 `providers/*` 访问。
- 改状态必须走 `loop_os/state_machine/*` 且有 evidence/claim 背书。
- 保留技能只有 `industry-chain-analysis`,禁止复活 `china-stock-*`。
- 阈值/开关优先进 `config/*.json`(config-driven + 内置 fallback),不要硬编码。
- 密钥不得进仓库。

## 阶段 3:结果导向验收(缺一不可)

```bash
python -m pytest -q                 # 全部 PASS,0 skipped
python scripts/run_harness.py       # 无 error(所有 check 为 ok/warn)
```
提交前跑 pre-commit hook(见 `scripts/install_hooks.sh` 安装),退出码必须为 0。
若开了 ExecPlan,同步更新其进度日志与验收勾选项(活文档)。

## 阶段 4:卡住时——按 Problem Taxonomy 归因(6 类)

不要盲目重试。先判断属于哪类,对症处理:

| 分类 | 症状 | 处理 |
|---|---|---|
| Navigation Gap 导航缺失 | 不知道该改哪 / 进错目录 | 回阶段 0,补/修 `docs/AGENTS.md` 或 reference 入口 |
| Doc Drift 文档漂移 | 按文档做却出错 | 以代码为准,顺手修过时文档(repo 是唯一事实源) |
| Verification Ambiguity 验证歧义 | 不知道跑什么命令验证 | 用阶段 3 的固定命令;必要时在 reference/guidance 补验证矩阵 |
| Guardrail Hit 护栏命中 | hook/harness 拦下问题 | 读报错→修复→重跑(自愈闭环),这是预期行为 |
| Guardrail Noise 护栏噪音 | hook 触发但提示不清、反复卡 | 改校验的报错文案,让它"报错即指导" |
| Env Drift 环境漂移 | 非代码问题(环境不稳)阻塞 | 先修环境可复现性(`.venv`、环境变量),不要改业务代码 |

## 完成清单

- [ ] 动手前已读相关 L0/L3 文档
- [ ] 已记录并对比基线
- [ ] 未违反架构不变式
- [ ] pytest 全绿 + harness 无 error + hook 退出 0
- [ ] 若有 ExecPlan,进度已更新;若发现文档漂移,已顺手修正
