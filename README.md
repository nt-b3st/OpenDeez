# OpenDeez 🎵

An open-source, unofficial Deezer client for Linux, built with Python and GTK4/Adwaita.

> **This project is not affiliated with, endorsed by, or connected to Deezer SAS in any way.**
> It is an independent client built for interoperability purposes under EU Directive 2009/24/EC
> (Software Directive), which permits reverse engineering for interoperability.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![GTK](https://img.shields.io/badge/GTK-4.0-green?style=flat-square)
![Linux](https://img.shields.io/badge/Platform-Linux-lightgrey?style=flat-square&logo=linux)
![Licence](https://img.shields.io/badge/Licence-GPL--3.0-orange?style=flat-square)

---

## What is OpenDeez?

OpenDeez is a native Linux desktop client for Deezer. It was created because **Deezer does not
provide an official Linux client**, leaving Linux users with no alternative but to use a web
browser. OpenDeez fills that gap.

This project does **not** host, distribute, cache, or reproduce any copyrighted music. It is
a thin interface that communicates with Deezer's servers on behalf of an authenticated user,
exactly like a web browser would.

### Legal basis

- **Interoperability** — EU Directive 2009/24/EC Art. 6 explicitly allows reverse engineering
  of software interfaces for interoperability purposes. OpenDeez enables interoperability between
  Deezer's service and the Linux desktop.
- **No distribution of copyrighted content** — no music files are stored, shared, or redistributed.
  All audio is streamed in real time from Deezer's own servers to the authenticated user.
- **Personal use** — this tool requires the user's own valid Deezer account and credentials.
  It does not bypass authentication or enable access to content the user is not entitled to.
- **Non-commercial** — this project is completely free, contains no ads, no paid features,
  and generates no revenue of any kind.

### A note on artist compensation

> ⚠️ **Premium accounts only.**
> Deezer Free accounts are funded by advertising revenue, which is used to compensate artists.
> Using this client with a Free account bypasses those ads and therefore reduces artist
> compensation. **OpenDeez is intended for Deezer Premium subscribers only.**
> If you have a Free account, please use the official Deezer web player or app.

---

## Features

- 🏠 **Home** — Personalized Flow preview, top tracks, new releases, suggested playlists
- 🎵 **Flow** — Your personal Deezer radio
- ⭐ **Favorites** — Liked tracks, albums, artists and playlists in tabbed view
- 📋 **Playlists** — Full playlist library with track browsing
- 🔍 **Search** — Search by track title or artist name
- ▶️ **Playback** — Prev / Play / Next controls with automatic queue
- 🔐 **Login** — Email/password or ARL cookie, credentials saved locally
- 🦊 **Firefox auto-detect** — One-click login if you're already signed in on Firefox

---

## Requirements

### System packages

```bash
# Fedora
sudo dnf install python3-gobject mpv

# Ubuntu / Debian
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 mpv
```

### Python packages

```bash
pip install requests pycryptodome --break-system-packages
```

---

## Installation

```bash
git clone https://github.com/nt-b3st/opendeez.git
cd opendeez
python3 main.py
```

---

## Connecting your account

### Option 1 — Email & Password
Enter your Deezer email and password directly in the login screen.

> If your account was created via Google or Facebook (no Deezer password set), use the ARL method below.

### Option 2 — ARL Cookie
1. Open Firefox and log in at [deezer.com](https://www.deezer.com)
2. Press `F12` → **Storage** → **Cookies** → `https://www.deezer.com`
3. Copy the value of the cookie named `arl`
4. Paste it into the ARL field in OpenDeez

### Option 3 — Firefox Auto-detect
If you are already logged into Deezer in Firefox, OpenDeez will detect your session automatically
and offer a one-click login button.

Credentials are stored locally in `~/.config/echo-linux/config.json` and never transmitted
anywhere other than Deezer's own servers.

---

## Audio quality

| Format   | Bitrate    | Account required  |
|----------|------------|-------------------|
| MP3 128  | 128 kbps   | Free or Premium   |
| MP3 320  | 320 kbps   | Premium only      |
| FLAC     | Lossless   | Premium only      |

---

## Project structure

```
opendeez/
├── main.py        # Main application (UI + API layer)
├── README.md
├── .gitignore
└── LICENSE
```

---

## Roadmap

- [ ] Album artwork display
- [ ] Playback progress bar with seek
- [ ] System notifications on track change
- [ ] Auto dark/light theme
- [ ] RPM package
- [ ] AppImage (universal Linux binary)
- [ ] Podcast support
- [ ] Equalizer

---

## Comparison with similar projects

OpenDeez is not unique — many similar open-source clients exist and have been available on
GitHub for years without legal action:

| Project     | Platform  | Status    |
|-------------|-----------|-----------|
| Strawberry  | Desktop   | Active ✅ |
| Nuclear     | Desktop   | Active ✅ |
| Lollypop    | GNOME     | Active ✅ |
| Deemix      | Desktop   | Archived  |
| Freezer     | Android   | Archived  |

The difference between archived and active projects is generally whether they included
**bulk downloading** features. OpenDeez does not include any downloading functionality.

---

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push (`git push origin feature/my-feature`)
5. Open a Pull Request

Please do not open issues or PRs related to downloading, ripping, or bypassing
Deezer's authentication in ways not already present in the codebase.

---

## Inspiration

This project was inspired by [Echo](https://github.com/brahmkshatriya/echo), an extensible
Android music player that supports Deezer via `.eapk` extension plugins. OpenDeez is an
independent Linux desktop implementation built around the same idea: a clean, native client
for users who already pay for Deezer but have no official Linux option.

---

## Disclaimer

OpenDeez is an independent project and is not affiliated with, authorized by, sponsored by,
or approved by Deezer SAS. The Deezer name and logo are trademarks of Deezer SAS.

This software does not circumvent access controls — it authenticates as a legitimate user
and accesses only content that the authenticated user is entitled to access under their
existing subscription.

This software is provided "as is", without warranty of any kind. Use at your own risk.
The author is not responsible for any account suspension or other consequences resulting
from use of this software.

---

## License

GPL-3.0 — see [LICENSE](LICENSE) for details.

By using the GPL license, any fork or derivative work must also remain open-source and
non-commercial.
