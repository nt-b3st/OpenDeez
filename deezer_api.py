import requests
import json

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
})

ARL = None
API_TOKEN = None

def init(arl: str):
    global ARL, API_TOKEN
    ARL = arl
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
    API_TOKEN = data["results"]["checkForm"]
    return user

def gw_api(method: str, params: dict = {}):
    r = SESSION.post(
        "https://www.deezer.com/ajax/gw-light.php",
        params={
            "method": method,
            "input": "3",
            "api_version": "1.0",
            "api_token": API_TOKEN,
        },
        json=params
    )
    return r.json()["results"]

def search(query: str):
    result = gw_api("deezer.pageSearch", {
        "query": query,
        "start": 0,
        "nb": 10,
    })
    tracks = result.get("TRACK", {}).get("data", [])
    for t in tracks:
        print(f"{t['SNG_TITLE']} - {t['ART_NAME']} [{t['SNG_ID']}]")
    return tracks

if __name__ == "__main__":
    arl = input("ARL : ").strip()
    init(arl)
    query = input("Recherche : ").strip()
    search(query)