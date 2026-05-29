import requests
import json

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Content-Type": "application/json",
})

def get_csrf_token():
    r = SESSION.get(
        "https://www.deezer.com/ajax/gw-light.php",
        params={
            "method": "deezer.getUserData",
            "input": "3",
            "api_version": "1.0",
            "api_token": "null",
        }
    )
    data = r.json()
    return data["results"]["checkForm"]

def login_arl(arl: str):
    SESSION.cookies.set("arl", arl, domain=".deezer.com")
    r = SESSION.get(
        "https://www.deezer.com/ajax/gw-light.php",
        params={
            "method": "deezer.getUserData",
            "input": "3",
            "api_version": "1.0",
            "api_token": "null",
        }
    )
    data = r.json()
    user = data["results"]["USER"]
    if user["USER_ID"] == 0:
        print("ARL invalide ou expiré")
        return None
    print(f"Connecté : {user['BLOG_NAME']} (id={user['USER_ID']})")
    return data["results"]

if __name__ == "__main__":
    arl = input("Entre ton ARL Deezer : ").strip()
    result = login_arl(arl)
    if result:
        print(f"Token CSRF : {result['checkForm']}")