# minecraft-exporter

This is a Prometheus Minecraft exporter.
This exporter reads minecrafts nbt files, the advancements files and can optionally connect via RCON to your minecraft server.

to use it mount your world to /world in the container

rcon connection is used to get online Players 
On Forge Servers enable FORGE_SERVER to get tps information

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
	   -e FORGE_SERVER="True" \
	   -e DYNMAP_ENABLED="True" \
	   -p 8000:8000 \
	   -v /opt/all_the_mods_3/world:/world \
	   joshi425/minecraft_exporter
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
minecraft_advancement_data_version
minecraft_advancement_story_count
minecraft_advancement_nether_count
minecraft_advancement_end_count
minecraft_advancement_adventure_count
minecraft_advancement_husbandry_count
minecraft_advancement_recipe_count
minecraft_advancement_other_count
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
minecraft_custom
minecraft_distance_traveled_cm_total
minecraft_interactions_total
minecraft_damage_total
```

## RCON Metrics

(only exported if RCON is configured)

```
minecraft_player_online
```

# Dashboards

In the folder dashboards you'll find grafana dashboards for these metrics, they are however incomplete and can be expanded 
or use the following dasboards:

https://grafana.com/grafana/dashboards/11993  
https://grafana.com/grafana/dashboards/11994
