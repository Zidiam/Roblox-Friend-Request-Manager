import os
import requests
import signal
import time
from colorama import Fore, Style, init
from typing import Dict

# Initialize colorama for Windows
init(autoreset=True)

roblosecurity = os.environ.get("ROBLOSECURITY")
if not roblosecurity:
    raise ValueError("ROBLOSECURITY environment variable not set")

headers = {
    "Accept": "application/json",
    "Referer": "https://www.roblox.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Cookie": f".ROBLOSECURITY={roblosecurity}",
    "X-CSRF-TOKEN": None
}

interrupted = False

def signal_handler(sig, frame):
    global interrupted
    print(f"\n{Fore.YELLOW}🚨 Ctrl-C detected, stopping operations...{Style.RESET_ALL}")
    interrupted = True

def get_xsrf_token():
    try:
        response = requests.post(
            "https://auth.roblox.com/v2/login",
            headers=headers,
            timeout=5
        )
        if 'x-csrf-token' in response.headers:
            headers["X-CSRF-TOKEN"] = response.headers['x-csrf-token']
            return True
        return False
    except Exception as e:
        print(f"{Fore.RED}❌ Error getting XSRF token: {str(e)}{Style.RESET_ALL}")
        return False

def get_administrator_status(user_id: int) -> bool:
    try:
        response = requests.get(
            f"https://accountinformation.roblox.com/v1/users/{user_id}/roblox-badges",
            headers=headers,
            timeout=5
        )
        return response.status_code == 200 and \
            any(badge.get("name") == "Administrator" for badge in response.json())
    except:
        return False

def get_verified_status(user_id: int) -> bool:
    try:
        response = requests.post(
            "https://apis.roblox.com/user-profile-api/v1/user/profiles/get-profiles",
            headers=headers,
            json={"fields": ["isVerified"], "userIds": [user_id]},
            timeout=5
        )
        if response.status_code == 200:
            profiles = response.json().get("profileDetails", [])
            return profiles[0]["isVerified"] if profiles else False
        return False
    except:
        return False

def get_follower_count(user_id: int) -> int:
    try:
        response = requests.get(
            f"https://friends.roblox.com/v1/users/{user_id}/followers/count",
            headers=headers,
            timeout=5
        )
        return response.json().get("count", 0) if response.status_code == 200 else 0
    except:
        return 0

def accept_friend_request(user_id: int) -> bool:
    return handle_friend_action(user_id, "accept")

def decline_friend_request(user_id: int) -> bool:
    return handle_friend_action(user_id, "decline")

def handle_friend_action(user_id: int, action: str) -> bool:
    try:
        if not headers["X-CSRF-TOKEN"] and not get_xsrf_token():
            print(f"{Fore.RED}❌ Failed to get XSRF token{Style.RESET_ALL}")
            return False

        response = requests.post(
            f"https://friends.roblox.com/v1/users/{user_id}/{action}-friend-request",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return True
        elif response.status_code == 403:  # Refresh CSRF token
            if get_xsrf_token():
                return handle_friend_action(user_id, action)
        return False
    except Exception as e:
        print(f"{Fore.RED}❌ {action.capitalize()} error for {user_id}: {str(e)}{Style.RESET_ALL}")
        return False

def process_friend_requests():
    global interrupted
    base_url = "https://friends.roblox.com/v1/my/friends/requests"
    params = {"limit": 18}
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        if not get_xsrf_token():
            print(f"{Fore.RED}❌ Failed to initialize CSRF token{Style.RESET_ALL}")
            return

        while not interrupted:
            try:
                response = requests.get(base_url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                current_users = data.get("data", [])
                if not current_users:
                    print(f"{Fore.CYAN}🌈 No more friend requests found{Style.RESET_ALL}")
                    break

                for user in current_users:
                    if interrupted:
                        break
                    
                    user_id = user["id"]
                    username = user["name"]
                    
                    # Get user criteria
                    verified = get_verified_status(user_id)
                    admin = get_administrator_status(user_id)
                    followers = get_follower_count(user_id)
                    meets_criteria = verified or admin or followers >= 10000
                    
                    # Format criteria display
                    criteria = f"{Fore.CYAN}V:{'✅' if verified else '❌'} " \
                             f"A:{'✅' if admin else '❌'} " \
                             f"F:{followers}{Style.RESET_ALL}"
                    
                    # Process request
                    if meets_criteria:
                        status = f"{Fore.GREEN}✅ ACCEPTING{Style.RESET_ALL}"
                        action = accept_friend_request
                    else:
                        status = f"{Fore.RED}❌ DECLINING{Style.RESET_ALL}"
                        action = decline_friend_request
                    
                    print(f"{status} {Fore.YELLOW}{username}{Style.RESET_ALL} ({user_id}) {criteria}")
                    
                    if action(user_id):
                        print(f"   {Fore.GREEN}↳ Success!{Style.RESET_ALL}")
                    else:
                        print(f"   {Fore.RED}↳ Failed!{Style.RESET_ALL}")
                    
                    time.sleep(0.5)  # Rate limiting

                if not data.get("nextPageCursor") or interrupted:
                    break
                params["cursor"] = data["nextPageCursor"]

            except requests.exceptions.Timeout:
                if not interrupted:
                    print(f"{Fore.YELLOW}⏳ Request timed out, retrying...{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ API Error: {str(e)}{Style.RESET_ALL}")
                break

    finally:
        if interrupted:
            print(f"\n{Fore.YELLOW}🛑 Graceful shutdown completed{Style.RESET_ALL}")

if __name__ == "__main__":
    print(f"{Fore.CYAN}🚀 Starting automated friend request processor...{Style.RESET_ALL}")
    process_friend_requests()
    print(f"{Fore.CYAN}🏁 Processing completed{Style.RESET_ALL}")