#!/usr/bin/env python3
"""从 BluetomatoBo/tortoise-wow 同步简中汉化 SQL，转成本模块的迁移文件。

用法：
    tools/sync.py                 # 比对：列出上游与 sources.lock.json 不同的文件，不写
    tools/sync.py apply           # 写入：生成新迁移、更新 sources.lock.json 与 SOURCES.md
    tools/sync.py apply --ref <commit>   # 指定上游提交（默认分支最新）
    tools/sync.py verify          # 不联网：用 mangosd 的切分规则回读 data/sql/world/ 里每个迁移（CI 跑这个）

为什么要转换，而不是原样拷贝：mangosd 的迁移执行器（AutoUpdater::ExecuteUpdate）
自己切分语句，规则与 MySQL 不同：
  - 单行注释里出现 `/*` 也会进入块注释，之后整个文件被吞掉（上游多个文件的注释里有
    `locales/Chinese/*.sql`）；
  - 引号内 `\\'` 会被当成转义，导致之后的引号奇偶全部错位；
  - 字符串里的换行被替换成空格。
所以这里用 MySQL 语义解析一遍，去掉注释与 `SET NAMES`，把字符串重新编码成
不含反斜杠-引号组合的形式，每条语句一行；再用 mangosd 的切分规则回读校验。
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

REPO = "BluetomatoBo/tortoise-wow"
BRANCH = "1181-zhcn-localization"
SRC_DIR = "sql/wip_updates"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "sql", "world")
LOCK = os.path.join(ROOT, "sources.lock.json")
SOURCES_MD = os.path.join(ROOT, "SOURCES.md")

# 执行顺序。整体覆盖的翻译先跑，带条件的修正其后，按值替换的繁简清理最后。
ORDER = [
    # 1. 整体写入的翻译（upsert）
    "locales_item.sql",
    "locales_spell.sql",
    "locales_creature.sql",
    "locales_gameobject.sql",
    "locales_page_text.sql",
    "locales_points_of_interest.sql",
    "locales_broadcast_text.sql",
    "locales_quest.sql",
    "locales_quest_details.sql",
    "locales_quest_objectives.sql",
    "locales_quest_rewards.sql",
    "locales_quest_extra.sql",
    "locales_quest_fixes.sql",
    "locales_quest_proper_nouns.sql",
    # 2. 只在缺失时补（INSERT ... WHERE NOT EXISTS）
    "locales_quest_live_text.sql",
    "locales_quest_new_content.sql",
    "locales_quest_new_content_mt.sql",
    "locales_new_entities.sql",
    # 3. 文本表与问候语
    "broadcast_text.sql",
    "npc_text.sql",
    "gossip_menu.sql",
    "creature_template.sql",
    "quest_greeting.sql",
    "npc_trainer_greeting.sql",
    "script_texts.sql",
    "chat_channels.sql",
    "mangos_string.sql",
    "pet_name_generation.sql",
    # 4. 带条件的修正（WHERE entry = ? AND 旧值 = ?）
    "locales_dbc_official.sql",
    "locales_official_wowhead.sql",
    "locales_name_fixes.sql",
    "locales_item_desc_fixes.sql",
    "locales_quest_missing_text.sql",
    # 5. 繁体 / 台湾用词清理（按值替换，必须最后）
    "locales_simplified_cleanup.sql",
]
# 与汉化无关、或没有可执行语句的文件
EXCLUDE = {
    "2026-10-16_survival_trainer_duplicate_rollback.sql",  # 作者服务器上的刷怪点回滚
    "spell_affect_missing38.sql",  # 只有说明，无语句
}


# ---------- 上游读取 ----------

def gh_json(path):
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def resolve_ref(ref):
    return gh_json(f"repos/{REPO}/commits/{ref}")["sha"]


def list_files(commit):
    items = gh_json(f"repos/{REPO}/contents/{SRC_DIR}?ref={commit}")
    return {i["name"]: i["sha"] for i in items if i["name"].endswith(".sql")}


def fetch(commit, name):
    """取文件原始字节；raw 域名不稳时重试，最后改走 gh api。"""
    url = f"https://raw.githubusercontent.com/{REPO}/{commit}/{SRC_DIR}/{name}"
    data = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            break
        except OSError:
            time.sleep(2)
    if data is None:
        data = subprocess.run(
            ["gh", "api", "-H", "Accept: application/vnd.github.raw",
             f"repos/{REPO}/contents/{SRC_DIR}/{name}?ref={commit}"],
            check=True, capture_output=True).stdout
    # git blob sha 校验，保证拿到的就是锁定的那一版
    blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    return data.decode("utf-8"), blob


# ---------- SQL 解析（MySQL 语义） ----------

STMT_START = re.compile(r"(UPDATE|INSERT|REPLACE|DELETE)\s+(IGNORE\s+)?(INTO\s+)?`")


def tokenize(sql, warn):
    """切成语句；每条语句是 token 列表：('s', 字符串值) 或 ('t', 原文片段)。注释丢弃。

    上游个别语句是坏的：缺结尾分号，或字符串没闭合（被截断）。行首出现新语句的开头
    就视为上一条结束；若此时还在字符串里，上一条整条丢弃并记警告。"""
    stmts, cur, buf = [], [], []
    i, n = 0, len(sql)

    def flush_text():
        if buf:
            cur.append(("t", "".join(buf)))
            buf.clear()

    def has_content():
        return any(k == "s" or v.strip() for k, v in cur)

    def at_stmt_start(pos):
        return (pos == 0 or sql[pos - 1] == "\n") and STMT_START.match(sql, pos)

    while i < n:
        c = sql[i]
        if at_stmt_start(i) and (has_content() or "".join(buf).strip()):
            flush_text()
            warn.append(f"补上缺失的分号：{render(cur, [])[:60]}")
            stmts.append(cur)
            cur = []
        # 与 mangosd 一致：`--` 后不要求空白（上游有 `--（…）` 这种写法）
        if c == "-" and sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j < 0:
                raise ValueError("未闭合的块注释")
            i = j + 2
            buf.append(" ")
            continue
        if c in "'\"":
            q = c
            j, val, broken = i + 1, [], False
            while True:
                if j >= n:
                    raise ValueError("未闭合的字符串")
                ch = sql[j]
                if ch == "\n" and STMT_START.match(sql, j + 1):
                    broken = True
                    break
                if ch == "\\":
                    nxt = sql[j + 1]
                    val.append({"n": "\n", "r": "\r", "t": "\t", "0": "\0"}.get(nxt, nxt))
                    j += 2
                    continue
                if ch == q:
                    if j + 1 < n and sql[j + 1] == q:
                        val.append(q)
                        j += 2
                        continue
                    break
                val.append(ch)
                j += 1
            if broken:
                flush_text()
                warn.append(f"丢弃字符串未闭合的语句：{render(cur, [])[:60]}")
                cur = []
                i = j + 1
                continue
            flush_text()
            cur.append(("s", "".join(val)))
            i = j + 1
            continue
        if c == ";":
            flush_text()
            if has_content():
                stmts.append(cur)
            cur = []
            i += 1
            continue
        buf.append(c)
        i += 1
    flush_text()
    if has_content():
        stmts.append(cur)
    return stmts


def encode_str(v, warn):
    """编码成 MySQL 与 mangosd 切分器都认同的字符串字面量。

    mangosd 只把「反斜杠 + 引号」当转义，所以反斜杠紧贴引号或结尾时会错位：
    这种反斜杠直接去掉；其余反斜杠（如书页图片路径 Interface\\Pictures）照常转义。
    换行写成 \\n 转义（字面换行会被 mangosd 换成空格）。"""
    if "\0" in v:
        raise ValueError("字符串含 NUL")
    out = []
    for idx, ch in enumerate(v):
        if ch == "\\":
            nxt = v[idx + 1] if idx + 1 < len(v) else "'"
            if nxt == "'":
                warn.append(f"去掉引号前的反斜杠：{v[:40]!r}")
                continue
            out.append("\\\\")
        elif ch == "'":
            out.append("''")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return "'" + "".join(out) + "'"


def render(stmt, warn):
    out = []
    for k, v in stmt:
        out.append(encode_str(v, warn) if k == "s" else re.sub(r"\s+", " ", v))
    return re.sub(r"\s+", " ", "".join(out)).strip() + ";"


def convert(sql):
    warn, lines = [], []
    for st in tokenize(sql, warn):
        line = render(st, warn)
        if re.match(r"^SET\s+NAMES\b", line, re.I):
            continue
        if re.match(r"^(DROP|TRUNCATE|ALTER|CREATE)\b", line, re.I):
            raise ValueError(f"不允许的语句：{line[:80]}")
        lines.append(line)
    return lines, warn


# ---------- mangosd 切分规则（照抄 AutoUpdater::ExecuteUpdate） ----------

def split_like_mangosd(s):
    queries, cur = [], []
    ss = None
    cs = None
    n = len(s)
    i = 0
    while i < n:
        ch = s[i]
        if ch in "\r\n":
            if ch == "\n":
                cur.append(" ")
            if cs == "single":
                cs = None
            i += 1
            continue
        if ch == "/":
            if cs == "multi" and i > 0 and s[i - 1] == "*":
                cs = None
                i += 1
                continue
            if i < n - 1 and ss is None and s[i + 1] == "*":
                cs = "multi"
                i += 1
                continue
        if cs:
            i += 1
            continue
        if ch == "-" and i < n - 1 and ss is None and s[i + 1] == "-":
            cs = "single"
            i += 1
            continue
        if ch == "'":
            if ss is None:
                ss = "'"
            elif ss == "'" and s[i - 1] != "\\":
                ss = None
        if ch == '"':
            if ss is None:
                ss = '"'
            elif ss == '"' and s[i - 1] != "\\":
                ss = None
        cur.append(ch)
        if ch == ";" and ss is None:
            queries.append("".join(cur))
            cur = []
        i += 1
    rest = "".join(cur)
    if rest.strip():
        queries.append(rest)
    return queries, ss


def verify(text, lines):
    got, ss = split_like_mangosd(text)
    got = [g.strip() for g in got if g.strip()]
    if ss is not None or got != lines:
        raise ValueError(f"mangosd 切分结果与预期不符（{len(got)} vs {len(lines)} 条）")


# ---------- 主流程 ----------

def load_lock():
    if os.path.exists(LOCK):
        with open(LOCK, encoding="utf-8") as f:
            return json.load(f)
    return {"repo": REPO, "branch": BRANCH, "syncs": [], "files": {}}


def next_prefix(lock):
    today = datetime.date.today().strftime("%Y%m%d")
    same = [s for s in lock["syncs"] if s["prefix"].startswith(today)]
    return f"{today}{len(same) + 1:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", default="check", choices=["check", "apply", "verify"])
    ap.add_argument("--ref", default=BRANCH)
    a = ap.parse_args()

    if a.mode == "verify":
        bad = 0
        for name in sorted(os.listdir(OUT_DIR)):
            text = open(os.path.join(OUT_DIR, name), encoding="utf-8").read()
            lines = [l for l in text.split("\n") if l and not l.startswith("--")]
            try:
                verify(text, lines)
            except ValueError as e:
                print(f"✗ {name}: {e}")
                bad += 1
        print(f"{'✗' if bad else '✓'} {len(os.listdir(OUT_DIR))} 个迁移，{bad} 个与 mangosd 切分不符")
        sys.exit(1 if bad else 0)

    commit = resolve_ref(a.ref)
    upstream = list_files(commit)
    lock = load_lock()
    known = set(ORDER) | EXCLUDE
    unknown = sorted(set(upstream) - known)
    if unknown:
        sys.exit(f"上游出现未分类的文件，先在 ORDER 或 EXCLUDE 里归类：{unknown}")
    gone = [f for f in ORDER if f not in upstream]
    if gone:
        print(f"注意：上游已删除 {gone}（已执行的迁移不会撤销）")

    changed = [f for f in ORDER if f in upstream and lock["files"].get(f, {}).get("blob") != upstream[f]]
    print(f"上游 {REPO}@{commit[:7]}；上次同步 {lock['syncs'][-1]['commit'][:7] if lock['syncs'] else '无'}")
    if not changed:
        print("没有变化。")
        return
    # 改了某个文件，排在它之后的修正与清理也要重跑，否则会被新翻译盖掉
    first = min(ORDER.index(f) for f in changed)
    emit = [f for f in ORDER[first:] if f in upstream]
    print("有变化：" + ", ".join(changed))
    print("将生成：" + ", ".join(emit))
    if a.mode != "apply":
        return

    prefix = next_prefix(lock)
    # 先全部取回并转换，任何一个出错都不写盘
    pending = []
    for idx, name in enumerate(emit, 1):
        sql, blob = fetch(commit, name)
        if blob != upstream[name]:
            sys.exit(f"{name} 内容与 blob {upstream[name]} 不符")
        lines, warn = convert(sql)
        out_name = f"{prefix}_{idx:02d}_{name[:-4]}.sql"
        header = [
            "-- tw-mod-zhcn 迁移，由 tools/sync.py 生成，勿手改",
            f"-- 来源：{REPO}@{commit} {SRC_DIR}/{name}（blob {blob}）",
            f"-- 语句数：{len(lines)}",
        ]
        text = "\n".join(header + lines) + "\n"
        verify(text, lines)
        pending.append((out_name, name, blob, lines, text, warn))

    os.makedirs(OUT_DIR, exist_ok=True)
    generated = []
    for out_name, name, blob, lines, text, warn in pending:
        with open(os.path.join(OUT_DIR, out_name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        if warn:
            print(f"  {name}: {len(warn)} 处修正（例：{warn[0]}）")
        lock["files"][name] = {"blob": blob, "commit": commit, "migration": out_name}
        generated.append((out_name, name, blob, len(lines)))
        print(f"  {out_name}  {len(lines)} 条")

    lock["syncs"].append({
        "prefix": prefix,
        "commit": commit,
        "date": datetime.date.today().isoformat(),
        "migrations": [g[0] for g in generated],
    })
    with open(LOCK, "w", encoding="utf-8") as f:
        json.dump(lock, f, ensure_ascii=False, indent=2)
        f.write("\n")

    entry = [f"\n## {prefix}（{datetime.date.today().isoformat()}）\n",
             f"上游 `{REPO}@{commit}`（分支 `{BRANCH}`）\n",
             "| 迁移 | 来源文件 | blob | 语句数 |", "| --- | --- | --- | --- |"]
    entry += [f"| `{o}` | `{n}` | `{b[:12]}` | {c} |" for o, n, b, c in generated]
    with open(SOURCES_MD, "a", encoding="utf-8") as f:
        f.write("\n".join(entry) + "\n")


if __name__ == "__main__":
    main()
