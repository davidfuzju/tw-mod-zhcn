-- tw-mod-zhcn 迁移，由 tools/sync.py 生成，勿手改
-- 来源：BluetomatoBo/tortoise-wow@95dac49bee20a6744a34c9deac38146cd5c9e854 sql/wip_updates/creature_template.sql（blob f12a8fc2a5c2e7a134e0ae372e1b0532c938e6ee）
-- 语句数：1
UPDATE `creature_template` SET `gossip_menu_id` = 8900001 WHERE `gossip_menu_id` = 0 AND `npc_flags` <> 0;
