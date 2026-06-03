#!/usr/bin/env python3
"""
OpenDeez — Client Deezer GTK4
pip install requests pycryptodome --break-system-packages
dnf install mpv
"""
import gi
gi.require_version("Gtk","4.0"); gi.require_version("Adw","1"); gi.require_version("GLib","2.0")
from gi.repository import Gtk, Adw, GLib, Pango, GdkPixbuf, Gdk, Gio
import threading, hashlib, tempfile, os, subprocess, json, requests, time

# ── Config ─────────────────────────────────────────────────────────────────────
CONFIG_DIR  = os.path.expanduser("~/.config/opendeez")
CONFIG_FILE = os.path.join(CONFIG_DIR,"config.json")
os.makedirs(CONFIG_DIR, exist_ok=True)

def load_config():
    try: return json.load(open(CONFIG_FILE))
    except: return {}

def save_config(d): json.dump(d, open(CONFIG_FILE,"w"))

# ── Deezer API ─────────────────────────────────────────────────────────────────
SESSION       = requests.Session()
SESSION.headers.update({"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"})
API_TOKEN=LICENSE_TOKEN=USER_ID=USER_TOKEN=None
QUALITY="MP3_128"
REST="https://api.deezer.com"

def dz_init(arl):
    global API_TOKEN,LICENSE_TOKEN,USER_ID,USER_TOKEN
    SESSION.cookies.set("arl",arl,domain=".deezer.com")
    r=SESSION.get("https://www.deezer.com/ajax/gw-light.php",
                  params={"method":"deezer.getUserData","input":"3","api_version":"1.0","api_token":"null"})
    d=r.json()["results"]
    API_TOKEN=d["checkForm"]; LICENSE_TOKEN=d["USER"]["OPTIONS"].get("license_token",""); USER_ID=d["USER"]["USER_ID"]
    USER_TOKEN=d["USER"].get("USER_TOKEN","") or d.get("USER_TOKEN","")
    if USER_ID==0: raise ValueError("ARL invalide")
    return d["USER"]

def gw(method,params={}):
    r=SESSION.post("https://www.deezer.com/ajax/gw-light.php",
                   params={"method":method,"input":"3","api_version":"1.0","api_token":API_TOKEN},json=params)
    return r.json().get("results",{})

def rest(path,params={}):
    return SESSION.get(f"{REST}{path}",params=params).json()

def dz_search_all(q):
    tracks  = gw("deezer.pageSearch",{"query":q,"start":0,"nb":30}).get("TRACK",{}).get("data",[])
    albums  = rest("/search/album",  {"q":q,"limit":20}).get("data",[])
    artists = rest("/search/artist", {"q":q,"limit":20}).get("data",[])
    return tracks, albums, artists

def dz_flow():           return gw("radio.getUserRadio",{"user_id":USER_ID}).get("data",[])
def dz_liked_tracks():   return rest(f"/user/{USER_ID}/tracks",{"limit":200}).get("data",[])
def dz_liked_albums():   return rest(f"/user/{USER_ID}/albums",{"limit":100}).get("data",[])
def dz_liked_artists():  return rest(f"/user/{USER_ID}/artists",{"limit":100}).get("data",[])
def playlist_img_url(p,sz="264x264"):
    img=p.get("PLAYLIST_PICTURE","")
    ptype=p.get("PICTURE_TYPE","playlist")
    if not img or not img.strip(): return ""
    if img.startswith("http"): return img
    kind="cover" if ptype=="cover" else "playlist"
    return f"https://e-cdns-images.dzcdn.net/images/{kind}/{img.strip()}/{sz}-000000-80-0-0.jpg"

def dz_playlists():
    r=gw("deezer.pageProfile",{"USER_ID":USER_ID,"tab":"playlists","nb":100})
    return r.get("TAB",{}).get("playlists",{}).get("data",[])
def dz_playlist_tracks(pid):
    r=gw("deezer.pagePlaylist",{"playlist_id":pid,"nb":200,"start":0})
    return r.get("SONGS",{}).get("data",[])
def dz_playlist_info(pid):
    r=gw("deezer.pagePlaylist",{"playlist_id":pid,"nb":1,"start":0})
    return r.get("DATA",{})
def dz_album_tracks(aid):  return rest(f"/album/{aid}/tracks",{"limit":100}).get("data",[])
def dz_album_info(aid):    return rest(f"/album/{aid}")
def dz_artist_top(aid):    return rest(f"/artist/{aid}/top",{"limit":50}).get("data",[])
def dz_artist_albums(aid): return rest(f"/artist/{aid}/albums",{"limit":50}).get("data",[])
def dz_artist_info(aid):   return rest(f"/artist/{aid}")
def dz_chart():            return rest("/chart/0/tracks",{"limit":20}).get("data",[])
def dz_releases():         return rest("/editorial/0/releases",{"limit":20}).get("data",[])
def dz_history():
    r=gw("favorite_song.getList",{"USER_ID":USER_ID,"tab":"loved","nb":20,"start":0})
    return r.get("data",[])
def dz_recommended_albums():
    # Albums des artistes likés
    artists=rest(f"/user/{USER_ID}/artists",{"limit":8}).get("data",[])
    albums=[]
    for a in artists[:5]:
        aid=a.get("id","")
        if aid:
            albs=rest(f"/artist/{aid}/albums",{"limit":4}).get("data",[])
            albums.extend(albs)
    return albums[:20]
def dz_like(tid):          return gw("favorite_song.add",{"SNG_ID":str(tid)})
def dz_unlike(tid):        return gw("favorite_song.remove",{"SNG_ID":str(tid)})
def dz_liked_ids():
    tracks=rest(f"/user/{USER_ID}/tracks",{"limit":500}).get("data",[])
    return {str(t.get("id","")) for t in tracks if t.get("id")}
def dz_add_to_pl(pid,tid):    return gw("playlist.addSongs",{"playlist_id":str(pid),"songs":[[str(tid),0]]})
def dz_remove_from_pl(pid,tid): return gw("playlist.deleteSongs",{"playlist_id":str(pid),"songs":[[str(tid),0]]})
def dz_create_pl(name):       return gw("playlist.create",{"title":name,"status":0,"songs":[]})
def dz_delete_pl(pid):        return gw("playlist.delete",{"playlist_id":str(pid)})
def dz_rename_pl(pid,name):   return gw("playlist.update",{"playlist_id":str(pid),"title":name})
def dz_reorder_pl(pid,ids):   return gw("playlist.updateOrder",{"object_id":str(pid),"objects":ids})
def dz_like_album(aid):       return gw("album.addFavorite",{"ALB_ID":str(aid)})
def dz_unlike_album(aid):     return gw("album.deleteFavorite",{"ALB_ID":str(aid)})
def dz_like_artist(aid):      return gw("artist.addFavorite",{"ART_ID":str(aid)})
def dz_unlike_artist(aid):    return gw("artist.deleteFavorite",{"ART_ID":str(aid)})
def dz_smart_radio(tid):      return gw("smart.getSmartRadio",{"art_id":str(tid),"limit":30}).get("data",[])
def dz_track_mix(tid):        return gw("song.getSearchTrackMix",{"SNG_ID":str(tid),"LANG":"FR"}).get("data",[])

def dz_lyrics(tid):
    # pipe.deezer.com accepte le cookie arl directement, pas besoin de JWT
    r=SESSION.post("https://pipe.deezer.com/api",
        json={"operationName":"SynchronizedTrackLyrics","variables":{"trackId":str(tid)},
              "query":"query SynchronizedTrackLyrics($trackId: String!) { track(trackId: $trackId) { id lyrics { id copyright text writers synchronizedLines { lrcTimestamp line milliseconds duration } } } }"})
    try:
        j=r.json()
        return j["data"]["track"]["lyrics"]
    except: return None

def dz_stream_url(tid):
    d=gw("song.getData",{"SNG_ID":tid}); tok=d["TRACK_TOKEN"]
    def try_fmt(fmt):
        r=SESSION.post("https://media.deezer.com/v1/get_url",
                       json={"license_token":LICENSE_TOKEN,
                             "media":[{"type":"FULL","formats":[{"cipher":"BF_CBC_STRIPE","format":fmt}]}],
                             "track_tokens":[tok]})
        return r.json()["data"][0]["media"][0]["sources"][0]["url"]
    try:    return try_fmt(QUALITY)
    except: return try_fmt("MP3_128")

def dz_bfkey(tid):
    S="g4el58wc0zvf9na1"; m=hashlib.md5(str(tid).encode()).hexdigest()
    return "".join(chr(ord(m[i])^ord(m[i+16])^ord(S[i]))for i in range(16)).encode()

def dz_decrypt(url,tid,out):
    from Crypto.Cipher import Blowfish
    key=dz_bfkey(tid); iv=b"\x00\x01\x02\x03\x04\x05\x06\x07"
    r=SESSION.get(url,stream=True); buf,idx=b"",0
    with open(out,"wb") as f:
        for chunk in r.iter_content(2048):
            buf+=chunk
            while len(buf)>=2048:
                bl,buf=buf[:2048],buf[2048:]
                if idx%3==0: bl=Blowfish.new(key,Blowfish.MODE_CBC,iv).decrypt(bl)
                f.write(bl); idx+=1
        f.write(buf)

def dz_arl_from_firefox():
    import sqlite3,shutil
    ff=os.path.expanduser("~/.mozilla/firefox")
    if not os.path.exists(ff): return ""
    for p in os.listdir(ff):
        db=os.path.join(ff,p,"cookies.sqlite")
        if not os.path.exists(db): continue
        tmp=tempfile.NamedTemporaryFile(suffix=".sqlite",delete=False); shutil.copy2(db,tmp.name)
        try:
            c=sqlite3.connect(tmp.name)
            row=c.execute("SELECT value FROM moz_cookies WHERE host LIKE '%deezer%' AND name='arl'").fetchone()
            c.close()
            if row: return row[0]
        except: pass
        finally: os.unlink(tmp.name)
    return ""

def norm(t):
    if "SNG_ID" in t: return t
    alb_pic=t.get("album",{}).get("cover_medium","") or t.get("album",{}).get("cover_xl","")
    return {"SNG_ID":t.get("id",""),"SNG_TITLE":t.get("title","?"),
            "ART_NAME":t.get("artist",{}).get("name",""),
            "ART_ID":t.get("artist",{}).get("id",""),
            "ALB_TITLE":t.get("album",{}).get("title",""),
            "DURATION":t.get("duration",0),
            "ALB_PICTURE":alb_pic}

def cover_url(t,sz="56x56"):
    p=t.get("ALB_PICTURE") or t.get("album",{}).get("cover_medium","")
    if not p: return ""
    if p.startswith("http"): return p
    if len(p)>10:  # hash MD5
        return f"https://e-cdns-images.dzcdn.net/images/cover/{p}/{sz}-000000-80-0-0.jpg"
    return ""

def fetch_img(url,size=56):
    try:
        r=SESSION.get(url,timeout=8,allow_redirects=True)
        if r.status_code!=200 or len(r.content)<100: return None
        lo=GdkPixbuf.PixbufLoader()
        lo.write(r.content); lo.close(); pb=lo.get_pixbuf()
        if pb: return pb.scale_simple(size,size,GdkPixbuf.InterpType.BILINEAR)
    except: pass
    return None

def set_pic(pic,pb):
    try:
        tmp=tempfile.NamedTemporaryFile(suffix=".png",delete=False)
        tmp.close(); pb.savev(tmp.name,"png",[],[]); tex=Gdk.Texture.new_from_filename(tmp.name)
        os.unlink(tmp.name); pic.set_paintable(tex)
    except: pass

def load_pic_async(url,pic,size=56):
    if not url: return
    def do(): 
        pb=fetch_img(url,size)
        if pb: GLib.idle_add(set_pic,pic,pb)
    threading.Thread(target=do,daemon=True).start()

def _clr(w):
    c=w.get_first_child()
    while c: n=c.get_next_sibling(); w.remove(c); c=n

# ── CSS ────────────────────────────────────────────────────────────────────────
CSS="""
.card-cover { border-radius:12px; }
.cover-pic   { border-radius:12px; }
.circular    { border-radius:9999px; }
.player-bar  { border-top:1px solid alpha(@borders,0.5); }
.section-title { font-size:16px; font-weight:700; }
.section-sub   { font-size:12px; color:alpha(@window_fg_color,0.5); }
.page-title    { font-size:28px; font-weight:800; }
.col-header    { font-size:11px; font-weight:600; color:alpha(@window_fg_color,0.5); }
.now-title  { font-size:12px; font-weight:600; }
.now-artist { font-size:11px; }
progressbar { min-height:3px; }
progressbar progress { min-height:3px; border-radius:0; background:@accent_color; }
progressbar trough   { min-height:3px; border-radius:0; background:alpha(@window_fg_color,0.12); }
.player-btn { min-width:28px; min-height:28px; padding:2px; }
.player-btn-play { min-width:32px; min-height:32px; padding:3px; }
.home-card { border-radius:8px; }
.home-card:hover { background:alpha(@window_fg_color,0.06); }
.home-section { margin-bottom:8px; }
.quick-row-btn { border-radius:8px; }
.quick-row-btn:hover { background:alpha(@window_fg_color,0.07); }
.grid-fb flowboxchild { padding:0; min-width:120px; max-width:120px; }
"""
def apply_css():
    p=Gtk.CssProvider(); p.load_from_string(CSS)
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

# ── Widget helpers ─────────────────────────────────────────────────────────────

def make_pic(size, circle=False):
    f=Gtk.Frame(); f.set_size_request(size,size)
    f.add_css_class("circular" if circle else "card-cover")
    p=Gtk.Picture(); p.set_size_request(size,size); p.set_content_fit(Gtk.ContentFit.COVER)
    p.add_css_class("circular" if circle else "cover-pic")
    f.set_child(p); return f,p

def make_card_btn(title,subtitle,img_url,size=130,circle=False,on_click=None):
    btn=Gtk.Button(); btn.add_css_class("flat")
    btn.set_halign(Gtk.Align.START); btn.set_valign(Gtk.Align.START)
    outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
    outer.set_size_request(size,-1)
    frm,pic=make_pic(size,circle)
    frm.set_size_request(size,size)
    outer.append(frm)
    tl=Gtk.Label(label=title); tl.set_max_width_chars(13); tl.set_ellipsize(Pango.EllipsizeMode.END)
    tl.set_halign(Gtk.Align.START); tl.add_css_class("caption"); outer.append(tl)
    if subtitle:
        sl=Gtk.Label(label=subtitle); sl.set_max_width_chars(14); sl.set_ellipsize(Pango.EllipsizeMode.END)
        sl.set_halign(Gtk.Align.START); sl.set_css_classes(["caption","dim-label"]); outer.append(sl)
    btn.set_child(outer)
    if on_click: btn.connect("clicked",on_click)
    load_pic_async(img_url,pic,size)
    return btn

def make_hscroll(items,build_fn):
    sc=Gtk.ScrolledWindow(); sc.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.NEVER)
    sc.set_propagate_natural_height(True)
    box=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12)
    box.set_margin_top(4); box.set_margin_bottom(8); box.set_margin_start(12); box.set_margin_end(12)
    for it in items:
        c=build_fn(it)
        if c: box.append(c)
    sc.set_child(box); return sc

def sec_label(text):
    l=Gtk.Label(label=text); l.set_halign(Gtk.Align.START)
    l.set_css_classes(["section-title"]); l.set_margin_start(16); l.set_margin_top(12); l.set_margin_bottom(4)
    return l

def make_track_row(track, app=None, show_album_col=True):
    """Row style Deezer: pochette | titre+artiste | album | durée | like | menu"""
    row=Gtk.ListBoxRow(); row.item=track; row.item_type="track"
    box=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=0)
    box.set_margin_top(6); box.set_margin_bottom(6)
    box.set_margin_start(8); box.set_margin_end(4)

    # Pochette
    frm,pic=make_pic(40)
    frm.set_margin_end(10)
    url=cover_url(track,"56x56")
    load_pic_async(url,pic,40)
    box.append(frm)

    # Titre + artiste
    vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=1); vb.set_hexpand(True)
    title  = track.get("SNG_TITLE") or track.get("title","?")
    artist = track.get("ART_NAME")  or track.get("artist",{}).get("name","")
    tl=Gtk.Label(label=title);  tl.set_halign(Gtk.Align.START); tl.set_ellipsize(Pango.EllipsizeMode.END)
    al=Gtk.Label(label=artist); al.set_halign(Gtk.Align.START); al.set_ellipsize(Pango.EllipsizeMode.END)
    al.set_css_classes(["caption","dim-label"]); vb.append(tl); vb.append(al)
    box.append(vb)

    # Album col
    if show_album_col:
        alb=track.get("ALB_TITLE") or track.get("album",{}).get("title","")
        albl=Gtk.Label(label=alb); albl.set_width_chars(18); albl.set_max_width_chars(18)
        albl.set_ellipsize(Pango.EllipsizeMode.END); albl.set_halign(Gtk.Align.START)
        albl.add_css_class("dim-label"); albl.set_margin_end(12)
        box.append(albl)

    # Durée
    dur=int(track.get("DURATION") or track.get("duration",0))
    dl=Gtk.Label(label=f"{dur//60}:{dur%60:02d}"); dl.add_css_class("dim-label"); dl.set_margin_end(4)
    box.append(dl)

    # Like btn
    tid=str(track.get("SNG_ID") or track.get("id",""))
    like_btn=Gtk.Button()
    liked=app is not None and tid in getattr(app,"_liked_ids",set())
    like_btn.set_icon_name("starred-symbolic" if liked else "emblem-favorite-symbolic")
    like_btn.set_css_classes(["flat","circular"]+( ["accent"] if liked else []))
    like_btn.set_valign(Gtk.Align.CENTER)
    def on_like(b,t=tid,a=app):
        if not t: return
        if a is not None and t in a._liked_ids:
            a._liked_ids.discard(t)
            b.set_icon_name("emblem-favorite-symbolic"); b.remove_css_class("accent")
            def do_unlike():
                dz_unlike(t)
                if a is not None: GLib.idle_add(a._refresh_fav_tracks)
            threading.Thread(target=do_unlike,daemon=True).start()
        else:
            if a is not None: a._liked_ids.add(t)
            b.set_icon_name("starred-symbolic"); b.add_css_class("accent")
            def do_like():
                dz_like(t)
                if a is not None: GLib.idle_add(a._refresh_fav_tracks)
            threading.Thread(target=do_like,daemon=True).start()
    like_btn.connect("clicked",on_like)
    box.append(like_btn)

    # Menu ⋮
    mbox=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
    mbox.set_margin_top(4); mbox.set_margin_bottom(4); mbox.set_margin_start(4); mbox.set_margin_end(4)
    pop=Gtk.Popover(); pop.set_child(mbox)
    mbtn=Gtk.MenuButton(); mbtn.set_icon_name("view-more-symbolic")
    mbtn.set_css_classes(["flat","circular"]); mbtn.set_valign(Gtk.Align.CENTER); mbtn.set_popover(pop)

    artist_id=str(track.get("ART_ID") or track.get("artist",{}).get("id",""))
    artist_name=artist

    b1=Gtk.Button(label="＋  Add to playlist"); b1.add_css_class("flat")
    def on_addpl(b,t=tid,p=pop,a=app):
        p.popdown()
        if a: a._show_pl_dialog(t)
    b1.connect("clicked",on_addpl); mbox.append(b1)

    if tid:
        bmix=Gtk.Button(label="Mix from this track"); bmix.add_css_class("flat")
        def on_mix(b,t=tid,p=pop,a=app):
            p.popdown()
            if not a: return
            def do():
                try:
                    mixes=dz_track_mix(t)
                    if mixes:
                        nq=[norm(x) for x in mixes]
                        GLib.idle_add(lambda:([setattr(a,"queue",nq),setattr(a,"queue_idx",0),a._play(nq[0])]))
                except Exception as e: GLib.idle_add(lambda:a._err(f"Mix: {e}"))
            threading.Thread(target=do,daemon=True).start()
        bmix.connect("clicked",on_mix); mbox.append(bmix)

    if artist_id:
        b2=Gtk.Button(label=f"👤  {artist_name}"); b2.add_css_class("flat")
        def on_art(b,aid=artist_id,an=artist_name,p=pop,a=app):
            p.popdown()
            if a: a._open_artist(aid,an)
        b2.connect("clicked",on_art); mbox.append(b2)

    box.append(mbtn)
    row.set_child(box); return row

def col_header(show_album=True):
    box=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=0)
    box.set_margin_start(58); box.set_margin_end(8); box.set_margin_top(4); box.set_margin_bottom(4)
    t=Gtk.Label(label="TITLE"); t.set_hexpand(True); t.set_halign(Gtk.Align.START); t.add_css_class("col-header")
    box.append(t)
    if show_album:
        a=Gtk.Label(label="ALBUM"); a.set_width_chars(18); a.set_halign(Gtk.Align.START)
        a.add_css_class("col-header"); a.set_margin_end(12); box.append(a)
    d=Gtk.Label(label="DURATION"); d.add_css_class("col-header"); d.set_margin_end(36)
    box.append(d); return box

# ── Collection page (playlist / album) ────────────────────────────────────────
def make_collection_page(title, creator, nb, duration_min, img_url, tracks, queue, app, kind=None, item_id=None):
    """Page style Deezer pour playlist ou album."""
    outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)

    # Header
    hdr=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=20)
    hdr.set_margin_top(24); hdr.set_margin_bottom(16); hdr.set_margin_start(20); hdr.set_margin_end(20)

    frm,pic=make_pic(180); load_pic_async(img_url,pic,180); hdr.append(frm)

    info=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8); info.set_valign(Gtk.Align.END)
    tl=Gtk.Label(label=title); tl.set_css_classes(["page-title"]); tl.set_halign(Gtk.Align.START)
    tl.set_wrap(True); tl.set_xalign(0)
    info.append(tl)
    if creator:
        cl=Gtk.Label(label=creator); cl.set_halign(Gtk.Align.START); cl.add_css_class("dim-label"); info.append(cl)
    meta=Gtk.Label(label=f"{nb} tracks · {duration_min} min")
    meta.set_halign(Gtk.Align.START); meta.add_css_class("dim-label"); info.append(meta)

    # Play button
    play_row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12)
    play_btn=Gtk.Button(); play_btn.set_icon_name("media-playback-start-symbolic")
    play_btn.set_css_classes(["suggested-action","circular"]); play_btn.set_size_request(52,52)
    def on_play(b,q=queue,a=app):
        if q:
            a.queue=q; a.queue_idx=0; a._play(q[0])
    play_btn.connect("clicked",on_play); play_row.append(play_btn)
    # Like album (si kind=="album")
    if kind=="album" and item_id:
        like_alb_btn=Gtk.Button(); like_alb_btn.set_icon_name("emblem-favorite-symbolic")
        like_alb_btn.set_css_classes(["flat","circular"]); like_alb_btn.set_tooltip_text("Like this album")
        def on_like_alb(b,aid=item_id):
            if "accent" in b.get_css_classes():
                b.remove_css_class("accent"); b.set_icon_name("emblem-favorite-symbolic")
                threading.Thread(target=lambda:dz_unlike_album(aid),daemon=True).start()
            else:
                b.add_css_class("accent"); b.set_icon_name("starred-symbolic")
                threading.Thread(target=lambda:dz_like_album(aid),daemon=True).start()
        like_alb_btn.connect("clicked",on_like_alb); play_row.append(like_alb_btn)
    # Mix depuis premier titre
    if queue and app:
        mix_btn=Gtk.Button(label="Mix"); mix_btn.set_css_classes(["pill","flat"])
        mix_btn.set_tooltip_text("Start a mix from this track")
        def on_mix(b,q=queue,a=app):
            tid=str(q[0].get("SNG_ID") or q[0].get("id",""))
            def do():
                try:
                    tracks_mix=dz_track_mix(tid)
                    if tracks_mix:
                        nq=[norm(t) for t in tracks_mix]
                        GLib.idle_add(lambda:([setattr(a,"queue",nq),setattr(a,"queue_idx",0),a._play(nq[0])]))
                except Exception as e: GLib.idle_add(lambda:a._err(f"Mix: {e}"))
            threading.Thread(target=do,daemon=True).start()
        mix_btn.connect("clicked",on_mix); play_row.append(mix_btn)
    info.append(play_row); hdr.append(info); outer.append(hdr)
    outer.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    # Col headers
    outer.append(col_header(show_album=True))
    outer.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    # Track list
    sc=Gtk.ScrolledWindow(); sc.set_vexpand(True)
    lb=Gtk.ListBox(); lb.add_css_class("boxed-list")
    lb.set_margin_top(4); lb.set_margin_bottom(12)
    lb.set_margin_start(8); lb.set_margin_end(8)
    def on_row(listbox,row,q=queue,a=app):
        t=norm(row.item)
        try: idx=next(i for i,x in enumerate(q) if str(x.get("SNG_ID"))==str(t.get("SNG_ID")))
        except: idx=0
        a.queue=q; a.queue_idx=idx; a._play(t)
    lb.connect("row-activated",on_row)
    for t in tracks:
        lb.append(make_track_row(t,app,show_album_col=True))
    sc.set_child(lb); outer.append(sc)
    return outer

# ── App ────────────────────────────────────────────────────────────────────────
class OpenDeez(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.opendeez.app")
        self.connect("activate",self.on_activate)
        self.current_proc=None; self.queue=[]; self.queue_idx=-1
        self.cfg=load_config(); self._cur_file=None; self._playing=False
        self._duration=0; self._elapsed=0; self._play_start=0; self._seek_timer=None
        self._username=""; self._liked_ids=set(); self._seek_frac=0.0; self._seek_da=None

    def on_activate(self,app):
        apply_css()
        self.win=Adw.ApplicationWindow(application=app)
        self.win.set_title("OpenDeez"); self.win.set_default_size(1040,720)
        self.win.set_content(self._build_ui()); self.win.present()
        self.win.connect("close-request",self._on_close)
        if arl:=self.cfg.get("arl",""): self._do_login(arl)

    def _on_close(self,_):
        if self.current_proc:
            try: self.current_proc.terminate(); self.current_proc.wait(timeout=2)
            except: pass
        return False

    # ── UI root ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.root_stack=Gtk.Stack(); self.root_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.root_stack.add_named(self._build_login(),"login")
        self.root_stack.add_named(self._build_main(), "main")
        return self.root_stack

    # ── Login ──────────────────────────────────────────────────────────────────
    def _build_login(self):
        tb=Adw.ToolbarView(); hdr=Adw.HeaderBar(); hdr.set_show_end_title_buttons(False); tb.add_top_bar(hdr)
        clamp=Adw.Clamp(); clamp.set_maximum_size(440); clamp.set_valign(Gtk.Align.CENTER); clamp.set_vexpand(True)
        out=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20)
        out.set_margin_top(48); out.set_margin_bottom(48); out.set_margin_start(24); out.set_margin_end(24)
        ic=Gtk.Image.new_from_icon_name("audio-headphones-symbolic"); ic.set_pixel_size(72); ic.add_css_class("dim-label")
        out.append(ic)
        tl=Gtk.Label(label="OpenDeez"); tl.set_css_classes(["title-1"]); out.append(tl)
        st=Gtk.Label(label="Open source Deezer player"); st.add_css_class("dim-label"); out.append(st)

        ec=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0); ec.add_css_class("card")
        er=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12)
        er.set_margin_top(12); er.set_margin_bottom(12); er.set_margin_start(16); er.set_margin_end(16)
        el=Gtk.Label(label="Email"); el.set_width_chars(10); el.set_halign(Gtk.Align.START); el.add_css_class("dim-label")
        self.email_e=Gtk.Entry(); self.email_e.set_placeholder_text("your@email.com"); self.email_e.set_hexpand(True)
        er.append(el); er.append(self.email_e); ec.append(er)
        ec.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        pr=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12)
        pr.set_margin_top(12); pr.set_margin_bottom(12); pr.set_margin_start(16); pr.set_margin_end(16)
        pl=Gtk.Label(label="Password"); pl.set_width_chars(10); pl.set_halign(Gtk.Align.START); pl.add_css_class("dim-label")
        self.pwd_e=Gtk.Entry(); self.pwd_e.set_visibility(False); self.pwd_e.set_placeholder_text("••••••••"); self.pwd_e.set_hexpand(True)
        self.pwd_e.connect("activate",self._on_login_email); pr.append(pl); pr.append(self.pwd_e); ec.append(pr)
        out.append(ec)
        self.login_btn=Gtk.Button(label="Sign in"); self.login_btn.set_css_classes(["suggested-action","pill"])
        self.login_btn.connect("clicked",self._on_login_email); out.append(self.login_btn)

        sep=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        sl=Gtk.Separator(); sl.set_hexpand(True); sl.set_valign(Gtk.Align.CENTER)
        sr=Gtk.Separator(); sr.set_hexpand(True); sr.set_valign(Gtk.Align.CENTER)
        sep.append(sl); sep.append(Gtk.Label(label="or")); sep.append(sr); out.append(sep)

        ac=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0); ac.add_css_class("card")
        ar=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12)
        ar.set_margin_top(12); ar.set_margin_bottom(12); ar.set_margin_start(16); ar.set_margin_end(16)
        al=Gtk.Label(label="ARL"); al.set_width_chars(10); al.set_halign(Gtk.Align.START); al.add_css_class("dim-label")
        self.arl_e=Gtk.Entry(); self.arl_e.set_visibility(False); self.arl_e.set_placeholder_text("ARL cookie"); self.arl_e.set_hexpand(True)
        self.arl_e.connect("activate",self._on_login_arl); ar.append(al); ar.append(self.arl_e); ac.append(ar)
        out.append(ac)
        ab=Gtk.Button(label="Sign in with ARL"); ab.set_css_classes(["pill"]); ab.connect("clicked",self._on_login_arl); out.append(ab)

        if ff:=dz_arl_from_firefox():
            fb=Gtk.Button(label="Use Firefox account"); fb.set_css_classes(["pill"])
            fb.connect("clicked",lambda _:self._do_login(ff)); out.append(fb)

        self.login_status=Gtk.Label(label=""); self.login_status.add_css_class("dim-label"); out.append(self.login_status)
        clamp.set_child(out); sc=Gtk.ScrolledWindow(); sc.set_child(clamp); sc.set_vexpand(True); tb.set_content(sc)
        return tb

    # ── Main ───────────────────────────────────────────────────────────────────
    def _build_main(self):
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        self.split=Adw.NavigationSplitView()

        # Sidebar
        sbp=Adw.NavigationPage(); sbp.set_title("OpenDeez")
        sbt=Adw.ToolbarView(); sbt.add_top_bar(Adw.HeaderBar())
        sbl=Gtk.ListBox(); sbl.add_css_class("navigation-sidebar")
        sbl.set_selection_mode(Gtk.SelectionMode.SINGLE); sbl.connect("row-activated",self._on_sidebar)
        for icon,label,name in [
            ("go-home-symbolic","Home","home"),
            ("media-playlist-shuffle-symbolic","Flow","flow"),
            ("starred-symbolic","Favorites","favorites"),
            ("system-search-symbolic","Search","search"),
        ]:
            r=Gtk.ListBoxRow(); r.page_name=name
            b=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12)
            b.set_margin_top(10); b.set_margin_bottom(10); b.set_margin_start(14); b.set_margin_end(14)
            b.append(Gtk.Image.new_from_icon_name(icon))
            lb=Gtk.Label(label=label); lb.set_halign(Gtk.Align.START); b.append(lb); r.set_child(b); sbl.append(r)
        ss=Gtk.ScrolledWindow(); ss.set_child(sbl); ss.set_vexpand(True); sbt.set_content(ss); sbp.set_child(sbt)
        self.split.set_sidebar(sbp)

        # Content pane
        ctp=Adw.NavigationPage(); ctp.set_title("OpenDeez")
        ctt=Adw.ToolbarView(); cth=Adw.HeaderBar()
        self.search_e=Gtk.SearchEntry(); self.search_e.set_placeholder_text("Search…"); self.search_e.set_hexpand(True)
        self.search_e.connect("activate",self._on_search); cth.set_title_widget(self.search_e)

        # Quality menu
        qbox=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        qbox.set_margin_top(8); qbox.set_margin_bottom(8); qbox.set_margin_start(8); qbox.set_margin_end(8)
        qbox.append(Gtk.Label(label="Audio quality"))
        self.qpop=Gtk.Popover(); self.qpop.set_child(qbox)
        for q,l in [("MP3_128","MP3 128 kbps"),("MP3_320","MP3 320 (Premium)"),("FLAC","FLAC (Premium)")]:
            b=Gtk.Button(label=l); b.add_css_class("flat"); b.connect("clicked",self._set_quality,q); qbox.append(b)
        qbtn=Gtk.MenuButton(); qbtn.set_icon_name("audio-card-symbolic"); qbtn.set_tooltip_text("Quality"); qbtn.set_popover(self.qpop)
        cth.pack_end(qbtn)
        lgbtn=Gtk.Button(); lgbtn.set_icon_name("system-log-out-symbolic"); lgbtn.add_css_class("flat"); lgbtn.connect("clicked",self._on_logout)
        cth.pack_end(lgbtn); ctt.add_top_bar(cth)

        # Navigation stack (supports back navigation)
        self.nav_stack=Gtk.Stack(); self.nav_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT); self.nav_stack.set_vexpand(True)
        self._page_history=[]

        self.nav_stack.add_named(self._build_home_page(),    "home")
        self.nav_stack.add_named(self._build_flow_page(),    "flow")
        self.nav_stack.add_named(self._build_favs_page(),    "favorites")
        self.nav_stack.add_named(self._build_search_page(),  "search")

        empty=Adw.StatusPage(); empty.set_icon_name("audio-headphones-symbolic")
        empty.set_title("OpenDeez"); empty.set_description("Select a section")
        self.nav_stack.add_named(empty,"empty")

        ctt.set_content(self.nav_stack); ctp.set_child(ctt); self.split.set_content(ctp)
        self.split.set_vexpand(True)
        self.player_spinner=Gtk.Spinner()

        player_bar=self._build_player()
        player_bar.set_vexpand(False)
        root.append(self.split)
        root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        root.append(player_bar)
        return root

    # ── Pages ──────────────────────────────────────────────────────────────────
    def _build_home_page(self):
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True)
        self.home_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        self.home_box.set_margin_bottom(16); sc.set_child(self.home_box); return sc

    def _build_flow_page(self):
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True)
        self.flow_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        self.flow_box.set_margin_bottom(16); sc.set_child(self.flow_box); return sc

    def _build_favs_page(self):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        self.fav_tabs=Gtk.StackSwitcher(); self.fav_stack=Gtk.Stack()
        self.fav_tabs.set_stack(self.fav_stack); self.fav_tabs.set_margin_top(8); self.fav_tabs.set_margin_bottom(4)
        self.fav_tabs.set_halign(Gtk.Align.CENTER)
        # Titres
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True)
        self.fav_tracks_lb=Gtk.ListBox(); self.fav_tracks_lb.add_css_class("boxed-list")
        self.fav_tracks_lb.set_margin_top(4); self.fav_tracks_lb.set_margin_bottom(8)
        self.fav_tracks_lb.set_margin_start(8); self.fav_tracks_lb.set_margin_end(8)
        self.fav_tracks_lb.connect("row-activated",self._on_fav_track)
        sc.set_child(self.fav_tracks_lb); self.fav_stack.add_titled(sc,"ft","Tracks")
        # Albums
        sc2=Gtk.ScrolledWindow(); sc2.set_vexpand(True)
        self.fav_albums_fb=Gtk.FlowBox(); self.fav_albums_fb.set_max_children_per_line(10)
        self.fav_albums_fb.set_min_children_per_line(3); self.fav_albums_fb.set_selection_mode(Gtk.SelectionMode.NONE)
        self.fav_albums_fb.set_margin_top(8); self.fav_albums_fb.set_margin_bottom(8)
        self.fav_albums_fb.set_margin_start(12); self.fav_albums_fb.set_margin_end(12)
        self.fav_albums_fb.set_column_spacing(8); self.fav_albums_fb.set_row_spacing(8)
        sc2.set_child(self.fav_albums_fb); self.fav_stack.add_titled(sc2,"fa","Albums")
        # Artistes
        sc3=Gtk.ScrolledWindow(); sc3.set_vexpand(True)
        self.fav_artists_fb=Gtk.FlowBox(); self.fav_artists_fb.set_max_children_per_line(10)
        self.fav_artists_fb.set_min_children_per_line(3); self.fav_artists_fb.set_selection_mode(Gtk.SelectionMode.NONE)
        self.fav_artists_fb.set_margin_top(8); self.fav_artists_fb.set_margin_bottom(8)
        self.fav_artists_fb.set_margin_start(12); self.fav_artists_fb.set_margin_end(12)
        self.fav_artists_fb.set_column_spacing(8); self.fav_artists_fb.set_row_spacing(8)
        sc3.set_child(self.fav_artists_fb); self.fav_stack.add_titled(sc3,"far","Artists")
        # Playlists
        pl_outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0); pl_outer.set_vexpand(True)
        pl_bar=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        pl_bar.set_margin_top(8); pl_bar.set_margin_bottom(4); pl_bar.set_margin_start(12); pl_bar.set_margin_end(12)
        new_pl_btn=Gtk.Button(label="＋  New playlist"); new_pl_btn.set_css_classes(["suggested-action","pill"])
        new_pl_btn.connect("clicked",self._on_create_playlist)
        import_pl_btn=Gtk.Button(label="Import"); import_pl_btn.set_css_classes(["pill"])
        import_pl_btn.connect("clicked",self._on_import_playlist)
        pl_bar.append(new_pl_btn); pl_bar.append(import_pl_btn); pl_outer.append(pl_bar)
        sc4=Gtk.ScrolledWindow(); sc4.set_vexpand(True)
        self.fav_pls_fb=Gtk.FlowBox(); self.fav_pls_fb.set_max_children_per_line(10)
        self.fav_pls_fb.set_min_children_per_line(3); self.fav_pls_fb.set_selection_mode(Gtk.SelectionMode.NONE)
        self.fav_pls_fb.set_margin_top(8); self.fav_pls_fb.set_margin_bottom(8)
        self.fav_pls_fb.set_margin_start(12); self.fav_pls_fb.set_margin_end(12)
        self.fav_pls_fb.set_column_spacing(8); self.fav_pls_fb.set_row_spacing(8)
        sc4.set_child(self.fav_pls_fb); pl_outer.append(sc4)
        self.fav_stack.add_titled(pl_outer,"fp","Playlists")
        box.append(self.fav_tabs); box.append(self.fav_stack); return box

    def _build_search_page(self):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        self.search_tabs=Gtk.StackSwitcher(); self.search_stack=Gtk.Stack()
        self.search_tabs.set_stack(self.search_stack); self.search_tabs.set_margin_top(8); self.search_tabs.set_margin_bottom(4)
        self.search_tabs.set_halign(Gtk.Align.CENTER)
        # Titres
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True)
        self.search_lb=Gtk.ListBox(); self.search_lb.add_css_class("boxed-list")
        self.search_lb.set_margin_top(4); self.search_lb.set_margin_bottom(8)
        self.search_lb.set_margin_start(8); self.search_lb.set_margin_end(8)
        self.search_lb.connect("row-activated",self._on_search_track); sc.set_child(self.search_lb)
        self.search_stack.add_titled(sc,"st","Tracks")
        # Albums
        sc2=Gtk.ScrolledWindow(); sc2.set_vexpand(True)
        self.search_albums_fb=Gtk.FlowBox(); self.search_albums_fb.set_max_children_per_line(10)
        self.search_albums_fb.set_min_children_per_line(3); self.search_albums_fb.set_selection_mode(Gtk.SelectionMode.NONE)
        self.search_albums_fb.set_margin_top(8); self.search_albums_fb.set_margin_bottom(8)
        self.search_albums_fb.set_margin_start(12); self.search_albums_fb.set_margin_end(12)
        self.search_albums_fb.set_column_spacing(8); self.search_albums_fb.set_row_spacing(8)
        sc2.set_child(self.search_albums_fb); self.search_stack.add_titled(sc2,"sa","Albums")
        # Artistes
        sc3=Gtk.ScrolledWindow(); sc3.set_vexpand(True)
        self.search_artists_fb=Gtk.FlowBox(); self.search_artists_fb.set_max_children_per_line(10)
        self.search_artists_fb.set_min_children_per_line(3); self.search_artists_fb.set_selection_mode(Gtk.SelectionMode.NONE)
        self.search_artists_fb.set_margin_top(8); self.search_artists_fb.set_margin_bottom(8)
        self.search_artists_fb.set_margin_start(12); self.search_artists_fb.set_margin_end(12)
        self.search_artists_fb.set_column_spacing(8); self.search_artists_fb.set_row_spacing(8)
        sc3.set_child(self.search_artists_fb); self.search_stack.add_titled(sc3,"sar","Artists")
        box.append(self.search_tabs); box.append(self.search_stack); return box

    # ── Player ─────────────────────────────────────────────────────────────────
    def _build_player(self):
        """Lecteur compact une seule ligne style Deezer."""
        bar=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        bar.add_css_class("player-bar"); bar.set_vexpand(False)

        # Barre de progression seekable — DrawingArea 4px
        self._seek_frac=0.0
        da=Gtk.DrawingArea()
        da.set_size_request(-1,4); da.set_hexpand(True); da.set_vexpand(False)
        da.set_valign(Gtk.Align.START)
        da.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        def on_draw(widget,cr,w,h):
            cr.set_source_rgba(0.5,0.5,0.5,0.15); cr.rectangle(0,0,w,h); cr.fill()
            cr.set_source_rgba(0.18,0.52,0.96,1.0)
            cr.rectangle(0,0,w*self._seek_frac,h); cr.fill()
        da.set_draw_func(on_draw)
        gc=Gtk.GestureClick(); gc.set_button(1)
        def on_press(gesture,n,x,y):
            w=da.get_width()
            if w>0: self._seek_to(x/w)
        gc.connect("pressed",on_press)
        gd=Gtk.GestureDrag()
        def on_drag(gesture,dx,dy):
            _ok,sx,sy=gesture.get_start_point(); w=da.get_width()
            if w>0: self._seek_to((sx+dx)/w)
        gd.connect("drag-update",on_drag)
        da.add_controller(gc); da.add_controller(gd)
        self.prog_bar=da; self._seek_da=da
        bar.append(da)
        self.prog=da  # alias

        # Ligne unique
        row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        row.set_margin_top(4); row.set_margin_bottom(4)
        row.set_margin_start(12); row.set_margin_end(12)
        row.set_vexpand(False)

        # Gauche : cover + info
        left=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        left.set_hexpand(True); left.set_halign(Gtk.Align.START); left.set_valign(Gtk.Align.CENTER)
        self.p_cover_frm,self.p_cover_pic=make_pic(28)
        left.append(self.p_cover_frm)
        ib=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0); ib.set_valign(Gtk.Align.CENTER)
        self.p_title=Gtk.Label(label="Nothing playing")
        self.p_title.set_halign(Gtk.Align.START); self.p_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.p_title.set_css_classes(["now-title"]); self.p_title.set_max_width_chars(26)
        self.p_artist=Gtk.Label(label="")
        self.p_artist.set_halign(Gtk.Align.START); self.p_artist.set_ellipsize(Pango.EllipsizeMode.END)
        self.p_artist.set_css_classes(["now-artist","dim-label"]); self.p_artist.set_max_width_chars(26)
        ib.append(self.p_title); ib.append(self.p_artist); left.append(ib)
        like_btn=Gtk.Button(); like_btn.set_icon_name("emblem-favorite-symbolic")
        like_btn.set_css_classes(["flat","circular"]); like_btn.set_valign(Gtk.Align.CENTER)
        self._player_like_btn=like_btn
        def _like(_):
            if self.queue and 0<=self.queue_idx<len(self.queue):
                t=self.queue[self.queue_idx]
                tid=str(t.get("SNG_ID") or t.get("id",""))
                if not tid: return
                if tid in self._liked_ids:
                    self._liked_ids.discard(tid)
                    like_btn.set_icon_name("emblem-favorite-symbolic")
                    like_btn.remove_css_class("accent")
                    def do_unlike(t=tid):
                        dz_unlike(t); GLib.idle_add(self._refresh_fav_tracks)
                    threading.Thread(target=do_unlike,daemon=True).start()
                else:
                    self._liked_ids.add(tid)
                    like_btn.set_icon_name("starred-symbolic")
                    like_btn.add_css_class("accent")
                    def do_like(t=tid):
                        dz_like(t); GLib.idle_add(self._refresh_fav_tracks)
                    threading.Thread(target=do_like,daemon=True).start()
        like_btn.connect("clicked",_like); left.append(like_btn)
        row.append(left)

        # Centre : prev + play + next + spinner
        centre=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=2)
        centre.set_halign(Gtk.Align.CENTER); centre.set_valign(Gtk.Align.CENTER)
        self.btn_prev=Gtk.Button(); self.btn_prev.set_icon_name("media-skip-backward-symbolic")
        self.btn_prev.set_css_classes(["circular","flat","player-btn"]); self.btn_prev.connect("clicked",self._on_prev); self.btn_prev.set_sensitive(False)
        self.btn_play=Gtk.Button(); self.btn_play.set_icon_name("media-playback-start-symbolic")
        self.btn_play.set_css_classes(["circular","suggested-action","player-btn-play"])
        self.btn_play.connect("clicked",self._on_playpause); self.btn_play.set_sensitive(False)
        self.btn_next=Gtk.Button(); self.btn_next.set_icon_name("media-skip-forward-symbolic")
        self.btn_next.set_css_classes(["circular","flat","player-btn"]); self.btn_next.connect("clicked",self._on_next); self.btn_next.set_sensitive(False)
        self.player_spinner=Gtk.Spinner()
        for w in [self.btn_prev,self.btn_play,self.btn_next,self.player_spinner]: centre.append(w)
        row.append(centre)

        # Droite : temps + queue
        right=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=6)
        right.set_hexpand(True); right.set_halign(Gtk.Align.END); right.set_valign(Gtk.Align.CENTER)
        self.t_cur=Gtk.Label(label="0:00"); self.t_cur.set_css_classes(["caption","dim-label"]); self.t_cur.set_width_chars(5)
        sep_t=Gtk.Label(label="/"); sep_t.add_css_class("dim-label")
        self.t_tot=Gtk.Label(label="0:00"); self.t_tot.set_css_classes(["caption","dim-label"]); self.t_tot.set_width_chars(5)
        queue_btn=Gtk.MenuButton(); queue_btn.set_icon_name("view-list-ordered-symbolic")
        queue_btn.set_css_classes(["flat","circular"]); queue_btn.set_tooltip_text("Queue")
        self.queue_pop=Gtk.Popover(); queue_btn.set_popover(self.queue_pop)
        self.queue_pop.connect("show",self._refresh_queue_pop)
        qpop_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0); qpop_box.set_size_request(320,1)
        self.queue_lb=Gtk.ListBox(); self.queue_lb.add_css_class("boxed-list")
        self.queue_lb.set_margin_top(4); self.queue_lb.set_margin_bottom(4)
        self.queue_lb.set_margin_start(8); self.queue_lb.set_margin_end(8)
        self.queue_lb.connect("row-activated",self._on_queue_row)
        qsc=Gtk.ScrolledWindow(); qsc.set_min_content_height(100); qsc.set_max_content_height(360)
        qsc.set_child(self.queue_lb); qpop_box.append(qsc); self.queue_pop.set_child(qpop_box)
        lyrics_btn=Gtk.Button(label="Lyrics"); lyrics_btn.set_css_classes(["flat","pill"])
        lyrics_btn.set_tooltip_text("Show lyrics")
        lyrics_btn.connect("clicked",self._on_lyrics)
        self._lyrics_btn=lyrics_btn
        for w in [self.t_cur,sep_t,self.t_tot,lyrics_btn,queue_btn]: right.append(w)
        row.append(right)
        bar.append(row); return bar

    def _refresh_queue_pop(self,_):
        _clr(self.queue_lb)
        for i,t in enumerate(self.queue):
            row=Gtk.ListBoxRow(); row.queue_idx=i
            b=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
            b.set_margin_top(8); b.set_margin_bottom(8); b.set_margin_start(12); b.set_margin_end(12)
            frm,pic=make_pic(32); url=cover_url(t,"56x56"); load_pic_async(url,pic,32); b.append(frm)
            vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=1); vb.set_hexpand(True)
            tl=Gtk.Label(label=t.get("SNG_TITLE") or t.get("title","?")); tl.set_halign(Gtk.Align.START); tl.set_ellipsize(Pango.EllipsizeMode.END)
            al=Gtk.Label(label=t.get("ART_NAME") or t.get("artist",{}).get("name","")); al.set_halign(Gtk.Align.START)
            al.set_css_classes(["caption","dim-label"]); al.set_ellipsize(Pango.EllipsizeMode.END)
            vb.append(tl); vb.append(al); b.append(vb)
            if i==self.queue_idx:
                ic=Gtk.Image.new_from_icon_name("media-playback-start-symbolic"); ic.add_css_class("accent"); b.append(ic)
            row.set_child(b); self.queue_lb.append(row)

    def _on_queue_row(self,_,row):
        self.queue_pop.popdown(); self.queue_idx=row.queue_idx; self._play(self.queue[self.queue_idx])

    # ── Auth ───────────────────────────────────────────────────────────────────
    def _on_login_email(self,_):
        email=self.email_e.get_text().strip(); pwd=self.pwd_e.get_text().strip()
        if not email or not pwd: self.login_status.set_label("Enter your email and password"); return
        self.login_status.set_label("Signing in…"); self.login_btn.set_sensitive(False)
        def do():
            try:
                s=requests.Session(); s.headers.update({"User-Agent":"Mozilla/5.0"})
                s.get("https://www.deezer.com/")
                sid=s.cookies.get("sid","")
                r=s.post("https://auth.deezer.com/login/arl",params={"jo":"p","rto":"c","i":"c"},
                          json={"login":email,"password":hashlib.md5(pwd.encode()).hexdigest(),"sid":sid})
                arl=r.json().get("arl") if r.status_code==200 else None
                if not arl: raise ValueError("Login échoué — essaie avec l'ARL")
                GLib.idle_add(self._do_login,arl)
            except Exception as e:
                GLib.idle_add(self.login_status.set_label,f"Error: {e}")
                GLib.idle_add(self.login_btn.set_sensitive,True)
        threading.Thread(target=do,daemon=True).start()

    def _on_login_arl(self,_):
        arl=self.arl_e.get_text().strip()
        if not arl: self.login_status.set_label("Enter your ARL"); return
        self._do_login(arl)

    def _do_login(self,arl):
        self.login_status.set_label("Signing in…")
        def do():
            try:
                user=dz_init(arl); self.cfg["arl"]=arl; save_config(self.cfg)
                GLib.idle_add(self._login_ok,user.get("BLOG_NAME","?"))
            except Exception as e:
                GLib.idle_add(self.login_status.set_label,f"Error: {e}")
                GLib.idle_add(self.login_btn.set_sensitive,True)
        threading.Thread(target=do,daemon=True).start()

    def _login_ok(self,name):
        self._username=name
        self.login_status.set_label(""); self.root_stack.set_visible_child_name("main"); self._load_home()
        threading.Thread(target=self._fetch_liked_ids,daemon=True).start()

    def _refresh_fav_tracks(self):
        def do():
            try:
                tracks=dz_liked_tracks()
                GLib.idle_add(self._update_fav_tracks,tracks)
            except: pass
        threading.Thread(target=do,daemon=True).start()

    def _update_fav_tracks(self,tracks):
        _clr(self.fav_tracks_lb)
        self._fav_q=[norm(t) for t in tracks]
        for t in tracks: self.fav_tracks_lb.append(make_track_row(t,self,show_album_col=True))

    def _fetch_liked_ids(self):
        try:
            ids=dz_liked_ids(); GLib.idle_add(self._set_liked_ids,ids)
        except: pass

    def _set_liked_ids(self,ids):
        self._liked_ids=ids

    def _on_logout(self,_):
        self.cfg.pop("arl",None); save_config(self.cfg)
        if self.current_proc:
            try: self.current_proc.terminate()
            except: pass
        self.root_stack.set_visible_child_name("login")

    # ── Navigation ─────────────────────────────────────────────────────────────
    def _go(self,page_name):
        """Navigate to a named page, pushing current to history."""
        current=self.nav_stack.get_visible_child_name()
        if current and current!=page_name:
            self._page_history.append(current)
        self.nav_stack.set_visible_child_name(page_name)

    def _go_dynamic(self,widget,name):
        """Add or replace a dynamic page and navigate to it."""
        current=self.nav_stack.get_visible_child_name()
        if current: self._page_history.append(current)
        existing=self.nav_stack.get_child_by_name(name)
        if existing: self.nav_stack.remove(existing)
        self.nav_stack.add_named(widget,name)
        self.nav_stack.set_visible_child_name(name)

    def _on_sidebar(self,_,row):
        name=row.page_name
        if name=="search":
            self._go("search"); self.search_e.grab_focus()
        elif name=="home":   self._load_home()
        elif name=="flow":   self._load_flow()
        elif name=="favorites":
            if self.nav_stack.get_visible_child_name()=="favorites":
                return  # déjà sur la page, ne pas recharger
            self._load_favs()

    # ── Home ───────────────────────────────────────────────────────────────────
    def _load_home(self):
        self._go("home"); _clr(self.home_box)
        sp=Gtk.Spinner(); sp.start(); sp.set_margin_top(60); sp.set_halign(Gtk.Align.CENTER)
        self.home_box.append(sp)
        def do():
            try:
                pls=dz_playlists()
                history=dz_history()
                flow=dz_flow()
                releases=dz_releases()
                reco=dz_recommended_albums()
                GLib.idle_add(self._show_home,pls,history,flow,releases,reco)
            except Exception as e: GLib.idle_add(self._err,f"Home: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _make_section(self,title):
        """Section header + container box."""
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        box.add_css_class("home-section")
        hdr=Gtk.Label(label=title); hdr.set_halign(Gtk.Align.START)
        hdr.set_css_classes(["section-title"])
        hdr.set_margin_start(16); hdr.set_margin_top(18); hdr.set_margin_bottom(8)
        box.append(hdr)
        return box

    def _make_dense_grid(self,items,build_fn,cols=5):
        fb=Gtk.FlowBox()
        fb.add_css_class("grid-fb")
        fb.set_homogeneous(False)
        fb.set_max_children_per_line(cols)
        fb.set_min_children_per_line(cols)
        fb.set_selection_mode(Gtk.SelectionMode.NONE)
        fb.set_halign(Gtk.Align.START)
        fb.set_margin_start(12); fb.set_margin_end(12); fb.set_margin_bottom(4)
        fb.set_column_spacing(8); fb.set_row_spacing(8)
        for it in items:
            c=build_fn(it)
            if c: fb.append(c)
        return fb

    def _make_quick_row(self,items,build_fn):
        """2 colonnes de boutons texte rapides style Spotify (Bonne humeur, Chill...)."""
        grid=Gtk.Grid(); grid.set_column_spacing(8); grid.set_row_spacing(8)
        grid.set_margin_start(12); grid.set_margin_end(12); grid.set_margin_bottom(4)
        for i,it in enumerate(items[:6]):
            w=build_fn(it)
            if w: grid.attach(w,i%2,i//2,1,1)
        return grid

    def _show_home(self,pls,history,flow,releases,reco):
        _clr(self.home_box)
        name=getattr(self,"_username","")
        # ── Salutation ─────────────────────────────────────────────────────────
        greet=Gtk.Label(label=f"Hello, {name}" if name else "Hello")
        greet.set_css_classes(["title-1"]); greet.set_halign(Gtk.Align.START)
        greet.set_margin_start(16); greet.set_margin_top(20); greet.set_margin_bottom(12)
        self.home_box.append(greet)

        # ── Raccourcis playlists (grille 2 col) ─────────────────────────────────
        if pls:
            quick_box=Gtk.Grid(); quick_box.set_column_spacing(8); quick_box.set_row_spacing(8)
            quick_box.set_margin_start(12); quick_box.set_margin_end(12); quick_box.set_margin_bottom(16)
            for i,p in enumerate(pls[:6]):
                pid=str(p.get("PLAYLIST_ID") or p.get("id",""))
                t=p.get("TITLE") or p.get("title","Playlist")
                img=playlist_img_url(p)
                btn=Gtk.Button(); btn.add_css_class("quick-row-btn")
                row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=10)
                row.set_size_request(260,48)
                frm,pic=make_pic(44,False)
                frm.add_css_class("card-cover"); row.append(frm)
                lbl=Gtk.Label(label=t); lbl.set_halign(Gtk.Align.START)
                lbl.set_ellipsize(Pango.EllipsizeMode.END); lbl.set_max_width_chars(20)
                lbl.add_css_class("caption"); row.append(lbl)
                btn.set_child(row)
                def oc(b,pid=pid,t=t): self._open_playlist(pid,t)
                btn.connect("clicked",oc)
                load_pic_async(img,pic,44)
                quick_box.attach(btn,i%2,i//2,1,1)
            self.home_box.append(quick_box)

        # ── Récemment écoutés ───────────────────────────────────────────────────
        if history:
            self._history_q=[norm(t) for t in history]
            sec=self._make_section("Récemment écoutés")
            def hc(t):
                title=t.get("SNG_TITLE","?"); artist=t.get("ART_NAME","")
                img=cover_url(t,"250x250"); nt=norm(t)
                def oc(b,track=nt):
                    self.queue=self._history_q
                    self.queue_idx=next((i for i,q in enumerate(self._history_q) if str(q.get("SNG_ID"))==str(track.get("SNG_ID"))),0)
                    self._play(track)
                return make_card_btn(title,artist,img,120,False,oc)
            sec.append(self._make_dense_grid(history[:10],hc,5))
            self.home_box.append(sec)

        # ── Recommandés pour toi (Flow) ─────────────────────────────────────────
        if flow:
            self._flow_home_q=[norm(t) for t in flow]
            sec=self._make_section("Recommended for you")
            def fc(t):
                title=t.get("SNG_TITLE") or t.get("title","?")
                artist=t.get("ART_NAME") or t.get("artist",{}).get("name","")
                img=cover_url(t,"250x250"); nt=norm(t)
                def oc(b,track=nt):
                    self.queue=self._flow_home_q
                    self.queue_idx=next((i for i,q in enumerate(self._flow_home_q) if str(q.get("SNG_ID"))==str(track.get("SNG_ID"))),0)
                    self._play(track)
                return make_card_btn(title,artist,img,120,False,oc)
            sec.append(self._make_dense_grid(flow[:10],fc,5))
            self.home_box.append(sec)

        # ── Nouveautés ──────────────────────────────────────────────────────────
        if releases:
            sec=self._make_section("New releases")
            def rc(r):
                aid=r.get("id",""); t=r.get("title","?"); artist=r.get("artist",{}).get("name","")
                img=r.get("cover_medium") or r.get("cover_xl","")
                def oc(b,aid=aid,t=t): self._open_album(aid,t)
                return make_card_btn(t,artist,img,120,False,oc)
            sec.append(self._make_dense_grid(releases[:10],rc,5))
            self.home_box.append(sec)

        # ── Parce que tu aimes… ─────────────────────────────────────────────────
        if reco:
            sec=self._make_section("Because you like these artists")
            def recc(r):
                aid=r.get("id",""); t=r.get("title","?"); artist=r.get("artist",{}).get("name","")
                img=r.get("cover_medium") or r.get("cover_xl","")
                def oc(b,aid=aid,t=t): self._open_album(aid,t)
                return make_card_btn(t,artist,img,120,False,oc)
            sec.append(self._make_dense_grid(reco[:10],recc,5))
            self.home_box.append(sec)

    # ── Flow ───────────────────────────────────────────────────────────────────
    def _load_flow(self):
        self._go("flow"); _clr(self.flow_box)
        sp=Gtk.Spinner(); sp.start(); sp.set_margin_top(60); sp.set_halign(Gtk.Align.CENTER); self.flow_box.append(sp)
        def do():
            try: tracks=dz_flow(); GLib.idle_add(self._show_flow,tracks)
            except Exception as e: GLib.idle_add(self._err,f"Flow: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _show_flow(self,tracks):
        _clr(self.flow_box); self._flow_q=[norm(t) for t in tracks]
        # Page Flow : juste un bouton + description, pas de liste
        status=Adw.StatusPage()
        status.set_icon_name("media-playlist-shuffle-symbolic")
        status.set_title("Flow")
        status.set_description("An infinite, personalized mix based on your taste")
        btn=Gtk.Button(label="Play Flow")
        btn.set_css_classes(["suggested-action","pill"])
        btn.set_halign(Gtk.Align.CENTER)
        def on_flow(b):
            if self._flow_q:
                self.queue=self._flow_q; self.queue_idx=0; self._play(self._flow_q[0])
        btn.connect("clicked",on_flow)
        status.set_child(btn)
        self.flow_box.append(status)

    # ── Favoris ────────────────────────────────────────────────────────────────
    def _load_favs(self):
        self._go("favorites"); self.player_spinner.start()
        def do():
            try:
                tracks=dz_liked_tracks(); albums=dz_liked_albums(); artists=dz_liked_artists(); pls=dz_playlists()
                GLib.idle_add(self._show_favs,tracks,albums,artists,pls)
            except Exception as e: GLib.idle_add(self._err,f"Favorites: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _show_favs(self,tracks,albums,artists,pls):
        self.player_spinner.stop()
        _clr(self.fav_tracks_lb); _clr(self.fav_albums_fb); _clr(self.fav_artists_fb); _clr(self.fav_pls_fb)
        self._fav_q=[norm(t) for t in tracks]
        for t in tracks: self.fav_tracks_lb.append(make_track_row(t,self,show_album_col=True))
        for a in albums:
            aid=a.get("id",""); t=a.get("title","?"); art=a.get("artist",{}).get("name",""); img=a.get("cover_medium","")
            def oc(b,aid=aid,t=t): self._open_album(aid,t)
            self.fav_albums_fb.append(make_card_btn(t,art,img,120,False,oc))
        for a in artists:
            aid=a.get("id",""); name=a.get("name","?"); img=a.get("picture_medium","")
            def oc(b,aid=aid,name=name): self._open_artist(aid,name)
            self.fav_artists_fb.append(make_card_btn(name,None,img,110,True,oc))
        for p in pls:
            pid=str(p.get("PLAYLIST_ID") or p.get("id","")); t=p.get("TITLE") or p.get("title","Playlist")
            img=playlist_img_url(p)
            # Wrapper avec bouton modifier en overlay
            wrapper=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
            card=make_card_btn(t,None,img,120,False,lambda b,pid=pid,t=t:self._open_playlist(pid,t))
            edit_btn=Gtk.Button(label="✏"); edit_btn.set_css_classes(["flat","circular","caption"])
            edit_btn.set_halign(Gtk.Align.END); edit_btn.set_valign(Gtk.Align.START)
            edit_btn.set_tooltip_text("Edit playlist")
            edit_btn.connect("clicked",lambda b,pid=pid,t=t:self._on_edit_playlist(pid,t))
            top_row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=0)
            top_row.set_hexpand(True)
            spacer=Gtk.Box(); spacer.set_hexpand(True)
            top_row.append(spacer); top_row.append(edit_btn)
            wrapper.append(top_row); wrapper.append(card)
            self.fav_pls_fb.append(wrapper)

    def _on_fav_track(self,_,row):
        t=norm(row.item)
        try: idx=next(i for i,q in enumerate(self._fav_q) if str(q.get("SNG_ID"))==str(t.get("SNG_ID")))
        except: idx=0
        self.queue=self._fav_q; self.queue_idx=idx; self._play(t)

    # ── Search ─────────────────────────────────────────────────────────────────
    def _on_search(self,entry):
        q=entry.get_text().strip()
        if not q or not USER_ID: return
        self._go("search"); self.player_spinner.start()
        def do():
            try:
                tracks,albums,artists=dz_search_all(q)
                GLib.idle_add(self._show_search,tracks,albums,artists)
            except Exception as e: GLib.idle_add(self._err,f"Search: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _show_search(self,tracks,albums,artists):
        self.player_spinner.stop()
        _clr(self.search_lb); _clr(self.search_albums_fb); _clr(self.search_artists_fb)
        self._search_q=[norm(t) for t in tracks]
        for t in tracks: self.search_lb.append(make_track_row(t,self,show_album_col=True))
        for a in albums:
            aid=a.get("id",""); t=a.get("title","?"); art=a.get("artist",{}).get("name",""); img=a.get("cover_medium","")
            def oc(b,aid=aid,t=t): self._open_album(aid,t)
            self.search_albums_fb.append(make_card_btn(t,art,img,120,False,oc))
        for a in artists:
            aid=a.get("id",""); name=a.get("name","?"); img=a.get("picture_medium","")
            def oc(b,aid=aid,name=name): self._open_artist(aid,name)
            self.search_artists_fb.append(make_card_btn(name,None,img,110,True,oc))

    def _on_search_track(self,_,row):
        t=norm(row.item)
        try: idx=next(i for i,q in enumerate(self._search_q) if str(q.get("SNG_ID"))==str(t.get("SNG_ID")))
        except: idx=0
        self.queue=self._search_q; self.queue_idx=idx; self._play(t)

    # ── Open playlist / album / artist ─────────────────────────────────────────
    def _open_playlist(self,pid,title):
        self.player_spinner.start()
        def do():
            try:
                tracks=dz_playlist_tracks(pid); info=dz_playlist_info(pid)
                GLib.idle_add(self._show_collection,tracks,info,"playlist",title)
            except Exception as e: GLib.idle_add(self._err,f"Playlist: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _open_album(self,aid,title):
        self.player_spinner.start()
        def do():
            try:
                tracks=dz_album_tracks(aid); info=dz_album_info(aid)
                GLib.idle_add(self._show_collection,tracks,info,"album",title)
            except Exception as e: GLib.idle_add(self._err,f"Album: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _show_collection(self,tracks,info,kind,title):
        self.player_spinner.stop()
        queue=[norm(t) for t in tracks]
        self.queue=queue

        # Image
        if kind=="playlist":
            img=playlist_img_url(info)
            if not img:
                pid2=info.get("PLAYLIST_ID") or info.get("id","")
                img=f"https://api.deezer.com/playlist/{pid2}/image"
            creator=info.get("PARENT_USERNAME","")
            nb=info.get("NB_SONG",len(tracks))
        else:
            img=info.get("cover_medium","")
            creator=info.get("artist",{}).get("name","")
            nb=len(tracks)

        dur_min=sum(int(t.get("DURATION") or t.get("duration",0)) for t in tracks)//60
        item_id=str(info.get("id","") or info.get("ALB_ID","") or info.get("PLAYLIST_ID",""))
        page=make_collection_page(title,creator,nb,dur_min,img,tracks,queue,self,kind=kind,item_id=item_id)
        self._go_dynamic(page,f"col_{kind}_{title[:20]}")

    def _open_artist(self,aid,name):
        self.player_spinner.start()
        def do():
            try:
                top=dz_artist_top(aid); albums=dz_artist_albums(aid)
                GLib.idle_add(self._show_artist,top,albums,name,aid)
            except Exception as e: GLib.idle_add(self._err,f"Artist: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _show_artist(self,top,albums,name,aid):
        self.player_spinner.stop()
        q=[norm(t) for t in top]

        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)

        # Header artiste
        hdr=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=20)
        hdr.set_margin_top(24); hdr.set_margin_bottom(16); hdr.set_margin_start(20); hdr.set_margin_end(20)
        info_art=dz_artist_info(aid)
        img=info_art.get("picture_medium","")
        frm,pic=make_pic(120,circle=True); load_pic_async(img,pic,120); hdr.append(frm)
        ib=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6); ib.set_valign(Gtk.Align.CENTER)
        tl=Gtk.Label(label=name); tl.set_css_classes(["page-title"]); tl.set_halign(Gtk.Align.START); ib.append(tl)
        fans=info_art.get("nb_fan",0)
        if fans:
            fl=Gtk.Label(label=f"{fans:,} fans"); fl.add_css_class("dim-label"); fl.set_halign(Gtk.Align.START); ib.append(fl)
        play_btn=Gtk.Button(); play_btn.set_icon_name("media-playback-start-symbolic")
        play_btn.set_css_classes(["suggested-action","circular"]); play_btn.set_size_request(48,48)
        def on_play(b,queue=q): self.queue=queue; self.queue_idx=0; self._play(queue[0]) if queue else None
        play_btn.connect("clicked",on_play)
        # Like artiste
        like_art_btn=Gtk.Button(); like_art_btn.set_icon_name("emblem-favorite-symbolic")
        like_art_btn.set_css_classes(["flat","circular"])
        like_art_btn.set_tooltip_text("Like this artist")
        def on_like_artist(b,aid=aid):
            if b.get_css_classes().__contains__("accent"):
                b.remove_css_class("accent"); b.set_icon_name("emblem-favorite-symbolic")
                threading.Thread(target=lambda:dz_unlike_artist(aid),daemon=True).start()
            else:
                b.add_css_class("accent"); b.set_icon_name("starred-symbolic")
                threading.Thread(target=lambda:dz_like_artist(aid),daemon=True).start()
        like_art_btn.connect("clicked",on_like_artist)
        ib.append(play_btn); ib.append(like_art_btn); hdr.append(ib)
        outer.append(hdr)
        outer.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True)
        inner=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0); inner.set_margin_bottom(16)

        # Top 5 titres
        tl2=Gtk.Label(label="Top tracks"); tl2.set_css_classes(["section-title"])
        tl2.set_halign(Gtk.Align.START); tl2.set_margin_start(16); tl2.set_margin_top(12); tl2.set_margin_bottom(4)
        inner.append(tl2); inner.append(col_header(show_album=True))
        inner.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        lb=Gtk.ListBox(); lb.add_css_class("boxed-list")
        lb.set_margin_top(4); lb.set_margin_start(8); lb.set_margin_end(8)
        def on_row(listbox,row,queue=q):
            t=norm(row.item)
            try: idx=next(i for i,x in enumerate(queue) if str(x.get("SNG_ID"))==str(t.get("SNG_ID")))
            except: idx=0
            self.queue=queue; self.queue_idx=idx; self._play(t)
        lb.connect("row-activated",on_row)

        LIMIT=5
        for t in top[:LIMIT]: lb.append(make_track_row(t,self,show_album_col=True))
        inner.append(lb)

        # Bouton "Voir plus"
        if len(top)>LIMIT:
            more_btn=Gtk.Button(label=f"See all {len(top)} tracks"); more_btn.add_css_class("flat")
            more_btn.set_margin_start(16); more_btn.set_margin_top(4); more_btn.set_margin_bottom(8)
            more_btn.set_halign(Gtk.Align.START)
            def on_more(b,tracks=top,lb=lb,btn=None,queue=q):
                _clr(lb)
                for t in tracks: lb.append(make_track_row(t,self,show_album_col=True))
                b.set_visible(False)
            more_btn.connect("clicked",on_more); inner.append(more_btn)

        # Albums grille
        if albums:
            al2=Gtk.Label(label="Albums"); al2.set_css_classes(["section-title"])
            al2.set_halign(Gtk.Align.START); al2.set_margin_start(16); al2.set_margin_top(16); al2.set_margin_bottom(4)
            inner.append(al2)
            fb=Gtk.FlowBox(); fb.set_max_children_per_line(10); fb.set_min_children_per_line(3)
            fb.set_selection_mode(Gtk.SelectionMode.NONE)
            fb.set_margin_start(12); fb.set_margin_end(12); fb.set_margin_bottom(12)
            fb.set_column_spacing(8); fb.set_row_spacing(8)
            for a in albums:
                aid2=a.get("id",""); at=a.get("title","?"); img2=a.get("cover_medium",""); yr=str(a.get("release_date",""))[:4]
                def oc(b,aid=aid2,t=at): self._open_album(aid,t)
                fb.append(make_card_btn(at,yr,img2,120,False,oc))
            inner.append(fb)

        sc.set_child(inner); outer.append(sc)
        self._go_dynamic(outer,f"artist_{aid}")

    # ── Playlist create / import ───────────────────────────────────────────────
    def _pl_editor_dialog(self, heading, initial_name="", initial_pid=None):
        """Dialog réutilisable : nom + upload cover. Retourne (dialog, entry, cover_path_holder)."""
        dlg=Adw.MessageDialog(); dlg.set_transient_for(self.win)
        dlg.set_heading(heading)
        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        outer.set_margin_top(8); outer.set_margin_bottom(4)

        entry=Gtk.Entry(); entry.set_placeholder_text("Playlist name")
        entry.set_text(initial_name); outer.append(entry)

        cover_row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        self._pl_cover_path=[None]
        cover_preview_frm,cover_preview_pic=make_pic(48)
        cover_row.append(cover_preview_frm)
        cover_info=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        cover_info.set_valign(Gtk.Align.CENTER); cover_info.set_hexpand(True)
        cover_lbl=Gtk.Label(label="No cover"); cover_lbl.set_halign(Gtk.Align.START)
        cover_lbl.set_css_classes(["caption","dim-label"]); cover_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        cover_info.append(cover_lbl)
        cover_btn=Gtk.Button(label="Choose image"); cover_btn.set_css_classes(["flat"])
        cover_btn.set_halign(Gtk.Align.START)
        cover_info.append(cover_btn); cover_row.append(cover_info)
        outer.append(cover_row)
        dlg.set_extra_child(outer)

        def on_pick_cover(b):
            fd=Gtk.FileDialog(); fd.set_title("Choose cover image")
            ff=Gtk.FileFilter(); ff.set_name("Images"); ff.add_pattern("*.jpg"); ff.add_pattern("*.jpeg"); ff.add_pattern("*.png")
            st=Gio.ListStore.new(Gtk.FileFilter); st.append(ff); fd.set_filters(st)
            def on_f(d,res):
                try:
                    gf=d.open_finish(res); p=gf.get_path()
                    self._pl_cover_path[0]=p
                    cover_lbl.set_text(os.path.basename(p))
                    pb=fetch_img(p,48)
                    if pb: GLib.idle_add(set_pic,cover_preview_pic,pb)
                except: pass
            fd.open(self.win,None,on_f)
        cover_btn.connect("clicked",on_pick_cover)
        return dlg, entry, self._pl_cover_path

    def _upload_pl_cover(self, pid, path):
        try:
            import base64
            data=open(path,"rb").read()
            b64=base64.b64encode(data).decode()
            SESSION.post(
                f"https://www.deezer.com/ajax/gw-light.php",
                params={"method":"playlist.uploadPicture","input":"3","api_version":"1.0","api_token":API_TOKEN},
                json={"playlist_id":str(pid),"picture":b64}
            )
        except: pass

    def _on_create_playlist(self,_):
        dlg,entry,cover_path=self._pl_editor_dialog("New playlist")
        dlg.add_response("cancel","Cancel"); dlg.add_response("ok","Create")
        dlg.set_default_response("ok"); dlg.set_close_response("cancel")
        def on_resp(d,r):
            if r=="ok":
                name=entry.get_text().strip()
                cp=cover_path[0]
                if name:
                    def do():
                        res=dz_create_pl(name)
                        pid=str(res) if isinstance(res,(int,str)) else str(res.get("PLAYLIST_ID") or res.get("id",""))
                        if cp and pid and pid!="None":
                            self._upload_pl_cover(pid,cp)
                        GLib.idle_add(self._load_favs)
                    threading.Thread(target=do,daemon=True).start()
            d.destroy()
        dlg.connect("response",on_resp); dlg.present()

    def _on_edit_playlist(self, pid, current_name):
        dlg,entry,cover_path=self._pl_editor_dialog("Edit playlist",initial_name=current_name)
        dlg.add_response("cancel","Cancel"); dlg.add_response("delete","Delete")
        dlg.add_response("ok","Save")
        dlg.set_response_appearance("delete",Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("ok"); dlg.set_close_response("cancel")
        def on_resp(d,r):
            if r=="ok":
                name=entry.get_text().strip()
                cp=cover_path[0]
                def do():
                    if name and name!=current_name: dz_rename_pl(pid,name)
                    if cp: self._upload_pl_cover(pid,cp)
                    GLib.idle_add(self._load_favs)
                threading.Thread(target=do,daemon=True).start()
            elif r=="delete":
                def do(): dz_delete_pl(pid); GLib.idle_add(self._load_favs)
                threading.Thread(target=do,daemon=True).start()
            d.destroy()
        dlg.connect("response",on_resp); dlg.present()

    def _on_import_playlist(self,_):
        dlg=Gtk.FileDialog(); dlg.set_title("Import playlist")
        f=Gtk.FileFilter(); f.set_name("JSON / M3U"); f.add_pattern("*.json"); f.add_pattern("*.m3u"); f.add_pattern("*.m3u8")
        store=Gio.ListStore.new(Gtk.FileFilter); store.append(f)
        dlg.set_filters(store)
        def on_open(d,res):
            try:
                gfile=d.open_finish(res); path=gfile.get_path()
                threading.Thread(target=lambda:self._import_pl_file(path),daemon=True).start()
            except: pass
        dlg.open(self.win,None,on_open)

    def _import_pl_file(self,path):
        import re
        try:
            name=os.path.splitext(os.path.basename(path))[0]
            if path.endswith(".json"):
                data=json.load(open(path,"r",encoding="utf-8"))
                tracks=data if isinstance(data,list) else data.get("tracks",data.get("songs",[]))
            else:
                lines=[l.strip() for l in open(path,"r",encoding="utf-8") if l.strip() and not l.startswith("#")]
                tracks=lines
            if not tracks:
                GLib.idle_add(self._err,"No tracks found in file"); return
            res=dz_create_pl(name)
            pid=str(res) if isinstance(res,(int,str)) else str(res.get("PLAYLIST_ID") or res.get("id",""))
            if not pid or pid=="None":
                GLib.idle_add(self._err,"Could not create playlist"); return
            added=0
            for item in tracks[:200]:
                if isinstance(item,dict):
                    tid=str(item.get("id") or item.get("SNG_ID") or item.get("isrc",""))
                else:
                    # Chercher l'ID depuis le titre si c'est une chaîne type "Artiste - Titre"
                    tid=str(item).strip()
                if tid and tid.isdigit():
                    dz_add_to_pl(pid,tid); added+=1
            GLib.idle_add(self._load_favs)
            GLib.idle_add(lambda:self._err(f"{added} tracks imported into '{name}'") if added else self._err("No tracks imported (missing IDs)"))
        except Exception as e:
            GLib.idle_add(self._err,f"Import: {e}")

    def _on_lyrics(self,_):
        if not self.queue or not 0<=self.queue_idx<len(self.queue): return
        t=self.queue[self.queue_idx]
        tid=str(t.get("SNG_ID") or t.get("id",""))
        title=t.get("SNG_TITLE") or t.get("title","?")
        artist=t.get("ART_NAME") or t.get("artist",{}).get("name","")
        pop=Gtk.Popover(); pop.set_parent(self._lyrics_btn)
        pop.set_size_request(360,420)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        box.set_margin_top(12); box.set_margin_bottom(12); box.set_margin_start(12); box.set_margin_end(12)
        hdr_l=Gtk.Label(label=f"{title} — {artist}"); hdr_l.set_css_classes(["caption","dim-label"])
        hdr_l.set_halign(Gtk.Align.START); hdr_l.set_ellipsize(Pango.EllipsizeMode.END); box.append(hdr_l)
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True); sc.set_min_content_height(340)
        self._lyrics_label=Gtk.Label(label="Loading…"); self._lyrics_label.set_wrap(True)
        self._lyrics_label.set_halign(Gtk.Align.START); self._lyrics_label.set_valign(Gtk.Align.START)
        self._lyrics_label.set_selectable(True)
        sc.set_child(self._lyrics_label); box.append(sc)
        pop.set_child(box); pop.popup()
        def do():
            try:
                ly=dz_lyrics(tid)
                if ly:
                    lines=ly.get("synchronizedLines") or []
                    if lines:
                        text="\n".join(l.get("line","") for l in lines if l.get("line"))
                    else:
                        text=ly.get("text","Lyrics not available")
                else:
                    text="Lyrics not available"
                GLib.idle_add(self._lyrics_label.set_label,text)
            except Exception as e:
                GLib.idle_add(self._lyrics_label.set_label,f"Error: {e}")
        threading.Thread(target=do,daemon=True).start()

    # ── Playlist dialog ────────────────────────────────────────────────────────
    def _show_pl_dialog(self,tid):
        dlg=Adw.MessageDialog(); dlg.set_transient_for(self.win)
        dlg.set_heading("Add to playlist"); dlg.set_body("Choose a playlist:")
        dlg.add_response("cancel","Cancel"); dlg.set_close_response("cancel")
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4); box.set_margin_top(8); box.set_margin_bottom(8)
        sc=Gtk.ScrolledWindow(); sc.set_min_content_height(180); sc.set_max_content_height(380)
        lb=Gtk.ListBox(); lb.add_css_class("boxed-list"); lb.set_margin_start(8); lb.set_margin_end(8)
        sc.set_child(lb); box.append(sc); dlg.set_extra_child(box)
        self._pld_lb=lb; self._pld_tid=tid; self._pld_dlg=dlg
        threading.Thread(target=lambda:GLib.idle_add(self._fill_pl_dialog,dz_playlists()),daemon=True).start()
        dlg.connect("response",lambda d,r:d.destroy()); dlg.present()

    def _fill_pl_dialog(self,pls):
        for p in pls:
            pid=str(p.get("PLAYLIST_ID") or p.get("id","")); t=p.get("TITLE") or p.get("title","Playlist")
            row=Gtk.ListBoxRow(); row.playlist_id=pid
            lb=Gtk.Label(label=t); lb.set_halign(Gtk.Align.START)
            lb.set_margin_top(10); lb.set_margin_bottom(10); lb.set_margin_start(12)
            row.set_child(lb); self._pld_lb.append(row)
        def on_row(listbox,row,tid=self._pld_tid,dlg=self._pld_dlg):
            threading.Thread(target=lambda:dz_add_to_pl(row.playlist_id,tid),daemon=True).start()
            dlg.destroy()
        self._pld_lb.connect("row-activated",on_row)

    # ── Playback ───────────────────────────────────────────────────────────────
    def _play(self,track):
        import uuid
        self._play_token=uuid.uuid4().hex  # token unique, annule les threads précédents
        token=self._play_token
        tid=str(track.get("SNG_ID") or track.get("id",""))
        title=track.get("SNG_TITLE") or track.get("title","?")
        artist=track.get("ART_NAME") or track.get("artist",{}).get("name","")
        dur=int(track.get("DURATION") or track.get("duration",0))
        self.p_title.set_label(title); self.p_artist.set_label(artist)
        self._duration=dur; self.t_tot.set_label(f"{dur//60}:{dur%60:02d}")
        self.player_spinner.start(); self.btn_play.set_sensitive(False)
        if self.current_proc:
            try: self.current_proc.terminate(); self.current_proc.wait(timeout=1)
            except: pass
            self.current_proc=None
        if self._seek_timer: GLib.source_remove(self._seek_timer); self._seek_timer=None
        self._elapsed=0; self._seek_frac=0.0
        if self._seek_da: self._seek_da.queue_draw()
        self.t_cur.set_label("0:00")
        img=cover_url(track,"250x250")
        if img: load_pic_async(img,self.p_cover_pic,28)
        def do(tok=token):
            try:
                url=dz_stream_url(tid); ext=".flac" if QUALITY=="FLAC" else ".mp3"
                tmp=tempfile.NamedTemporaryFile(suffix=ext,delete=False); tmp.close()
                dz_decrypt(url,tid,tmp.name)
                if self._play_token==tok:  # si un autre play est arrivé, on abandonne
                    GLib.idle_add(self._start_play,tmp.name,track,tok)
                else:
                    os.unlink(tmp.name)
            except Exception as e:
                if self._play_token==tok: GLib.idle_add(self._err,f"Stream: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _start_play(self,path,track,tok=None):
        if tok and self._play_token!=tok: os.unlink(path); return
        self.player_spinner.stop()
        player=next((p for p in["mpv","ffplay","cvlc"] if subprocess.run(["which",p],capture_output=True).returncode==0),None)
        if not player: self.p_title.set_label("Install mpv: sudo dnf install mpv"); return
        # Update like button state for the new track
        if hasattr(self,"_player_like_btn") and self.queue and 0<=self.queue_idx<len(self.queue):
            t=self.queue[self.queue_idx]
            tid=str(t.get("SNG_ID") or t.get("id",""))
            if tid in self._liked_ids:
                self._player_like_btn.set_icon_name("starred-symbolic")
                self._player_like_btn.add_css_class("accent")
            else:
                self._player_like_btn.set_icon_name("emblem-favorite-symbolic")
                self._player_like_btn.remove_css_class("accent")
        args={"mpv":[player,"--no-video","--really-quiet",path],"ffplay":[player,"-nodisp","-autoexit","-loglevel","quiet",path],"cvlc":[player,"--intf","dummy",path]}
        self._cur_file=path; self.current_proc=subprocess.Popen(args[player],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self._playing=True; self._play_start=time.time(); self._elapsed=0
        self.btn_play.set_icon_name("media-playback-stop-symbolic"); self.btn_play.set_sensitive(True)
        self.btn_prev.set_sensitive(True); self.btn_next.set_sensitive(True)
        self._seek_timer=GLib.timeout_add(500,self._tick)

    def _seek_to(self,frac):
        if not self._duration or not self._cur_file: return
        target=max(0.0,min(1.0,frac))*self._duration
        self._seek_frac=frac; self._elapsed=target
        self._play_start=time.time()-target
        if self._seek_da: self._seek_da.queue_draw()
        if self.current_proc:
            try: self.current_proc.terminate(); self.current_proc.wait(timeout=1)
            except: pass
        player=next((p for p in["mpv","ffplay","cvlc"] if subprocess.run(["which",p],capture_output=True).returncode==0),None)
        if not player: return
        start=int(target)
        args={
            "mpv":[player,"--no-video","--really-quiet",f"--start={start}",self._cur_file],
            "ffplay":[player,"-nodisp","-autoexit","-loglevel","quiet","-ss",str(start),self._cur_file],
            "cvlc":[player,"--intf","dummy","--start-time",str(start),self._cur_file],
        }
        self.current_proc=subprocess.Popen(args[player],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

    def _tick(self):
        if not self._playing or not self.current_proc: return False
        if self.current_proc.poll() is not None:
            GLib.idle_add(self._on_next,None); return False
        self._elapsed=time.time()-self._play_start
        if self._duration>0:
            self._seek_frac=min(self._elapsed/self._duration,1.0)
            if self._seek_da: self._seek_da.queue_draw()
        e=int(self._elapsed); self.t_cur.set_label(f"{e//60}:{e%60:02d}")
        return True

    def _on_seek(self,*_): pass

    def _on_playpause(self,_):
        if self.current_proc:
            try: self.current_proc.terminate()
            except: pass
            self.current_proc=None; self._playing=False
            if self._seek_timer: GLib.source_remove(self._seek_timer); self._seek_timer=None
            self.btn_play.set_icon_name("media-playback-start-symbolic")
        elif self.queue and self.queue_idx>=0:
            self._play(self.queue[self.queue_idx])

    def _on_prev(self,_):
        if self.queue and self.queue_idx>0:
            self.queue_idx-=1; self._play(self.queue[self.queue_idx])

    def _on_next(self,_):
        if self.queue and self.queue_idx<len(self.queue)-1:
            self.queue_idx+=1; self._play(self.queue[self.queue_idx])

    def _set_quality(self,_,q):
        global QUALITY; QUALITY=q; self.qpop.popdown()

    def _err(self,msg):
        self.player_spinner.stop(); self.p_title.set_label(msg)

if __name__=="__main__":
    import sys; app=OpenDeez(); sys.exit(app.run(sys.argv))
