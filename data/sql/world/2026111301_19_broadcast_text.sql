-- tw-mod-zhcn 迁移，由 tools/sync.py 生成，勿手改
-- 来源：BluetomatoBo/tortoise-wow@95dac49bee20a6744a34c9deac38146cd5c9e854 sql/wip_updates/broadcast_text.sql（blob d0c0d190bab0b87582524ed8b1c21ea36547d300）
-- 语句数：2
INSERT INTO `broadcast_text` (`entry`, `male_text`, `female_text`, `chat_type`) VALUES (8900001, 'I can only train those who already know the trade.', '', 0) ON DUPLICATE KEY UPDATE `male_text` = VALUES(`male_text`);
INSERT INTO `locales_broadcast_text` (`entry`, `male_text_loc4`) VALUES (8900001, '我只能训练已经掌握本行技艺的人。') ON DUPLICATE KEY UPDATE `male_text_loc4` = VALUES(`male_text_loc4`);
