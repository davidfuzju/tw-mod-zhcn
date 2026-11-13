-- tw-mod-zhcn 迁移，由 tools/sync.py 生成，勿手改
-- 来源：BluetomatoBo/tortoise-wow@95dac49bee20a6744a34c9deac38146cd5c9e854 sql/wip_updates/gossip_menu.sql（blob 51f9bfa9eb153be0521165566f61650e4aa0edbb）
-- 语句数：4
INSERT IGNORE INTO `gossip_menu` (`entry`, `text_id`) VALUES (8900001, 8900001);
INSERT IGNORE INTO `gossip_menu` (`entry`, `text_id`) VALUES (18983, 8900001), (62403, 8900001), (62962, 8900001);
INSERT IGNORE INTO `gossip_menu` (`entry`, `text_id`) VALUES (1282, 8900001);
UPDATE `gossip_menu` m LEFT JOIN `npc_text` t ON t.ID = m.text_id SET m.text_id = 8900001 WHERE t.ID IS NULL;
