"""robots.txt checker

Simple tool to fetch and parse robots.txt for a list of hosts and report Disallow rules for User-agent: *.
Usage: python scripts/check_robots.py hosts.txt

Hosts file contains one host per line (e.g., www.flashscore.es)
"""
from __future__ import annotations

import sys
import requests
from typing import Dict, List


def fetch_robots_txt(host: str, timeout: int = 10) -> str | None:
    url = f"https://{host}/robots.txt"
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.text
        return None
    except Exception:
        return None


def parse_disallows(robots_txt: str) -> List[str]:
    lines = robots_txt.splitlines()
    disallows: List[str] = []
    user_agent_all = False
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("user-agent:"):
            ua = line.split(":", 1)[1].strip()
            user_agent_all = ua == "*"
            continue
        if user_agent_all and line.lower().startswith("disallow:"):
            val = line.split(":", 1)[1].strip()
            disallows.append(val)
    return disallows


def check_hosts(hosts: List[str]) -> Dict[str, List[str]]:
    report: Dict[str, List[str]] = {}
    for h in hosts:
        txt = fetch_robots_txt(h)
        if not txt:
            report[h] = []
            continue
        report[h] = parse_disallows(txt)
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_robots.py hosts.txt")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        hosts = [l.strip() for l in f if l.strip()]
    rep = check_hosts(hosts)
    for host, dis in rep.items():
        print(f"Host: {host}")
        if not dis:
            print("  No Disallow rules for User-agent: * or robots.txt missing")
        else:
            for d in dis:
                print(f"  Disallow: {d}")
