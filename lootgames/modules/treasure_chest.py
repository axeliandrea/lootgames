from pyrogram import filters

TARGET_GROUP = -1002946278772  # ganti sesuai ID group mu

def register(app):
    @app.on_message()
    async def treasure_handler(client, message):
        # Cek command sederhana
        if message.text and message.text.strip() == ".treasurechest":
            try:
                # Kirim chat biasa ke group
                await client.send_message(TARGET_GROUP, "TEST CHEST - pesan dari owner")
                await message.reply(f"✅ Berhasil kirim TEST CHEST ke group {TARGET_GROUP}")
            except Exception as e:
                await message.reply(f"❌ Gagal kirim chest: {e}")

