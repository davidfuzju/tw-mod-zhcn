#!/bin/bash
# 在一份真实的世界库上执行本模块的迁移，任何 ERROR 都判失败。CI 跑它；本机跑需要 docker 且给容器 ≥ 2 GB 内存。
#   tools/db-test.sh
# 步骤：用 tortoise-database 镜像建库（base 数据）→ 套上与镜像同一提交的核心迁移（mangosd 启动时会做的事）
#       → 按文件名顺序执行 data/sql/world/ 两遍（第二遍验证可重复执行）→ 打印中文覆盖率前后对比。
set -euo pipefail
IMAGE=${IMAGE:-ghcr.io/davidfuzju/tortoise-database:zhcn}
NAME=tw-mod-zhcn-db-test
cd "$(dirname "$0")/.."
work=$(mktemp -d)
cleanup() { docker rm -f -v "$NAME" >/dev/null 2>&1 || true; rm -rf "$work"; }
trap cleanup EXIT

docker pull -q "$IMAGE" >/dev/null
docker run -d --name "$NAME" \
  --health-cmd tortoise-healthcheck --health-interval 5s --health-retries 1000 \
  -e TORTOISE_DEPLOY_VERSION=1 -e MARIADB_ROOT_PASSWORD=ci -e MARIADB_PASSWORD=ci \
  -e TORTOISE_PROCESS_CUSTOM_SQL=0 "$IMAGE" >/dev/null
echo "等待建库…"
for _ in $(seq 360); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' "$NAME")" = healthy ] && break
  [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" = true ] || { docker logs --tail 30 "$NAME"; exit 1; }
  sleep 5
done
[ "$(docker inspect -f '{{.State.Health.Status}}' "$NAME")" = healthy ] || { echo "建库超时"; exit 1; }

sql() { docker exec -i "$NAME" mariadb -uroot -pci --default-character-set=utf8mb4 --force "$@"; }

# 核心迁移：与镜像同一提交；出错只报告（mangosd 执行它们时也不因单句出错而停）
rev=$(docker image inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$IMAGE")
echo "核心提交 $rev"
git clone -q --filter=blob:none --no-checkout https://github.com/tortoise-wow/tortoise-wow.git "$work/core"
git -C "$work/core" sparse-checkout set --no-cone 'sql/database_updates/'
git -C "$work/core" checkout -q "$rev"
core_err=0
for f in $(find "$work/core/sql/database_updates" -maxdepth 2 -name '*.sql' -not -path '*/character/*' | awk -F/ '{print $NF"\t"$0}' | LC_ALL=C sort | cut -f2); do
  n=$(sql tw_world < "$f" 2>&1 | grep -c '^ERROR' || true)
  core_err=$((core_err + n))
done
echo "核心迁移执行完，ERROR $core_err 条（仅报告）"

coverage() {
  sql -N tw_world <<'SQL'
SELECT CONCAT('任务缺中文 ', COUNT(*)) FROM quest_template q LEFT JOIN locales_quest l USING(entry) WHERE l.entry IS NULL OR l.Title_loc4='';
SELECT CONCAT('生物缺中文 ', COUNT(*)) FROM creature_template c LEFT JOIN locales_creature l USING(entry) WHERE l.entry IS NULL OR l.name_loc4='';
SELECT CONCAT('物品缺中文 ', COUNT(*)) FROM item_template i LEFT JOIN locales_item l USING(entry) WHERE l.entry IS NULL OR l.name_loc4='';
SELECT CONCAT('系统消息有中文 ', SUM(content_loc4 IS NOT NULL AND content_loc4<>'')) FROM mangos_string;
SQL
}
echo "--- 执行前"; coverage

fail=0
for pass in 1 2; do
  for f in data/sql/world/*.sql; do
    out=$(sql tw_world < "$f" 2>&1 || true)
    if printf '%s' "$out" | grep -q '^ERROR'; then
      echo "✗ 第 $pass 遍 $(basename "$f")："; printf '%s\n' "$out" | grep '^ERROR' | head -5
      fail=1
    fi
  done
done
echo "--- 执行后"; coverage
[ $fail = 0 ] && echo "✓ 两遍执行都没有 ERROR"
exit $fail
