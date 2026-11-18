# Cue — stage timer & confidence monitor

A minimal on-stage countdown for moderating panels and fireside chats. You run it from a laptop. Panelists see a clean, huge countdown on any screen. They open it by scanning a QR code, with no app and no login.

- Big countdown that turns amber, then red, then counts overtime (`+0:12`) with a slow pulse
- Run of show with names and minutes per segment, plus how long the whole show has left and its projected end time
- One-tap cues to the panel (Wrap up, 1 minute, Time, Last question…) or your own text, plus Flash and Blackout
- Scanned screens only watch: they can't change anything
- Keyboard: `Space` start/pause · `← →` segment · `+ −` 1 min · `W` wrap up · `L` flash · `B` blackout · `Q` QR · `O` output view · `F` fullscreen

## Two ways to share the panel view

| | **Anywhere** (GitHub Pages) | **This wifi only** (`cue.py`) |
|---|---|---|
| Panelists' phones need | Any internet: venue wifi or mobile data | The same wifi as your laptop |
| Venue internet needed | Yes | No |
| Setup on the day | Open your GitHub Pages link | Run `python3 cue.py` |

Run `cue.py` and you get **both** QR codes: the Anywhere code while the laptop is online, and the wifi code as a fallback.

---

## Put it on GitHub (one time, about 5 minutes, all in the browser)

1. Sign in at github.com, click **+** (top right) → **New repository**.
   - Name: `cue-timer` · **Public** · leave "Add a README" unticked → **Create repository**.
2. On the new repo page, click **uploading an existing file**.
3. Unzip `cue-timer.zip` and drag **everything inside the folder** into the page: `index.html`, `cue.py`, `cue-config.js`, `README.md`, the `vendor` folder and `.nojekyll`.
   *(On a Mac, press `Cmd+Shift+.` in Finder to see `.nojekyll`. It's optional, so skip it if you can't see it.)*
   Click **Commit changes**.
4. Go to **Settings → Pages**. Under *Build and deployment* choose **Deploy from a branch**, branch **main**, folder **/ (root)** → **Save**.
5. Wait about a minute. Your timer is live at **`https://YOUR-NAME.github.io/cue-timer/`**.
6. In the repo, open `cue-config.js`, click the ✏️ pencil, set
   `publicUrl: 'https://YOUR-NAME.github.io/cue-timer/'` and commit.
   (This only matters for `cue.py`. It tells the laptop where its "Anywhere" QR should point.)

## On the day

**Venue has internet:** open `https://YOUR-NAME.github.io/cue-timer/` on your laptop. Set up the run of show, press `Q` and have panelists scan. That's it.

**Venue internet is unreliable or missing:**
1. Download the repo (**Code → Download ZIP**) to the laptop and unzip it.
2. Open Terminal in that folder and run `python3 cue.py`. On Windows, use `py cue.py`.
3. Allow incoming connections if your computer asks.
4. Panelists join the same wifi and scan the **This wifi only** QR.
   If the venue wifi blocks devices from seeing each other (common in hotels), turn on your phone's hotspot and put the laptop and panel devices on it.

**Confidence monitor over HDMI:** open a second window, drag it to the monitor and press `O`, then `F`. Or mirror the laptop and switch to Output.

## Tips

- Panelists tap once when the timer opens. That keeps their screen awake. Landscape gives the biggest numbers.
- **New link** (in the share panel) makes old QR codes stop working.
- Your run of show is saved in your browser and survives a reload.

## How it works and privacy

GitHub Pages only serves the page; it can't pass the countdown between devices. For that, the "Anywhere" mode sends the timer state through free public relays (HiveMQ and EMQX, used together so one can fail). Every message is **encrypted in your browser** with a key that exists only in the QR link. The relays can't read your segment names or messages, and only someone with the QR can open the view. The wifi mode never leaves your local network.

Bundled libraries (MIT): [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator), [NoSleep.js](https://github.com/richtr/NoSleep.js), [MQTT.js](https://github.com/mqttjs/MQTT.js).
