
import asyncio
import threading
import urllib.parse
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client

API_ID    = 15236856
API_HASH  = "e5d7c2bceacf90792ddadeb63cef8b1e"
BOT_TOKEN = "8799878382:AAFX7wBxKYWx0Py6tWTnXcZwtJjL0osI0w8"

# ✅ Render يحدد البورت تلقائياً عبر متغير البيئة PORT
PORT = int(os.environ.get("PORT", 8080))

# ✅ رابط التطبيق على Render (غيّر هذا برابطك الفعلي بعد النشر)
PUBLIC_HOST = os.environ.get("RENDER_EXTERNAL_URL", f"http://localhost:{PORT}")

bot   = Client("stream_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
loop  = asyncio.new_event_loop()
cache = {}

class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_GET(self):
        token = self.path.strip("/")
        entry = cache.get(token)
        if not entry:
            self.send_response(404); self.end_headers()
            self.wfile.write(b"Not found"); return

        msg, fname, fsize = entry
        fname_encoded = urllib.parse.quote(fname)

        range_h = self.headers.get("Range", "")
        if range_h:
            try:
                parts = range_h.replace("bytes=", "").split("-")
                start = int(parts[0])
                end   = int(parts[1]) if parts[1] else fsize - 1
            except Exception:
                start, end = 0, fsize - 1
            status = 206
        else:
            start, end, status = 0, fsize - 1, 200

        try:
            self.send_response(status)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Content-Range", f"bytes {start}-{end}/{fsize}")
            self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{fname_encoded}")
            self.end_headers()
        except Exception:
            return

        offset = start // (1024 * 1024)
        sent   = 0
        target = end - start + 1

        async def write_all():
            nonlocal sent
            async for chunk in bot.stream_media(msg, offset=offset):
                if sent >= target:
                    break
                remaining = target - sent
                data = chunk[:remaining] if len(chunk) > remaining else chunk
                self.wfile.write(data)
                self.wfile.flush()
                sent += len(data)

        try:
            future = asyncio.run_coroutine_threadsafe(write_all(), loop)
            future.result()
        except Exception:
            pass


async def setup(channel: str, msg_id: int):
    msg   = await bot.get_messages(channel, msg_id)
    media = msg.audio or msg.voice or msg.document
    fname = getattr(media, "file_name", f"{msg_id}.mp3")
    fsize = media.file_size
    token = f"{channel}_{msg_id}"
    cache[token] = (msg, fname, fsize)
    return token, fname, fsize


async def main():
    await bot.start()
    print("✅ Bot started")

    channel = "storytell_free"
    msg_id  = 482

    token, fname, fsize = await setup(channel, msg_id)

    # ✅ الرابط العام على Render بدل localhost
    url = f"{PUBLIC_HOST}/{token}"

    print(f"\n🎵 {fname}")
    print(f"📦 {fsize/1024/1024:.1f} MB")
    print(f"🔗 رابط البث:\n   {url}\n")

    server = HTTPServer(("0.0.0.0", PORT), StreamHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
