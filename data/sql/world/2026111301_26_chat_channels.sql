-- tw-mod-zhcn 迁移，由 tools/sync.py 生成，勿手改
-- 来源：BluetomatoBo/tortoise-wow@95dac49bee20a6744a34c9deac38146cd5c9e854 sql/wip_updates/chat_channels.sql（blob 361baacbc406b764777de1ccdefa2755b2e3e836）
-- 语句数：7
UPDATE `chat_channels` SET `name_loc4` = '综合 - %s', `shortcut_loc4` = '综合' WHERE `id` = 1;
UPDATE `chat_channels` SET `name_loc4` = '交易 - %s', `shortcut_loc4` = '交易' WHERE `id` = 2;
UPDATE `chat_channels` SET `name_loc4` = '本地防务 - %s', `shortcut_loc4` = '本地防务' WHERE `id` = 22;
UPDATE `chat_channels` SET `name_loc4` = '世界防务', `shortcut_loc4` = '世界防务' WHERE `id` = 23;
UPDATE `chat_channels` SET `name_loc4` = '寻求组队', `shortcut_loc4` = '寻求组队' WHERE `id` = 24;
UPDATE `chat_channels` SET `name_loc4` = '公会招募 - %s', `shortcut_loc4` = '公会招募' WHERE `id` = 25;
UPDATE `chat_channels` SET `name_loc4` = '世界', `shortcut_loc4` = '世界' WHERE `id` = 27;
