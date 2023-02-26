create table estimate_enemy_units_with_seconds (
    game_seconds int(11) not null default -1 comment '游戏进行时间的秒数'
    unit_count text default null comment '敌方单位的数量'
)