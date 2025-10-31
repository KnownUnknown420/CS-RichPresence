#!/usr/bin/env python3

import time
import psutil
from pypresence import Presence
import server


client_id = '1151973828633829447'
GSI_AUTH = "S8RL9Z6Y22TYQK45JB4V8PHRJJMD9DS9"
GSI_ADDR = ("127.0.0.1", 3000)
REFRESH_INTERVAL = 2  # seconds


# Initialize Rich Presence
RPC = Presence(client_id)
RPC.connect()
server = server.GSIServer(GSI_ADDR, GSI_AUTH)
server.start_server()

game_time = None
last_map = None
data = None

gamemode_mapping = {
    'deathmatch': 'Deathmatch',
    'competitive': 'Competitive',
    'gungameprogressive': 'Arms Race',
    'scrimcomp2v2': 'Wingman',
    'casual': 'Casual',
    'custom': 'Custom',
}

# Optional custom map names
custom_map_names = {
    'Dust2': 'Dust II',
    'Brewry': 'Brewery',
}


def format_map_name(raw_name: str) -> str:
    if not raw_name:
        return "Unknown Map"
    if raw_name.startswith(("de_", "cs_", "ar_")):
        raw_name = raw_name.split("_", 1)[1]
    formatted = raw_name.replace("_", " ").title()
    return custom_map_names.get(formatted, formatted)


def safe_get(*args, default=None):
    try:
        return server.get_info(*args)
    except Exception:
        return default


while True:
    # Efficient process check
    game_found = any(
        proc.info["name"].lower() in ("cs2", "cs2.exe")
        for proc in psutil.process_iter(attrs=["name"])
    )

    if game_found:
        if game_time is None:
            game_time = time.time()

        # Safely fetch GSI data
        player_activity = safe_get("player", "activity")
        player_name = safe_get("player", "steamid")
        local_player = safe_get("provider", "steamid")
        current_map = safe_get("map", "name")

        # Reset timer if map changes
        if current_map and current_map != last_map:
            last_map = current_map
            game_time = time.time()

        # Debug output
        print(f"Map: {current_map}")
        print(f"Player SteamID: {player_name}")
        print(f"Local SteamID: {local_player}")
        print(f"Kills: {safe_get('player', 'match_stats', 'kills')}")

        # --- MENU STATE --- #
        if player_activity == 'menu':
            data = {
                "large_image": 'cs2',
                "state": "In Menu",
                "start": game_time
            }

        # --- IN-GAME STATE --- #
        elif player_activity != 'menu' and current_map:
            display_map_name = format_map_name(current_map)
            gamemode_name = safe_get("map", "mode")
            display_gamemode = gamemode_mapping.get(
                gamemode_name, gamemode_name.title() if gamemode_name else "Unknown Mode"
            )

            map_ct_score = safe_get("map", "team_ct", "score", default=0)
            map_t_score = safe_get("map", "team_t", "score", default=0)
            player_assists = safe_get("player", "match_stats", "assists", default=0)
            player_kills = safe_get("player", "match_stats", "kills", default=0)
            player_deaths = safe_get("player", "match_stats", "deaths", default=0)
            player_team = safe_get("player", "team", default="Unknown")

            data = {
                "state": f"K: {player_kills} | D: {player_deaths} | A: {player_assists}"
                         if player_name == local_player else "Dead",
                "details": f"{display_map_name} - {map_ct_score}:{map_t_score}"
                           if player_team == 'CT'
                           else f"{display_map_name} - {map_t_score}:{map_ct_score}",
                "large_image": current_map or 'unknown',
                "large_text": f"Playing {display_gamemode} on {display_map_name}",
                "small_image": 'ct' if player_team == 'CT' else 't',
                "small_text": f"Playing {player_team}",
                "start": game_time
            }

        # Update Discord presence
        if data:
            try:
                RPC.update(**data)
            except Exception as e:
                print(f"RPC error: {e}, reconnecting...")
                try:
                    RPC.connect()
                    RPC.update(**data)
                except Exception as e:
                    print(f"Reconnection failed: {e}")
        else:
            RPC.clear()
            game_time = None

    else:
        if last_map is not None:
            print("Game closed. Resetting state...")
        last_map = None
        data = None
        game_time = None
        RPC.clear()

    time.sleep(REFRESH_INTERVAL)
