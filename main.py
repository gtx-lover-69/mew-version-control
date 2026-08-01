import base64
import json
import asyncio
import re
import aiohttp
import os
import sys
import time
import subprocess
import getpass
from colorama import Fore, Style

savedir = "dataBase/userData/"
idList = "dataBase/idref.json"
idLog = "dataBase/idLog.json"

os.makedirs(savedir, exist_ok=True)
os.makedirs(os.path.dirname(idList), exist_ok=True)

def hex_to_rgb(h):
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def rgb_to_ansi256(r, g, b):
    def to_cube(x):
        return int(round(x / 255 * 5))
    rc, gc, bc = to_cube(r), to_cube(g), to_cube(b)
    return 16 + 36 * rc + 6 * gc + bc

def fg_hex(hex_color, text):
    r, g, b = hex_to_rgb(hex_color)
    idx = rgb_to_ansi256(r, g, b)
    return f"\x1b[38;5;{idx}m{text}{Style.RESET_ALL}"

def clear_screen ():
    if not os.environ.get("PYCHARM_HOSTED"):
        os.system('cls' if os.name == 'nt' else 'clear')

def ping(site, count=3, timeout_s=1):
    print(f"Checking connection to {site}...")

    if os.name == "nt":
        cmd = ["ping", "-n", str(count), "-w", str(timeout_s * 1000), site]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout_s), site]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

headers = {
    "x-csrftoken": "a",
    "x-requested-with": "XMLHttpRequest",
    "Cookie": "scratchcsrftoken=a;scratchlanguage=en;",
    "referer": "https://scratch.mit.edu",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Content-Type": "application/json",
}


def saveID(id_, key, identif, success):
    if os.path.exists(idList):
        with open(idList, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data[key] = identif

    with open(idList, "w") as file:
        json.dump(data, file, indent=2)

    if os.path.exists(idLog):
        with open(idLog, "r") as f:
            logData = json.load(f)
    logData[key+identif] = success
    with open(idLog, "w") as f:
        json.dump(logData, f, indent=2)


async def login(id_, username, password):
    body = json.dumps({
        "username": username,
        "password": password,
        "useMessages": True,
    })

    async with aiohttp.ClientSession() as session:
        key = "L"
        identif = str(int(re.sub(r'\D', '', id_)) + 1)

        async with session.post("https://scratch.mit.edu/login/", data=body, headers=headers) as resp:
            try:
                result = (await resp.json())[0]
            except Exception as e:
                print(e)
                saveID(id_, key, identif, False)
                return {"success": False, "error": "unexpected_response"}

            if result.get("success") != 1:
                saveID(id_, key, identif, False)
                return {"success": False, "error": "invalid_credentials"}

            session_cookie = resp.cookies.get("scratchsessionsid")

    data = {
        "username": username,
        "password": password,
        "session_id": session_cookie.value if session_cookie else None,
        "token": result.get("token"),
    }

    with open(savedir + username + ".json", "w") as file:
        json.dump(data, file, indent=2)

    saveID(id_, key, identif, True)
    print("Authenticated!")
    return {
        "success": True,
        "username": username,
        "session_id": session_cookie.value if session_cookie else None,
        "token": result.get("token"),
    }


async def repoCreate(id_, **kwargs):
    return {"success": False, "error": "not_implemented"}

async def repoCreateOK(id_, **kwargs):
    return {"success": False, "error": "not_implemented"}

async def repoDelete(id_, **kwargs):
    return {"success": False, "error": "not_implemented"}

async def repoDeleteOK(id_, **kwargs):
    return {"success": False, "error": "not_implemented"}

async def repoCommit(id_, **kwargs):
    return {"success": False, "error": "not_implemented"}

async def repoCommitOK(id_, **kwargs):
    return {"success": False, "error": "not_implemented"}

async def repoGetData(id_, **kwargs):
    return {"success": False, "error": "not_implemented"}

async def repoGetDataResponse(id_, **kwargs):
    return {"success": False, "error": "not_implemented"}

async def getRepoList(id_, username):
    key = "GRL"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)

    with open(savedir + username + ".json") as f:
        data = json.load(f)

        if not data.get("repos"):
            saveID(id_, key, identif, False)
            return {"success": False, "error": "no_repos"}

        else:
            saveID(id_, key, identif, True)

async def getProjectList(id_, username, **kwargs):
    url = f"https://api.scratch.mit.edu/users/{username}/projects"

    key = "GRL"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"limit": 40}, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            try:
                projects = await resp.json()
            except Exception as e:
                print(e)
                saveID(id_, key, identif, False)
                return {"success": False, "error": "unexpected_response"}

    for p in projects:
        print(p.get("id"), p.get("title"))

    input("Press enter to go back.")
    saveID(id_, key, identif, True)
    return {"success": True, "username": username, "projects": projects}

funcs = {
    "L": login,
    "RC": repoCreate,
    "RCOK": repoCreateOK,
    "RD": repoDelete,
    "RDOK": repoDeleteOK,
    "RCM": repoCommit,
    "RCMOK": repoCommitOK,
    "RGD": repoGetData,
    "RGDR": repoGetDataResponse,
    "GRL": getRepoList,
    "GPL": getProjectList,
}

async def main():
    if not ping("scratch.mit.edu"):
        print("Could not connect. Check your internet connection.")
        exit(0)
    else:
        print("Connected successfully!")

    clear_screen()
    while True:
        username = input(Style.RESET_ALL + "Enter your username: " + Fore.LIGHTBLUE_EX)

        if not os.path.isfile(savedir + username + ".json"):
            if not os.environ.get("PYCHARM_HOSTED"):
                password = getpass.getpass(Style.RESET_ALL + "Enter your password: " + Fore.LIGHTBLUE_EX)
            else:
                password = input(Style.RESET_ALL + "Enter your password: " + Fore.LIGHTBLUE_EX)
            data = {
                "username":username,
                "password":password
            }
            with open((savedir + username + ".json"), 'w') as file:
                json.dump(data, file, indent=2)

        else:
            with open((savedir + username + ".json"), "r") as f:
                data = json.load(f)
                password = data.get("password")

        with open(("dataBase/idref.json"), "r") as f:
            data = json.load(f)

            id_ = data.get("L")

        try:
            result = await(login(id_, username, password))
        except Exception as e:
            print("Error: " + str(e))

        if not result.get("success"):
            print(Fore.RED + "Could not authenticate." + Style.RESET_ALL)
            os.remove(savedir + username + ".json")
            time.sleep(1)
        else:
            clear_screen()
            break

    print(Style.BRIGHT + fg_hex("#ffb4cc", "Welcome to Mew!"))
    while True:
        print("1. View your projects")
        print("2. View your repos")
        print("0. Exit")
        menuChoice = input("> ")
        if menuChoice == "":
            print("Invalid choice. Try again.")

        elif int(menuChoice) == 1:
            with open(("dataBase/idref.json"), "r") as f:
                data = json.load(f)

                id_ = data.get("GPL")

            await getProjectList(id_, username)

        elif int(menuChoice) == 2:
            with open(("dataBase/idref.json"), "r") as f:
                data = json.load(f)

                id_ = data.get("GRL")

            await getRepoList(id_, username)

        elif int(menuChoice) == 0:
            print(Style.BRIGHT + fg_hex("#ffb4cc", "See you soon!"))
            exit(0)

        else:
            print("Invalid choice")

def decoder(text):
    directory = 'dataBase/'
    with open(directory + text, "r") as f:
        b64_content = f.read().strip()

    decoded_bytes = base64.b64decode(b64_content)
    decoded_str = decoded_bytes.decode("utf-8")

    data = json.loads(decoded_str)

    print(data)

    with open(directory + "output.json", "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())