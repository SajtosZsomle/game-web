#!/usr/bin/env python3
"""
Queries a Source engine game server using the real A2S_INFO protocol
(https://developer.valvesoftware.com/wiki/Server_queries) and writes
the live result to server-info.json.

No fake/placeholder data: this either gets a real response from the
server or reports that the server is offline.
"""
import json
import socket
import struct
import sys
import time

HOST = "147.185.221.225"
PORT = 43043
TIMEOUT = 5

A2S_INFO_REQUEST = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00"


def read_cstring(data, offset):
    end = data.index(b"\x00", offset)
    return data[offset:end].decode("utf-8", errors="replace"), end + 1


def query():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.sendto(A2S_INFO_REQUEST, (HOST, PORT))
        data, _ = sock.recvfrom(4096)

        # Some servers reply with a challenge (0x41) first; resend with it.
        if data[4:5] == b"\x41":
            challenge = data[5:9]
            sock.sendto(A2S_INFO_REQUEST + challenge, (HOST, PORT))
            data, _ = sock.recvfrom(4096)

        header = data[4:5]
        if header != b"\x49":  # 'I' = A2S_INFO response
            raise ValueError(f"Unexpected response header: {header!r}")

        offset = 5
        offset += 1  # protocol version (byte)
        name, offset = read_cstring(data, offset)
        map_name, offset = read_cstring(data, offset)
        _folder, offset = read_cstring(data, offset)
        game, offset = read_cstring(data, offset)
        offset += 2  # steam app id (short)
        players = data[offset]; offset += 1
        max_players = data[offset]; offset += 1
        bots = data[offset]; offset += 1
        _server_type = data[offset]; offset += 1
        _environment = data[offset]; offset += 1
        visibility = data[offset]; offset += 1
        vac = data[offset]; offset += 1

        return {
            "online": True,
            "name": name,
            "map": map_name,
            "game": game,
            "players": players,
            "max_players": max_players,
            "bots": bots,
            "password_protected": bool(visibility),
            "vac_secured": bool(vac),
            "queried_at": int(time.time()),
        }
    finally:
        sock.close()


if __name__ == "__main__":
    try:
        info = query()
    except Exception as e:
        info = {
            "online": False,
            "error": str(e),
            "queried_at": int(time.time()),
        }
        print(f"Query failed: {e}", file=sys.stderr)

    with open("counterStrikeSource/server-info.json", "w") as f:
        json.dump(info, f, indent=2)

    print(json.dumps(info, indent=2))