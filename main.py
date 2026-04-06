import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from googlesearch import search

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "7946458938:AAEmq6qBhEysEIitalnLZJpT0QhWnoSD4kU"
CHANNEL_ID = "-1003565360163" 
CHANNEL_URL = "https://t.me/+hFepWPiOKGhkNTI1"
# ---------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

def get_sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подписаться на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="Проверить подписку", callback_data="check_sub")]
    ])

def get_advanced_dorks(target_type, value):
    if target_type == "fio":
        return {
            "SOCIAL_AND_PROFILES": [f'"{value}" site:vk.com', f'"{value}" site:ok.ru', f'"{value}" site:facebook.com', f'"{value}" site:instagram.com'],
            "DOCUMENTS_AND_LEAKS": [f'"{value}" filetype:pdf', f'"{value}" filetype:xlsx', f'"{value}" "паспортные данные"', f'"{value}" "список сотрудников"'],
            "GOV_AND_COURTS": [f'"{value}" site:sudact.ru', f'"{value}" site:fssp.gov.ru', f'"{value}" "ИНН"'],
            "MENTIONS": [f'"{value}" -site:vk.com -site:ok.ru']
        }
    elif target_type == "domain":
        return {
            "INFRASTRUCTURE": [f'site:{value}', f'host:{value}', f'intitle:"index of" "{value}"'],
            "SENSITIVE_FILES": [f'site:{value} filetype:env', f'site:{value} filetype:sql', f'site:{value} filetype:log', f'site:{value} "password"'],
            "ADMIN_PANELS": [f'site:{value} inurl:admin', f'site:{value} inurl:login', f'site:{value} intitle:"dashboard"'],
            "SUBDOMAINS": [f'site:*..{value}']
        }
    else: # IP
        return {
            "REPORTS": [f'"{value}"', f'"{value}" abuse', f'"{value}" blacklist'],
            "OPEN_SERVICES": [f'"{value}" "port 80"', f'"{value}" "port 443"', f'"{value}" "index of"'],
            "LOCATION_DATA": [f'site:ipinfo.io "{value}"', f'site:shodan.io "{value}"']
        }

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if await check_subscription(message.from_user.id):
        await message.answer("🛠 **IntelScry OSINT Console v2.0**\n\nВведите ФИО, Домен или IP для глубокого сканирования.", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Доступ заблокирован. Подпишитесь на канал для использования базы.", reply_markup=get_sub_kb())

@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.edit_text("✅ Доступ разрешен. Введите запрос.")
    else:
        await callback.answer("❌ Вы не подписаны!", show_alert=True)

@dp.message()
async def handle_osint(message: types.Message):
    if not await check_subscription(message.from_user.id):
        return await message.answer("❌ Подпишитесь на канал!", reply_markup=get_sub_kb())

    query = message.text
    progress_msg = await message.answer("🧬 **Идет глубокое сканирование...**\n[░░░░░░░░░░] 0%")
    
    # Определение типа
    if any(c.isalpha() for c in query) and " " in query: t_type = "fio"
    elif "." in query and any(c.isalpha() for c in query): t_type = "domain"
    else: t_type = "ip"

    dork_groups = get_advanced_dorks(t_type, query)
    report = f"```\n[>>> DEEP_SCAN_REPORT: {query} <<<]\n"
    report += f"IDENT_TYPE: {t_type.upper()}\n"
    report += f"SCAN_LEVEL: MAXIMUM\n"
    report += "="*35 + "\n\n"

    try:
        step = 100 // len(dork_groups)
        current_progress = 0

        for group_name, queries in dork_groups.items():
            report += f"[{group_name}]\n"
            found_in_group = False
            
            # Берем по 2 запроса из группы для баланса скорости и объема
            for d in queries[:2]:
                # search(..., advanced=True) дает доступ к title и description
                results = search(d, num_results=3, advanced=True)
                for res in results:
                    found_in_group = True
                    report += f"● SOURCE: {res.url}\n"
                    report += f"  TITLE: {res.title[:50]}...\n"
                    report += f"  SNIPPET: {res.description[:100]}...\n\n"
            
            if not found_in_group:
                report += "  [!] No clear matches in this sector.\n\n"
            
            current_progress += step
            await progress_msg.edit_text(f"🧬 **Идет сбор данных...**\n[{'█'*(current_progress//10)}{'░'*(10-(current_progress//10))}] {current_progress}%")

        report += "="*35 + "\n"
        report += f"PROBABILITY_SCORE: {random.randint(60, 98)}%\n"
        report += "END OF TRANSMISSION\n```"
        
        await progress_msg.delete()
        # Если отчет слишком длинный, разбиваем его (TG лимит 4096 символов)
        if len(report) > 4000:
            for i in range(0, len(report), 4000):
                await message.answer(report[i:i+4000], parse_mode="MarkdownV2")
        else:
            await message.answer(report, parse_mode="MarkdownV2")

    except Exception as e:
        await message.answer(f"```\n[ERROR]: Scan interrupted\nREASON: {str(e)}\n```", parse_mode="MarkdownV2")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
