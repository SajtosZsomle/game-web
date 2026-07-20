#!/usr/bin/env python3
"""
Queries a Source engine game server using the A2S_INFO protocol
and writes the result to server-info.json.
"""
import json
import socket
import sys
import time

HOST = "147.185.221.225"
PORT = 43043
TIMEOUT = 5

A2S_INFO_REQUEST = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00"
CHALLENGE_HEADER = b"\x41"
INFO_HEADER = b"\x49"


def read_cstring(data, offset):
    end = data.index(b"\x00", offset)
    return data[offset:end].decode("utf-8", errors="replace"), end + 1


def skip(offset, n):
    return offset + n


def parse_response(data):
    if data[4:5] != INFO_HEADER:
        raise ValueError(f"Unexpected response header: {data[4:5]!r}")

    offset = skip(5, 1)  # skip protocol version
    name, offset = read_cstring(data, offset)
    map_name, offset = read_cstring(data, offset)
    _, offset = read_cstring(data, offset)  # folder
    game, offset = read_cstring(data, offset)
    offset = skip(offset, 2)  # steam app id

    players, max_players, bots = data[offset], data[offset + 1], data[offset + 2]
    offset = skip(offset, 4)  # players, max, bots, server_type
    offset = skip(offset, 1)  # environment
    visibility = data[offset]
    vac = data[offset + 1]

    return {
        "name": name,
        "map": map_name,
        "game": game,
        "players": players,
        "max_players": max_players,
        "bots": bots,
        "password_protected": bool(visibility),
        "vac_secured": bool(vac),
    }


def send_query(sock):
    sock.sendto(A2S_INFO_REQUEST, (HOST, PORT))
    data, _ = sock.recvfrom(4096)

    if data[4:5] == CHALLENGE_HEADER:
        sock.sendto(A2S_INFO_REQUEST + data[5:9], (HOST, PORT))
        data, _ = sock.recvfrom(4096)

    return data


def query():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    try:
        data = send_query(sock)
        result = parse_response(data)
        result["online"] = True
        result["queried_at"] = int(time.time())
        return result
    finally:
        sock.close()


if __name__ == "__main__":
    try:
        info = query()
    except Exception as e:
        info = {"online": False, "error": str(e), "queried_at": int(time.time())}
        print(f"Query failed: {e}", file=sys.stderr)

    with open("storage/counterStrikeSource/server-info.json", "w") as f:
        json.dump(info, f, indent=2)

    print(json.dumps(info, indent=2))
