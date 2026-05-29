import hashlib
import binascii
from Crypto.Cipher import Blowfish
import struct
import requests

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
})

API_TOKEN = None

def init(arl: str):
    global API_TOKEN
    SESSION.cookies.set("arl", arl, domain=".deezer.com")
    r = SESSION.get(
        "https://www.deezer.com/ajax/gw-light.php",
        params={"method": "deezer.getUserData", "input": "3",
                "api_version": "1.0", "api_token": "null"}
    )
    data = r.json()
    API_TOKEN = data["results"]["checkForm"]

def gw_api(method, params={}):
    r = SESSION.post(
        "https://www.deezer.com/ajax/gw-light.php",
        params={"method": method, "input": "3",
                "api_version": "1.0", "api_token": API_TOKEN},
        json=params
    )
    return r.json()["results"]

def get_track_token(track_id: str):
    result = gw_api("song.getData", {"SNG_ID": track_id})
    return result["TRACK_TOKEN"], result["TRACK_TOKEN_EXPIRE"], result

def get_stream_url(track_token: str):
    r = SESSION.post(
        "https://media.deezer.com/v1/get_url",
        json={
            "license_token": gw_api("deezer.getUserData")["USER"]["OPTIONS"]["license_token"],
            "media": [{"type": "FULL", "formats": [
                {"cipher": "BF_CBC_STRIPE", "format": "MP3_128"},
            ]}],
            "track_tokens": [track_token],
        }
    )
    data = r.json()
    return data["data"][0]["media"][0]["sources"][0]["url"]

def get_blowfish_key(track_id: str) -> bytes:
    SECRET = "g4el58wc0zvf9na1"
    md5 = hashlib.md5(str(track_id).encode()).hexdigest()
    key = ""
    for i in range(16):
        key += chr(ord(md5[i]) ^ ord(md5[i + 16]) ^ ord(SECRET[i]))
    return key.encode()

def decrypt_chunk(key: bytes, data: bytes) -> bytes:
    iv = b"\x00\x01\x02\x03\x04\x05\x06\x07"
    cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv)
    return cipher.decrypt(data)

def download_and_decrypt(url: str, track_id: str, out_path: str):
    key = get_blowfish_key(track_id)
    r = SESSION.get(url, stream=True)
    chunk_size = 2048
    chunk_index = 0
    with open(out_path, "wb") as f:
        buf = b""
        for chunk in r.iter_content(chunk_size):
            buf += chunk
            while len(buf) >= chunk_size:
                block = buf[:chunk_size]
                buf = buf[chunk_size:]
                if chunk_index % 3 == 0:
                    block = decrypt_chunk(key, block)
                f.write(block)
                chunk_index += 1
        f.write(buf)
    print(f"Sauvegardé : {out_path}")

if __name__ == "__main__":
    arl = input("ARL : ").strip()
    init(arl)
    track_id = input("Track ID : ").strip()
    token, expire, data = get_track_token(track_id)
    print(f"Token obtenu, expire : {expire}")
    url = get_stream_url(token)
    print(f"URL : {url}")
    download_and_decrypt(url, track_id, f"{track_id}.mp3")