import json
import asyncio
import re
from logging import exception

import aiohttp
import os
import time
from datetime import  datetime
import subprocess
import getpass
from colorama import Fore, Style

savedir = "dataBase/userData/"
idList = "dataBase/idref.json"
idLog = "dataBase/idLog.json"
repoList = "dataBase/repos.json"
checkList = "dataBase/checklist.json"

print("Initialized:")
os.makedirs(savedir, exist_ok=True)
print("  savedir:", os.path.abspath(savedir))
os.makedirs("dataBase", exist_ok=True)

if not os.path.exists(idList):
    with open(idList, "w") as f:
        json.dump({"L":"0",
                    "GPL":"0",
                    "GRL":"0",
                    "RC":"0",
                    "SO":"0",
                    "GRD":"0",
                    "CHC":"0"
                    }, f)
        f.flush()
print("  idList:", os.path.abspath(idList))

if not os.path.exists(idLog):
    with open(idLog, "w") as f:
        json.dump({}, f)
        f.flush()
print("  idLog:", os.path.abspath(idLog))

if not os.path.exists(repoList):
    with open(repoList, "w") as f:
        json.dump({}, f)
        f.flush()
print("  repoList:", os.path.abspath(repoList))

if not os.path.exists(checkList):
    with open(checkList, "w") as f:
        json.dump({}, f)
        f.flush()
print("  checkList:", os.path.abspath(checkList))

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
clear_screen()

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

    logData.setdefault(key, []).append({
        "id": key+identif,
        "status": success,
        "time": time.time()
    })

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
                saveID(id_, key, identif, "unexpected_response")
                return {"success": False, "error": "unexpected_response"}

            if result.get("success") != 1:
                saveID(id_, key, identif, "invalid_credentials")
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

    saveID(id_, key, identif, "success")
    print("Authenticated!")
    return {
        "success": True,
        "username": username,
        "session_id": session_cookie.value if session_cookie else None,
        "token": result.get("token"),
    }

async def removeData(id_, password):
    key = "RD"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)
    print("This feature isn't available just yet. Check back in soon!")
    saveID(id_, key, identif, "nonexistent")

async def signOut(id_, username, password):
    key = "SO"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)

    while True:
        print(f"{Fore.RED}[WARNING]{Style.RESET_ALL} This will delete your password, token, and session ID from this machine.")
        deleteChoice = input(f"{Fore.RED}[WARNING]{Style.RESET_ALL} Are you sure you want to sign out? {Style.DIM} [y/N] {Style.RESET_ALL}")
        if deleteChoice == "" or deleteChoice.upper().strip() == "N":
            print("Alright!")
            saveID(id_, key, identif, "user_cancelled")
            return {"success": False, "error": "user_cancelled"}
        elif deleteChoice.upper().strip() == "Y":
            while True:
                if not os.environ.get("PYCHARM_HOSTED"):
                    passAttempt = getpass.getpass(Style.RESET_ALL + "Enter your password: " + Fore.LIGHTBLUE_EX)
                else:
                    passAttempt = input(Style.RESET_ALL + "Enter your password: " + Fore.LIGHTBLUE_EX)
                if passAttempt.upper() == "ABORT":
                    break
                if passAttempt == password:
                    break
                print(Fore.RED + "Incorrect password." + Style.RESET_ALL)

            if passAttempt.strip() == "ABORT":
                print("Sign out cancelled.")
                saveID(id_, key, identif, "user_cancelled")
                return {"success": False, "error": "user_cancelled"}

            print("Signing out...")
            os.remove(savedir + username + ".json")
            saveID(id_, key, identif, "success")
            print("Removed data.")
            clear_screen()
            print(Style.BRIGHT + fg_hex("#ffb4cc", "See you soon!"))
            time.sleep(1)
            exit(0)

async def repoCreate(id_, username, isCheck):
    while True:
        while True:
            print("What is the ID of the project you want to create a repository for? ")
            projectID = input(Style.DIM + "(Must be public and owned by you) " + Style.RESET_ALL + "> ").strip()
            if not projectID.isdigit():
                print(Fore.RED + "Please enter a valid ID." + Style.RESET_ALL)
            else:
                projectID = int(projectID)
                break

        url = f"https://api.scratch.mit.edu/users/{username}/projects"
        key = "RC"
        identif = str(int(re.sub(r'\D', '', id_)) + 1)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"limit": 40}, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                try:
                    projects = await resp.json()
                except Exception as e:
                    print(e)
                    saveID(id_, key, identif, "unexpected_response")
                    return {"success": False, "error": "unexpected_response"}

        project_ids = {p["id"] for p in projects}

        if not projectID in project_ids:
            print(Fore.RED + "Project ID not found. Make sure that you have published this project." + Style.RESET_ALL)
            time.sleep(1)
        else:
            async def get_project_info(project_id):
                url = f"https://api.scratch.mit.edu/projects/{project_id}"

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        return await resp.json()

            projectInfo = await get_project_info(projectID)
            projectName = projectInfo["title"]
            projectToken = projectInfo["project_token"]
            print(Fore.BLUE + "Creating repository for " + projectName + Style.RESET_ALL)
            url = f"https://projects.scratch.mit.edu/{projectID}?token={projectToken}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json(content_type=None)

                with open(repoList, "r") as f:
                    repos = json.load(f)

            timestamp = time.time()

            trueTime = str(datetime.fromtimestamp(timestamp))

            repos[str(projectName)] = {
                "owner": username,
                "project_id": projectID,
                "project_token": projectToken,
                "last_updated": trueTime,
                "project": data
            }

            with open(repoList, "w") as f:
                json.dump(repos, f, indent=2)

            saveID(id_, key, identif, "success")
            print(Style.BRIGHT + fg_hex("#9cff63", "Repo created!"))
            input("Press enter to go back. ")
            break

async def checkHasChanges(id_, projectID, username):
    key = "CHC"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)

    url = f"https://api.scratch.mit.edu/projects/{projectID}"

    async def get_project_info(project_id):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()

    projectInfo = await get_project_info(projectID)
    projectName = projectInfo["title"]
    projectToken = projectInfo["project_token"]
    url = f"https://projects.scratch.mit.edu/{projectID}?token={projectToken}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json(content_type=None)

        with open(checkList, "r") as f:
            repos = json.load(f)

    repos[str(projectName)] = {
        "owner": username,
        "project_id": projectID,
        "project_token": projectToken,
        "project": data
    }

    with open(checkList, "w") as f:
        json.dump(repos, f, indent=2)

    with open(checkList, "r") as f:
        new = json.load(f)

    with open(repoList, "r") as f:
        oldData = json.load(f)

    old = oldData[projectName]
    new = new[projectName]

    def diff_changes(old, new):
        # removed keys are marked with {"__removed__": true}
        if old == new:
            return {}

        # dict vs dict: recurse
        if isinstance(old, dict) and isinstance(new, dict):
            out = {}
            old_keys = set(old.keys())
            new_keys = set(new.keys())

            # added/changed
            for k in new_keys:
                if k not in old:
                    out[k] = new[k]  # added
                else:
                    sub = diff_changes(old[k], new[k])
                    if sub != {}:
                        out[k] = sub  # changed

            # removed
            for k in old_keys - new_keys:
                out[k] = {"__removed__": True}

            return out

        # lists / primitives: replace whole value if different
        return new

    changes = diff_changes(old, new)

    with open("changes.json", "w", encoding="utf-8") as f:
        json.dump(changes, f, indent=2, ensure_ascii=False)
        f.flush()

    with open("changes.json", "r") as f:
        data = json.load(f)

    return data

async def repoDelete(id_, projectName):
    key = "RD"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)

    try:
        with open(repoList[projectName]) as f:
            json.dump({}, f, indent=2)
            saveID(id_, key, identif, "deleted")
    except Exception as e:
        print(Fore.RED + "Error: " + e)
        saveID(id_, key, identif, "no_delete")


async def repoCommit(id_, projectName):
    key = "RCM"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)

    while True:
        msg = input("Enter a commit message: ")
        if msg == "":
            print("Invalid input.")
        else:
            break

    with open(repoList) as f:
        local = json.load(f)
    with open(checkList) as f:
        checked = json.load(f)
    local[projectName] = checked[projectName]
    with open(repoList, "w") as f:
        json.dump(local, f, indent=2)
        f.flush()
    os.remove(checkList)
    saveID(id_, key, identif, f"committed: {msg}")

async def repoGetData(id_, projectName, projectID, username):
    clear_screen()
    key = "GRD"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)

    print("Retrieving data...")
    changes = await checkHasChanges(id_, projectID, username)
    clear_screen()
    print(Style.BRIGHT + fg_hex("#ffb4cc",projectName))
    with open(repoList) as f:
        repos = json.load(f)

    print(Style.BRIGHT + Fore.BLUE + "  Owner: " ,Style.RESET_ALL,repos[projectName].get("owner"))
    with open("dataBase/idref.json", "r") as f:
        data = json.load(f)
        id_ = data.get("CHC")

    print(Style.BRIGHT,Fore.BLUE,"Changes:",Style.RESET_ALL,Style.DIM,"Type " + Style.BRIGHT + "view " + Style.RESET_ALL + "to view changes")
    changeInput = input("> ")
    if changeInput.upper().strip() == "VIEW":
        print(json.dumps(changes, indent=2))
        input("Press enter to continue.")

    os.remove("changes.json")

    clear_screen()
    print(Style.BRIGHT + fg_hex("#ffb4cc",projectName))
    print("What would you like to do?")
    print("1. Commit changes locally")
    print("2. Delete repository")
    choice = input("> ")
    if choice.strip() == "1":
        if not changes:
            print(Fore.RED + "Nothing to commit.")
            saveID(id_, key, identif, "no_commit")
            return
        else:
            with open("dataBase/idref.json", "r") as f:
                data = json.load(f)
                id_ = data.get("RC")

            await repoCommit(id_, projectName)
    elif choice.strip() == "2":
        deleteChoice = input(Fore.RED + Style.BRIGHT + "Are you sure you want to delete this repository?" + Style.RESET_ALL + Style.DIM + "[y/N] ")
        if deleteChoice == "" or deleteChoice.upper().strip() == "N":
            saveID(id_, key, identif, "no_delete")
            print("Alright!")
        elif deleteChoice.upper().strip() == "Y":
            with open("dataBase/idref.json", "r") as f:
                data = json.load(f)
                id_ = data.get("RD")

            await repoDelete(id_, projectName)
    else:
        print(Fore.RED + "Invalid choice.")
        time.sleep(0.2)

async def getRepoList(id_, username):
    key = "GRL"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)

    with open(repoList) as f:
        repos = json.load(f)

    if not repos:
        print(Fore.RED + "No repos... yet!" + Style.RESET_ALL)
        saveID(id_, key, identif, "no_repos")
        while True:
            createChoice = input(f"Would you like to create one? {Style.DIM}[Y/n] {Style.RESET_ALL}")
            if createChoice == "" or createChoice.upper().strip() == "Y":
                with open(("dataBase/idref.json"), "r") as f:
                    data = json.load(f)

                    id_ = data.get("RCM")
                await repoCreate(id_, username, False)
                break
            elif createChoice.upper().strip() == "N":
                print("Alright!")
                time.sleep(1)
                saveID(id_, key, identif, "cancelled")
                return {"success": False, "error": "no_creation"}

    else:
        clear_screen()
        print(Style.BRIGHT + fg_hex("#ffb4cc", "Your repositories"))
        width = max(len(str(repos[i].get("project_id"))) for i in repos)
        for i in repos:
            print(f"{repos[i].get('project_id'):>{width}} │ {Style.BRIGHT}{i}{Style.RESET_ALL} │ Last updated: {repos[i].get('last_updated')}")

        openRepoChoice = input("Input a repository ID to edit it, or press enter to go back. ")
        if openRepoChoice == "":
            saveID(id_, key, identif, "viewed_and_left")
            return {"success": True, "error": "viewed_and_left"}

        elif openRepoChoice.strip().isdigit():
            projectID = int(openRepoChoice.strip())
            for projectName, projectData in repos.items():
                if projectData.get("project_id") == projectID:
                    with open("dataBase/idref.json", "r") as f:
                        data = json.load(f)
                        id_ = data.get("GRD")

                    await repoGetData(id_, projectName, projectID, username)
                    break
            else:
                print(Fore.RED + "Couldn't find project :(")
                saveID(id_, key, identif, "could_not_find")
                return {"success": False, "error": "could_not_find"}

        else:
            print("Invalid choice, exiting.")
            saveID(id_, key, identif, "invalid_response")
            return {"success": False, "error": "invalid_response"}

async def getProjectList(id_, username):
    clear_screen()
    url = f"https://api.scratch.mit.edu/users/{username}/projects"

    key = "GRL"
    identif = str(int(re.sub(r'\D', '', id_)) + 1)

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            try:
                projects = await resp.json()
            except Exception as e:
                print(e)
                saveID(id_, key, identif, "unexpected_response")
                return {"success": False, "error": "unexpected_response"}

    width = max(len(str(p.get("id"))) for p in projects)

    for p in projects:
        print(f"{p.get('id'):>{width}} │ {Style.BRIGHT}{p.get('title')}{Style.RESET_ALL}")

    input("Press enter to go back. ")
    saveID(id_, key, identif, "success")
    return {"success": True, "username": username, "projects": projects}

async def main():
    clear_screen()
    if not ping("scratch.mit.edu"):
        print(Fore.RED + "Could not connect. Check your internet connection.")
        time.sleep(3)
    else:
        print(fg_hex("#9cff63", "Connected successfully"))
        time.sleep(0.1)

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
                try:
                    data = json.load(f)
                    password = data.get("password")
                except Exception:
                    if not os.environ.get("PYCHARM_HOSTED"):
                        password = getpass.getpass(Style.RESET_ALL + "Enter your password: " + Fore.LIGHTBLUE_EX)
                    else:
                        password = input(Style.RESET_ALL + "Enter your password: " + Fore.LIGHTBLUE_EX)

        with open(("dataBase/idref.json"), "r") as f:
            data = json.load(f)

            id_ = data.get("L")

        result = {"success": False}

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

    while True:
        clear_screen()
        print(Style.BRIGHT + fg_hex("#ffb4cc", "Welcome to Mew!"))
        print("1. View your projects")
        print("2. View your repos")
        print("S. Settings")
        print("0. Exit")
        menuChoice = input("> ")
        if menuChoice == "":
            print(Fore.RED + "Invalid choice. Try again." + Style.RESET_ALL)

        # Settings
        elif menuChoice.upper().strip() == "S":
            clear_screen()
            print(Fore.RED + Style.BRIGHT + "   [ DANGER ZONE ]" + Style.RESET_ALL)
            print("1. Sign out")
            print("2. Remove all data")
            while True:
                settingsChoice = input("> ")
                if settingsChoice == "":
                    print(Fore.RED + "Invalid choice.")

                elif settingsChoice.strip() == "1":
                    with open(("dataBase/idref.json"), "r") as f:
                        data = json.load(f)

                        id_ = data.get("SO")
                    await signOut(id_, username, password)

                elif settingsChoice.strip() == "2":
                    with open(("dataBase/idref.json"), "r") as f:
                        data = json.load(f)

                        id_ = data.get("RD")
                    await removeData(id_, password)

                else:
                    print(Fore.RED + "Invalid choice. ")

        # Get project list
        elif menuChoice.strip() == "1":
            with open(("dataBase/idref.json"), "r") as f:
                data = json.load(f)

                id_ = data.get("GPL")

            await getProjectList(id_, username)

        # Get repo list
        elif menuChoice.strip() == "2":
            with open(("dataBase/idref.json"), "r") as f:
                data = json.load(f)

                id_ = data.get("GRL")

            await getRepoList(id_, username)

        # Exit
        elif menuChoice.strip() == "0":
            print(Style.BRIGHT + fg_hex("#ffb4cc", "See you soon!"))
            time.sleep(1)
            exit(0)

        else:
            print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())