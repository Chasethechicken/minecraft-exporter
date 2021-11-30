# minecraft-exporter

This is a Prometheus Minecraft exporter.
This exporter reads minecrafts nbt files, the advancements files and can optionally connect via RCON to your minecraft server.

to use it mount your world to /world in the container

rcon connection is used to get online Players 

to enable rcon on your minecraft server add the following to the server.properties file:

```
broadcast-rcon-to-ops=false
rcon.port=25575
rcon.password=Password
enable-rcon=true
```

The RCON Module is only enabled if `RCON_HOST` and `RCON_PASSWORD` is set


# Usage

```
docker run -e RCON_HOST=127.0.0.1 \
	   -e RCON_PORT=25575 \
	   -e RCON_PASSWORD="Password" \
	   -p 8000:8000 \
	   -v /path/to/minecraft/server/world:/world \
	   minecraft_exporter
```

# Metrics
The metrics exported can be broken up into 3 categories which come from 4 sources.

| Source | Category |
| ------ | -------- |
| world/advancements | Player Advancements |
| world/playerdata | Player Specific Data | 
| world/stats | Game stats per player |
| rcon | Player Specific Data |

## Advancement Metrics

```
minecraft_advancement_data_version_total
minecraft_advancement_story_count_total
minecraft_advancement_nether_count_total
minecraft_advancement_end_count_total
minecraft_advancement_adventure_count_total
minecraft_advancement_husbandry_count_total
minecraft_advancement_recipe_count_total
minecraft_advancement_other_count_total
```

## Player Metrics

```
minecraft_score
minecraft_xp_total
minecraft_current_level
minecraft_health
minecraft_food_level
minecraft_food_saturation_level
minecraft_food_exhaustion_level
minecraft_game_type
minecraft_dimension
```

## Stats Metrics

```
minecraft_blocks_mined_total
minecraft_items_broken_total
minecraft_items_crafted_total
minecraft_items_used_total
minecraft_items_picked_up_total
minecraft_items_dropped_total
minecraft_entities_killed_total
minecraft_entities_killed_by_total
minecraft_custom_total
minecraft_distance_traveled_cm_total
minecraft_interactions_total
minecraft_damage_total
```

### Minecraft Custom

```
custom_stat=minecraft:deaths
custom_stat=minecraft:total_world_time
custom_stat=minecraft:play_time
custom_stat=minecraft:jump
custom_stat=minecraft:sneak_time
custom_stat=minecraft:time_since_death
custom_stat=minecraft:time_since_rest
custom_stat=minecraft:leave_game
```

## RCON Metrics

(only exported if RCON is configured)

```
minecraft_player_online
```
