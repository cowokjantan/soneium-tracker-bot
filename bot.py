import os
import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.markdown import hlink
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN tidak ditemukan! Pastikan sudah diatur di Railway Variables atau .env.")

bot = Bot(token=TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Database sementara (alamat + nama yang dipantau)
watched_addresses = {}
notified_tx_hashes = set()

# Command: /start
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("👋 Selamat datang! Kirimkan /add <alamat> <nama> untuk mulai melacak transaksi.")

# Command: /add <alamat> <nama>
@dp.message(Command("add"))
async def add_address(message: Message):
    args = message.text.split(" ", 2)
    if len(args) < 3:
        await message.answer("⚠️ Format salah! Gunakan: /add <alamat> <nama>")
        return
    address, name = args[1], args[2]
    watched_addresses[address.lower()] = name
    await message.answer(f"✅ Alamat {name} ({address}) telah ditambahkan!")

# Command: /list
@dp.message(Command("list"))
async def list_addresses(message: Message):
    if not watched_addresses:
        await message.answer("📭 Tidak ada alamat yang dipantau.")
        return
    msg = "📋 **Daftar Alamat yang Dipantau:**\n"
    for addr, name in watched_addresses.items():
        msg += f"🔹 {name}: `{addr}`\n"
    await message.answer(msg)

# Fungsi untuk mengecek transaksi baru
async def check_transactions():
    while True:
        for address, name in watched_addresses.items():
            url = f"https://soneium.blockscout.com/api?module=account&action=txlist&address={address}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    for tx in data["result"]:
                        tx_hash = tx["hash"]
                        if tx_hash not in notified_tx_hashes:
                            tx_link = f"https://soneium.blockscout.com/tx/{tx_hash}"
                            tx_type = "🔄 Transaksi"
                            if tx["to"].lower() == address:
                                tx_type = "📥 Received"
                            elif tx["from"].lower() == address:
                                tx_type = "📤 Sent"
                            elif tx.get("input", "").startswith("0xa9059cbb"):
                                tx_type = "🎨 Buy NFT"
                            elif tx.get("input", "").startswith("0x23b872dd"):
                                tx_type = "🛒 Sell NFT"

                            msg = f"📢 {tx_type} dari {name}:\n{hlink('🔗 Lihat Tx', tx_link)}"
                            await bot.send_message(chat_id=os.getenv("CHAT_ID"), text=msg)
                            notified_tx_hashes.add(tx_hash)
        await asyncio.sleep(30)

# Jalankan bot
async def main():
    asyncio.create_task(check_transactions())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
