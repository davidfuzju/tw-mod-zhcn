# tw-mod-zhcn

Tortoise-WoW 简中本地化模块（只带数据）。仓 `github.com/davidfuzju/tw-mod-zhcn`（public），本地嵌套 clone 在 `~/Workspaces/tokendivers/projects/tw-mod-zhcn/`。由 `davidfuzju/tortoise-deploy` 编进镜像，部署在 `davidfuzju/tortoise`。

| 路径 | 内容 |
| --- | --- |
| `data/sql/world/` | 迁移，**全部由 `tools/sync.py` 生成，不手改** |
| `tools/sync.py` | 从 BluetomatoBo/tortoise-wow 拉 `sql/wip_updates/`、转换、记录版本 |
| `SOURCES.md` / `sources.lock.json` | 每次同步的上游提交与文件 blob（人读 / 机读） |
| `src/tw-mod-zhcn.cpp` | 空壳脚本；有 `src/` 核心才会识别模块 |
| `tw-mod-zhcn.cmake` | 把迁移装到 `${CMAKE_INSTALL_PREFIX}/modules/tw-mod-zhcn/data/sql/world` |

## 规则

- 迁移按内容哈希记账：已发布的文件一改就会被当成新迁移再执行一遍。更新只能 `tools/sync.py apply` 生成新文件。
- mangosd 自己切分 SQL（`AutoUpdater::ExecuteUpdate`），与 MySQL 不同：单行注释里的 `/*` 会吞掉后续全部内容，反斜杠紧贴引号会让引号错位，字面换行变空格。生成的文件因此无注释体（只有头三行 `--`）、一行一句、换行写 `\n`；`sync.py` 写盘前用同样的切分规则回读校验。
- 迁移里的语句必须可重复执行（upsert / 条件更新 / `INSERT IGNORE`），`sync.py` 拒绝 `DROP` / `ALTER` / `CREATE` / `TRUNCATE`。
- 改了转换规则后，用一份真实世界库（上游 `tortoise-database` 镜像 + 核心迁移）逐句执行新生成的文件，确认无报错再发布。

## 发布

提交推到 `main` 后，`davidfuzju/tortoise-deploy` 的每日构建发现新提交会自动重建镜像；急用可以在那边手动触发 `Build and push Docker images`。
