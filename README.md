# tw-mod-zhcn

[Tortoise-WoW](https://github.com/tortoise-wow/tortoise-wow) 的简体中文本地化模块。只带数据：编进 mangosd 后，启动时由核心的迁移机制把 `data/sql/world/` 里的汉化写进世界库，不改核心源码。

汉化内容来自 [BluetomatoBo/tortoise-wow](https://github.com/BluetomatoBo/tortoise-wow) 分支 `1181-zhcn-localization` 的 `sql/wip_updates/`（AGPL-3.0）。本仓只做格式转换，翻译工作归原作者。每次同步的上游提交与文件版本见 [`SOURCES.md`](SOURCES.md)。

## 内容

| 类别 | 表 |
| --- | --- |
| 物品、法术、生物、物件、书页、兴趣点、广播文本的中文 | `locales_item` / `locales_spell` / `locales_creature` / `locales_gameobject` / `locales_page_text` / `locales_points_of_interest` / `locales_broadcast_text` |
| 任务标题、描述、目标、交还文本，含乌龟服新内容 | `locales_quest` |
| 服务器系统消息、聊天频道名、问候语、脚本台词 | `mangos_string` / `chat_channels` / `quest_greeting` / `npc_trainer_greeting` / `script_texts` |
| 术士宠物名字音节 | `pet_name_generation` |
| 让无菜单 NPC 显示中文问候 | `gossip_menu` / `npc_text` / `broadcast_text` / `creature_template`（自有 ID 段 8900001） |
| 官方译名校对、繁体与台湾用词清理 | 以上各表的条件更新 |

中文只发给语言为简体中文（`loc4`）的客户端，英文客户端不受影响。

## 安装

把仓库放进核心的 `modules/tw-mod-zhcn/`，带模块编译：

```bash
git clone https://github.com/davidfuzju/tw-mod-zhcn.git modules/tw-mod-zhcn
cmake -S . -B build -DMODULE_TW_MOD_ZHCN=static   # 其余选项照旧
```

`Database.AutoUpdate.Enabled = 1` 且 `Database.AutoUpdate.AllowedModules` 为 `all` 或包含 `tw-mod-zhcn` 时，mangosd 启动会自动执行迁移。保持 `Database.AutoUpdate.SortByName = 1`，迁移按文件名顺序执行。

## 同步上游

```bash
tools/sync.py           # 比对：列出上游有变化的文件
tools/sync.py apply     # 生成新迁移，追加 SOURCES.md / sources.lock.json
```

- 迁移文件名 `<YYYYMMDDNN>_<序号>_<来源文件>.sql`，每次同步一个前缀；已发布的迁移不再改动，更新一律生成新文件。
- 某个来源文件变了，排在它之后的修正与繁简清理会一起重新生成，避免新翻译盖掉清理结果。
- 上游新增的文件要先在 `tools/sync.py` 的 `ORDER` 或 `EXCLUDE` 里归类，否则同步会停下。

转换时做的处理（原因见 `tools/sync.py` 开头）：去掉注释和 `SET NAMES`；字符串重新编码，换行写成 `\n`；上游个别被截断、缺分号的语句丢弃或补齐，并在输出里列出。

## 许可

AGPL-3.0，与来源一致。
