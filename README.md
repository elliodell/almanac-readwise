<div align="center">

<img src="docs/logo.svg" width="80" alt="Almanac logo">

# Almanac: Reading Stats

> **Readwise Books feature branch:** This fork adds optional direct Wi-Fi
> reading-session sync to Readwise Books while keeping Almanac working.
> It requires the companion CrossPoint firmware; see [setup and behavior](READWISE.md)
> and [verification status](VERIFY.md). Original Almanac attribution and license
> are preserved below.

#### Reading time, streaks and progress on your reader and the web. Just a plugin for the official CrossPoint firmware: no other firmware, no account. _(beta)_

**Free · No sign-up · Anonymous** · [www.almanac.im](https://almanac.im)

</div>

| On your reader | When you read | Every book |
| :---: | :---: | :---: |
| <img src="docs/reader.png" width="250" alt="The plugin on the reader: today, all time and the books in progress"> | <img src="docs/charts.png" width="250" alt="Reading time by day and by hour on www.almanac.im"> | <img src="docs/books.png" width="250" alt="Books with their progress on www.almanac.im"> |

## Original Almanac service

The privacy promises and Plugin Hub instructions below apply only to the original
Almanac service. The optional Readwise Books mirror shares reading metadata with
Readwise and uses your Readwise account. See [Books privacy and setup](READWISE.md).

## 🔒 Privacy first (Almanac only)

- 🙈 **Anonymous** — no sign-up: no name, email or password.
- 📖 **Only the basics** — the book's file name, reading time and progress.
- 🛡️ **Never sold** — not shared or shown to anyone.
- 🇪🇺 **Stored in the EU** — your stats stay in the European Union.

[Privacy policy and terms](https://almanac.im/privacy)

## 📦 Install original Almanac (without Books sync)

You need a reader with [CrossPoint](https://crosspointreader.com) 2.0 or newer (tested on the Xteink X3), Wi-Fi and a phone.

1. On the reader, turn on **Settings → Connectivity → Plugins**.
2. Open **Home → Plugins → Plugin Hub** and install **Almanac: Reading Stats** from the community plugins.
3. Open **Home → Plugins → Almanac: Reading Stats**, choose **Sign in** and scan the QR code with your phone.
4. Read as usual. Your stats are sent when the reader goes to sleep.

## 📶 When stats are sent

- Going to sleep, the reader joins your Wi-Fi for a moment, so it takes a few seconds longer.
- Want them right away? Leave the book and open the plugin: it connects and sends first.
- No Wi-Fi nearby or battery under 20%? Sessions wait on the reader for the next time. It keeps about 12; one more and it starts over, losing the unsent ones, so connect now and then when reading away from home.
- Quick peeks don't count: a session needs at least 10 seconds of reading.
- Books in very deep folders or with very long names (over about 235 bytes of path) aren't counted.

## 🛠️ Development

<details>
<summary>Install from this repo</summary>

Start **File Transfer** on the reader, on the same Wi-Fi as your computer, and run:

```bash
yarn install
yarn upload   # or: yarn upload 192.168.1.23, the IP shown on the reader
```

Without Node.js, copy the files from `almanac.crosspoint-plugin/` to `/plugins/almanac/` on the SD card, or upload them with curl in File Transfer mode:

```bash
H=crosspoint.local   # or the IP shown on the reader
curl -X POST -d "name=plugins&path=/" http://$H/mkdir
curl -X POST -d "name=almanac&path=/plugins" http://$H/mkdir
for f in almanac.crosspoint-plugin/*; do
  curl -X POST -d "path=/plugins/almanac/$(basename "$f")" http://$H/delete   # older firmware can't overwrite
  curl -X POST -F "file=@$f" "http://$H/upload?path=/plugins/almanac"
done
```

Then leave File Transfer and sign in as above.

</details>

## ⭐️ Support

If you find Almanac useful and you are brave enough consider [making a donation](https://github.com/sponsors/bartholomej) or sending some 🍺 or 🍵 over [Revolut](https://revolut.me/lukasbartak) ;)

## 📝 License

[MIT](LICENSE) © 2026 BART! A hobby project, not affiliated with CrossPoint, CrossInk or Xteink.

---

<div align="center">

**Built with ❤️ by [BART!](https://bartweb.cz)**

Powered by nature 🗻, wind 💨, tea 🍵 and beer 🍺

[📊 www.almanac.im](https://almanac.im) • [⭐ Star on GitHub](https://github.com/bartholomej/almanac.crosspoint-plugin) • [🔒 Privacy](https://almanac.im/privacy)

</div>
