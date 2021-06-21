# noinspection PyProtectedMember
from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY, \
    GaugeMetricFamily, CounterMetricFamily
import time
import requests
import json
import logging
import nbt
import re
import os
import schedule
from mcrcon import MCRcon
from os import listdir
from os.path import isfile, join

# Can move this around or add handlers as needed
m_logger = logging.getLogger(__name__)
env_level = os.environ.get('LOG_LEVEL', "INFO")
level = logging.getLevelName(env_level)
m_logger.setLevel(level)
ch = logging.StreamHandler()
ch.setLevel(level)
formatter = logging.Formatter(
    fmt='time=%(created)f level=%(levelname)s ' 
    'method=%(funcName)s:%(lineno)s msg="%(message)s"',
    datefmt='%d-%b-%Y %H:%M:%S %z %Z')
ch.setFormatter(formatter)
m_logger.addHandler(ch)

MOJANG_API_NAMES_URL = "https://api.mojang.com/user/profiles/%s/names"


class MinecraftCollector(object):
    def __init__(self):
        # Can move this around or add handlers as needed
        self.logger = logging.getLogger(__name__)

        world_directory = os.environ.get("WORLD_DIR", "/world")
        self.stats_directory = "%s/stats" % world_directory
        self.player_directory = "%s/playerdata" % world_directory
        self.advancements_directory = "%s/advancements" % world_directory

        self.uuid_name_map = dict()
        self.rcon = None

        schedule.every().day.at("01:00").do(self.flush_playernamecache)

    def get_players(self):
        return [f[:-5] for f in listdir(self.stats_directory) if isfile(join(self.stats_directory, f))]

    def flush_playernamecache(self):
        self.logger.info("flushing playername cache")
        self.uuid_name_map = dict()
        return

    def uuid_to_player(self, uuid):
        result = uuid
        if uuid in self.uuid_name_map:
            result = self.uuid_name_map[uuid]
            self.logger.debug(
                "Got %s as username for %s from local cache." % (uuid, result)
            )
        else:
            response = requests.get(MOJANG_API_NAMES_URL % uuid)

            if response.status_code == 200:
                # noinspection PyBroadException
                try:
                    history = response.json()
                    for change in history:
                        if 'changedToAt' not in change and 'name' in change:
                            self.uuid_name_map[uuid] = change['name']
                            result = change['name']
                            break
                except Exception:
                    self.logger.exception(
                        "Parsing of Mojang API response failed.")

                self.logger.debug(
                    "Got %s as username for %s from Mojang API."
                    % (uuid, result))
            else:
                self.logger.error(
                    "UUID lookup failed for %s.\n"
                    "API returned %i - %s." % (
                        uuid, response.status_code, response.text)
                )
                self.logger.warning("Using UUID instead of username.")

        return result

    def rcon_command(self, command):
        if self.rcon is None:
            self.rcon = MCRcon(os.environ['RCON_HOST'], os.environ['RCON_PASSWORD'], port=int(os.environ['RCON_PORT']))
            self.rcon.connect()
        try:
            response = self.rcon.command(command)
        except BrokenPipeError:
            self.logger.error("Lost RCON Connection, trying to reconnect")
            self.rcon.connect()
            response = self.rcon.command(command)

        self.logger.info("rcon command %s got %s" % (command, response))

        return response

    def get_server_stats(self):
        metrics = []
        if not all(x in os.environ for x in ['RCON_HOST', 'RCON_PASSWORD']):
            self.logger.warning(
                "RCON_HOST and/or RCON_password are not defined."
                "\nServer stats not available."
            )
            return []
        player_online = GaugeMetricFamily(
            'player_online',
            "The value is 1 if player is online, missing if not.",
            labels=['player'])

        metrics.append(player_online)

        # player
        resp = self.rcon_command("list")
        player_regex = re.compile("players online:(.*)")
        if player_regex.findall(resp):
            for player in player_regex.findall(resp)[0].split(","):
                if not player.isspace():
                    player_online.add_metric([player.lstrip()], 1)

        return metrics

    def get_player_advancements(self, uuid, name):
        result = []
        print("get_player_advancements")

        data_version_metric = CounterMetricFamily(
            'minecraft_advancement_data_version',
            "The data version of the advancements file",
            labels=['player'])
        # aka minecraft
        story_metric = CounterMetricFamily(
            'minecraft_advancement_story_count',
            "The count of completed story advancements.",
            labels=['player'])
        nether_metric = CounterMetricFamily(
            'minecraft_advancement_nether_count',
            "The count of completed nether advancements.",
            labels=['player'])
        end_metric = CounterMetricFamily(
            'minecraft_advancement_end_count',
            "The count of completed end advancements.",
            labels=['player'])
        adventure_metric = CounterMetricFamily(
            'minecraft_advancement_adventure_count',
            "The count of completed adventure advancements.",
            labels=['player'])
        husbandry_metric = CounterMetricFamily(
            'minecraft_advancement_husbandry_count',
            "The count of completed husbandry advancements.",
            labels=['player'])
        recipe_metric = CounterMetricFamily(
            'minecraft_advancement_recipe_count',
            "The count of completed recipe advancements.",
            labels=['player'])
        other_metric = CounterMetricFamily(
            'minecraft_advancement_other_count',
            "The count of completed other advancements.",
            labels=['player'])

        advancements_file_path = os.path.join(
            self.advancements_directory, uuid + ".json")

        if not isfile(advancements_file_path):
            self.logger.warning("No advancements for player %s." % uuid)
        else:
            with open(advancements_file_path) as json_file:
                data_version = 0
                story_count = 0
                nether_count = 0
                the_end_count = 0
                adventure_count = 0
                husbandry_count = 0
                recipe_count = 0
                unknown_count = 0

                advancements = json.load(json_file)
                for key, value in advancements.items():
                    if key == "DataVersion":
                        data_version = value
                        continue

                    if "story" in key and value.get("done", False) is True:
                        story_count += 1
                    elif "nether" in key and value.get("done", False) is True:
                        nether_count += 1
                    elif "end" in key and value.get("done", False) is True:
                        the_end_count += 1
                    elif "adventure" in key and value.get("done", False) is True:
                        adventure_count += 1
                    elif "husbandry" in key and value.get("done", False) is True:
                        husbandry_count += 1
                    elif "recipe" in key and value.get("done", False) is True:
                        recipe_count += 1
                    else:
                        if value["done"] is True:
                            unknown_count += 1

            data_version_metric.add_metric([name], data_version)
            result.append(data_version_metric)

            story_metric.add_metric([name], story_count)
            result.append(story_metric)

            nether_metric.add_metric([name], nether_count)
            result.append(nether_metric)

            end_metric.add_metric([name], the_end_count)
            result.append(end_metric)

            adventure_metric.add_metric([name], adventure_count)
            result.append(adventure_metric)

            husbandry_metric.add_metric([name], husbandry_count)
            result.append(husbandry_metric)

            recipe_metric.add_metric([name], recipe_count)
            result.append(recipe_metric)

            other_metric.add_metric([name], unknown_count)
            result.append(other_metric)

        return result

    def get_player_data(self, uuid, name):
        result = []
        print("get_player_data")

        #  TODO double check that score resets on death in server
        player_score = GaugeMetricFamily(
            'player_score',
            "The score of a player.", labels=['player'])
        player_xp_total = GaugeMetricFamily(
            'player_xp_total',
            "The total amount of XP the player has collected over time;"
            " used for the Score upon death.", labels=['player'])
        player_current_level = GaugeMetricFamily(
            'player_current_level',
            "The level shown on the XP bar.",
            labels=['player'])
        player_health = GaugeMetricFamily(
            'player_health',
            "How much Health the player currently has",
            labels=['player'])
        player_food_level = GaugeMetricFamily(
            'player_food_level',
            "The value of the hunger bar; 20 is full.",
            labels=['player'])
        player_food_saturation_level = GaugeMetricFamily(
            'player_food_saturation_level',
            "The food saturation the player currently has.",
            labels=['player'])
        player_food_exhaustion_level = GaugeMetricFamily(
            'player_food_exhaustion_level',
            "The food exhaustion the player currently has.",
            labels=['player'])
        player_game_type = GaugeMetricFamily(
            'player_game_type',
            "The game mode of the player."
            " 0 is Survival, 1 is Creative,"
            " 2 is Adventure and 3 is Spectator.",
            labels=['player'])
        player_dimension = GaugeMetricFamily(
            'player_dimension',
            "A namespaced ID of the dimension the player is in.",
            labels=['player', 'dimension'])

        player_data_file_path = os.path.join(
            self.player_directory, uuid + ".dat")

        if not isfile(player_data_file_path):
            self.logger.error("No player data for player %s." % uuid)
        else:
            nbtfile = nbt.nbt.NBTFile(player_data_file_path, 'rb')

            player_score.add_metric([name], nbtfile.get("Score").value)
            result.append(player_score)

            player_xp_total.add_metric([name], nbtfile.get("XpTotal").value)
            result.append(player_xp_total)

            player_current_level.add_metric(
                [name], nbtfile.get("XpLevel").value)
            result.append(player_current_level)

            player_health.add_metric([name], nbtfile.get("Health").value)
            result.append(player_health)

            player_food_level.add_metric(
                [name], nbtfile.get("foodLevel").value)
            result.append(player_food_level)

            player_food_saturation_level.add_metric(
                [name], nbtfile.get("foodSaturationLevel").value)
            result.append(player_food_saturation_level)

            player_food_exhaustion_level.add_metric(
                [name], nbtfile.get("foodExhaustionLevel").value)
            result.append(player_food_exhaustion_level)

            player_game_type.add_metric(
                [name], nbtfile.get("playerGameType").value)
            result.append(player_game_type)

            player_dimension.add_metric(
                [name, nbtfile.get("Dimension").value], 1)
            result.append(player_dimension)

        return result

    def get_player_stats(self, uuid, name):
        result = []
        print("get_player_stats")
        # Define a metric for each category of stat
        # https://minecraft.fandom.com/wiki/Statistics#Statistic_types_and_names
        blocks_mined = CounterMetricFamily(
            'blocks_mined',
            'The count of blocks a player mined by block type.',
            labels=['player', 'block'])
        items_broken = CounterMetricFamily(
            'items_broken',
            'The count of items a player has used to negative durability.',
            labels=['player', 'item'])
        items_crafted = CounterMetricFamily(
            'items_mined',
            'The count of items a player has crafted, smelted, etc.',
            labels=['player', 'item'])
        items_used = CounterMetricFamily(
            'items_used',
            'The count of blocks or items a player used.',
            labels=['player', 'item'])
        items_picked_up = CounterMetricFamily(
            'items_picked_up',
            'The count of items a player picked up.',
            labels=['player', 'item'])
        items_dropped = CounterMetricFamily(
            'items_dropped',
            'The count of items a player has dropped.',
            labels=['player', 'item'])
        entities_killed = CounterMetricFamily(
            'entities_killed',
            "The count of entities killed by a player.",
            labels=['player', 'entity'])
        entities_killed_by = CounterMetricFamily(
            'entities_killed_by',
            "The count of entities that killed a player",
            labels=['player', 'entity'])

        mc_custom = CounterMetricFamily(
            'mc_custom', "Custom Minecraft stat",
            labels=['player', 'custom_stat'])

        # Let's break out some sub-categories from the
        # custom stats to avoid high label cardinality (where we can)
        minecraft_distance_traveled_cm = CounterMetricFamily(
            'minecraft_distance_traveled_cm',
            "The total distance traveled by method of transportation.",
            labels=['player', 'method'])

        minecraft_interactions_total = CounterMetricFamily(
            'minecraft_interactions_total',
            "The number of times interacted with various workstations.",
            labels=['player', 'workstation'])

        minecraft_damage_total = CounterMetricFamily(
            'minecraft_damage_total',
            "The amount of damage a player has dealt/taken by category.",
            labels=['player', 'category'])

        player_stats_file_path = os.path.join(
            self.stats_directory, uuid + ".json")

        if not isfile(player_stats_file_path):
            self.logger.error("No statistics for player %s." % uuid)
            return result

        with open(player_stats_file_path) as json_file:
            data = json.load(json_file)
            json_file.close()

        # I can't think of a reason why I'd ever play an older version
        # hence removal of pre 1.15 code block.
        if "stats" not in data:
            self.logger.error(
                "No stats key in file %s." % player_stats_file_path)
        else:
            stats = data["stats"]

            if "minecraft:mined" in stats:
                for block, value in stats["minecraft:mined"].items():
                    blocks_mined.add_sample(
                        "blocks_mined", value=value,
                        labels={'player': name, 'block': block})
                result.append(blocks_mined)

            if "minecraft:broken" in stats:
                for item, value in stats["minecraft:broken"].items():
                    items_broken.add_sample(
                        "items_broken", value=value,
                        labels={'player': name, 'item': item})
                result.append(items_broken)

            if "minecraft:crafted" in stats:
                for item, value in stats["minecraft:crafted"].items():
                    items_crafted.add_sample(
                        "items_crafted", value=value,
                        labels={'player': name, 'item': item})
                result.append(items_crafted)

            if "minecraft:used" in stats:
                for item, value in stats["minecraft:used"].items():
                    items_used.add_sample(
                        "items_used", value=value,
                        labels={'player': name, 'item': item})
                result.append(items_used)

            if "minecraft:picked_up" in stats:
                for item, value in stats["minecraft:picked_up"].items():
                    items_picked_up.add_sample(
                        "items_picked_up", value=value,
                        labels={'player': name, 'item': item})
                result.append(items_picked_up)

            if "minecraft:items_dropped" in stats:
                for item, value in stats["minecraft:items_dropped"].items():
                    items_dropped.add_sample(
                        "items_dropped", value=value,
                        labels={'player': name, 'item': item})
                result.append(items_dropped)

            if "minecraft:killed" in stats:
                for entity, value in stats["minecraft:killed"].items():
                    entities_killed.add_sample(
                        "entities_killed", value=value,
                        labels={'player': name, 'entity': entity})
                result.append(entities_killed)

            if "minecraft:killed_by" in stats:
                for entity, value in stats["minecraft:killed_by"].items():
                    entities_killed_by.add_sample(
                        "entities_killed_by", value=value,
                        labels={'player': name, 'entity': entity})
                result.append(entities_killed_by)

            # Grab the custom stats
            for custom_stat, value in stats["minecraft:custom"].items():
                if custom_stat.endswith("one_cm"):
                    minecraft_distance_traveled_cm.add_metric(
                        [name, custom_stat], value)
                elif custom_stat.startswith("interact"):
                    minecraft_interactions_total.add_metric(
                        [name, custom_stat], value
                    )
                elif custom_stat.startswith("damage"):
                    minecraft_damage_total.add_metric(
                        [name, custom_stat], value
                    )
                else:
                    mc_custom.add_metric([name, custom_stat], value)

            result.append(minecraft_distance_traveled_cm)
            result.append(minecraft_interactions_total)
            result.append(minecraft_damage_total)
            result.append(mc_custom)

        return result

    def collect(self):
        for uuid in self.get_players():
            name = self.uuid_to_player(uuid)  # if this fails we use the UUID

            # TODO fix this so all the yields happen elsewhere
            metrics = self.get_player_advancements(uuid, name)
            for metric in metrics:
                yield metric

            metrics = self.get_player_data(uuid, name)
            for metric in metrics:
                yield metric

            metrics = self.get_player_stats(uuid, name)
            for metric in metrics:
                yield metric

        # Leave this guy alone for now
        for metric in self.get_server_stats():
            yield metric


if __name__ == '__main__':
    logger = logging.getLogger(__name__)

    logger.info("Starting up")
    if all(x in os.environ for x in ['RCON_HOST', 'RCON_PASSWORD']):
        logger.info("RCON is enabled for " + os.environ['RCON_HOST'])

    start_http_server(8000)
    REGISTRY.register(MinecraftCollector())
    logger.info("Exporter started on Port 8000")
    while True:
        time.sleep(1)
        schedule.run_pending()
