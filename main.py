import asyncio
import feedparser
from aiogram import Bot, Dispatcher, types
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bs4 import BeautifulSoup
import hashlib
import html

BOT_TOKEN = "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

rss_url = None
channel_id = None
show_preview = True
limit_text = False
sent_posts = set()


def clean_html(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    allowed_tags = ["b", "i", "u", "a", "ul", "li", "br"]
    for tag in soup.find_all(True):
        if tag.name not in allowed_tags:
            tag.unwrap()
    for ul in soup.find_all("ul"):
        for li in ul.find_all("li"):
            li.insert_before("• ")
            li.append("\n")
    return str(soup)


def parse_rss():
    global sent_posts
    if not rss_url:
        return []
    feed = feedparser.parse(rss_url)
    posts = []
    for entry in feed.entries:
        uid = hashlib.md5(entry.link.encode()).hexdigest()
        if uid in sent_posts:
            continue
        sent_posts.add(uid)
        title = html.escape(entry.title)
        description = clean_html(entry.get("summary", "") or entry.get("description", ""))
        link = entry.link
        image = None
        if "media_content" in entry:
            image = entry.media_content[0]["url"]
        elif "media_thumbnail" in entry:
            image = entry.media_thumbnail[0]["url"]
        posts.append({"title": title, "text": description, "link": link, "image": image})
    return posts


async def send_post(post):
    global channel_id, show_preview, limit_text
    if not channel_id:
        return
    text = f"<b>{post['title']}</b>\n\n{post['text']}\n\n<a href='{post['link']}'>🔗 Читать полностью</a>"
    if limit_text and len(text) > 1000:
        text = text[:997] + "..."
    try:
        if post['image']:
            await bot.send_photo(
                chat_id=channel_id,
                photo=post['image'],
                caption=text,
                disable_web_page_preview=not show_preview
            )
        else:
            await bot.send_message(
                chat_id=channel_id,
                text=text,
                disable_web_page_preview=not show_preview
            )
    except Exception as e:
        print("Ошибка при отправке:", e)


async def rss_checker():
    while True:
        posts = parse_rss()
        for post in posts:
            await send_post(post)
        await asyncio.sleep(300)


async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/setrss"), KeyboardButton(text="/setchannel")],
            [KeyboardButton(text="/togglepreview"), KeyboardButton(text="/togglelimit")],
            [KeyboardButton(text="/status")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Привет! Я бот, который пересылает записи из RSS в канал.\n\n"
        "Нажми кнопку или введи команду вручную.",
        reply_markup=kb
    )


async def cmd_setrss(message: types.Message):
    global rss_url, sent_posts
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи ссылку на RSS. Пример:\n/setrss https://site.com/rss")
        return
    rss_url = args[1]
    sent_posts.clear()
    await message.answer(f"✅ RSS установлен: {rss_url}")


async def cmd_setchannel(message: types.Message):
    global channel_id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи ID или username канала. Пример:\n/setchannel @mychannel")
        return
    channel_id = args[1]
    await message.answer(f"✅ Канал установлен: {channel_id}")


async def cmd_togglepreview(message: types.Message):
    global show_preview
    show_preview = not show_preview
    await message.answer(f"🔁 Превью ссылок: {'включено' if show_preview else 'выключено'}")


async def cmd_togglelimit(message: types.Message):
    global limit_text
    limit_text = not limit_text
    await message.answer(f"✂️ Ограничение текста: {'включено' if limit_text else 'выключено'}")


async def cmd_status(message: types.Message):
    await message.answer(
        f"<b>Текущие настройки:</b>\n"
        f"RSS: {rss_url or '❌ не установлен'}\n"
        f"Канал: {channel_id or '❌ не установлен'}\n"
        f"Превью: {'✅ включено' if show_preview else '❌ выключено'}\n"
        f"Ограничение текста: {'✅ включено' if limit_text else '❌ выключено'}"
    )


dp.message.register(cmd_start, Command("start"))
dp.message.register(cmd_setrss, Command("setrss"))
dp.message.register(cmd_setchannel, Command("setchannel"))
dp.message.register(cmd_togglepreview, Command("togglepreview"))
dp.message.register(cmd_togglelimit, Command("togglelimit"))
dp.message.register(cmd_status, Command("status"))


async def main():
    asyncio.create_task(rss_checker())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
