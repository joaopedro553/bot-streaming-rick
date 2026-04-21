import os
import logging
import asyncio
import threading
import re
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from pymongo import MongoClient

# --- LOGS ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"
LINK_GRUPO = "https://t.me/+B57LHwEBCAhiYzc5"

# Conectar MongoDB
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
db = client['streaming_db']
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']
cooldowns = {}

def escape_md(text):
    return re.sub(r'([._\\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

async def auto_delete(context, chat_id, msg_id, tempo):
    await asyncio.sleep(tempo)
    try: await context.bot.delete_message(chat_id, msg_id)
    except: pass

# --- MOTOR DO GRUPO ---
async def gerar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    servico = update.message.text.replace("/", "").lower()
    if servico not in SERVICOS: return
    
    uid = update.effective_user.id
    if uid in cooldowns and datetime.now() < cooldowns[uid] and uid != OWNER_ID:
        try: await update.message.delete()
        except: pass
        return

    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    if res:
        cooldowns[uid] = datetime.now() + timedelta(seconds=60)
        dados = res[0].get('dados', 'erro:erro')
        email, senha = dados.split(':', 1) if ":" in dados else (dados, "---")
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ APAGAR CONTA", callback_data=f"del_{uid}")],
            [InlineKeyboardButton("🛒 COMPRE SEUS STREAMING", url=VENDAS_URL)]
        ])
        
        txt = (f"✅ *{servico.upper()} GERADA\!*\n\n"
               f"✉️ E\-mail: `{escape_md(email)}`\n"
               f"🔑 Senha: `{escape_md(senha)}`\n\n"
               f"🤖 Grupo: [Clique aqui]({LINK_GRUPO})\n"
               f"⚠️ Apagando em 3 minutos\.")
        
        msg = await update.message.reply_text(txt, parse_mode='MarkdownV2', reply_markup=kb, disable_web_page_preview=True)
        try: await update.message.delete()
        except: pass
        asyncio.create_task(auto_delete(context, update.effective_chat.id, msg.message_id, 180))
    else:
        aviso = await update.message.reply_text(f"⚠️ {servico.upper()} vazio!")
        asyncio.create_task(auto_delete(context, update.effective_chat.id, aviso.message_id, 5))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id in [int(query.data.split("_")[1]), OWNER_ID]:
        try: await query.message.delete()
        except: pass

async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    est = "".join([f"▪️ /{s.capitalize()}: `{db[s].count_documents({})}`\n" for s in SERVICOS])
    m = await update.message.reply_text(f"👋 *Botricks Online\!*\n\n📊 *ESTOQUE:* \n{est}", parse_mode='MarkdownV2')
    asyncio.create_task(auto_delete(context, update.effective_chat.id, m.message_id, 20))
    try: await update.message.delete()
    except: pass

# --- SERVER PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def h(): return "Bot Ativo", 200

if __name__ == '__main__':
    # Render usa a porta 10000 por padrão
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler('bot', bot_intro))
    bot.add_handler(CallbackQueryHandler(button))
    for s in SERVICOS:
        bot.add_handler(CommandHandler(s.capitalize(), gerar))
    
    bot.run_polling(drop_pending_updates=True)
