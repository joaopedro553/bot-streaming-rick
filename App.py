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

# --- CONFIGURAÇÕES DE LOGS ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES CRÍTICAS ---
# Se a Render falhar em ler o Environment, ele usará o que você colocar aqui:
TOKEN = os.environ.get("TELEGRAM_TOKEN") or "8479454342:AAFEX0k2XcKcLZB-q_77kIRH-CoPpmKlDVI"
MONGO_URI = os.environ.get("MONGO_URI") or "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"
LINK_GRUPO = "https://t.me/+B57LHwEBCAhiYzc5"

# Conectar MongoDB
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
    db = client['streaming_db']
    client.admin.command('ping')
    logger.info("✅ BANCO DE DADOS CONECTADO!")
except Exception as e:
    logger.error(f"❌ ERRO NO MONGODB: {e}")

cooldowns = {}
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

def escape_md(text):
    # Função simples para evitar erros de MarkdownV2
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+']:
        text = str(text).replace(char, f"\\{char}")
    return text

async def auto_delete_task(context, chat_id, msg_id, tempo):
    await asyncio.sleep(tempo)
    try: await context.bot.delete_message(chat_id, msg_id)
    except: pass

# --- COMANDOS ---
async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    est = ""
    for s in SERVICOS:
        qtd = db[s].count_documents({})
        est += f"▪️ /{s.capitalize()}: {qtd}\n"
    
    txt = f"👋 *Botricks Online*\n\n📊 *ESTOQUE DISPONÍVEL:*\n{est}"
    m = await update.message.reply_text(txt, parse_mode='MarkdownV2')
    asyncio.create_task(auto_delete_task(context, update.effective_chat.id, m.message_id, 20))
    try: await update.message.delete()
    except: pass

async def gerar_servico(update: Update, context: ContextTypes.DEFAULT_TYPE, servico: str):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
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
        
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ APAGAR CONTA", callback_data=f"del_{uid}"), InlineKeyboardButton("🛒 COMPRE SEUS STREAMING", url=VENDAS_URL)]])
        
        # Texto limpo sem escapes complexos
        txt = (
            f"✅ *{servico.upper()} GERADA*\n\n"
            f"✉️ E-mail: `{escape_md(email)}`\n"
            f"🔑 Senha: `{escape_md(senha)}`"
        )
        
        msg = await update.message.reply_text(txt, parse_mode='MarkdownV2', reply_markup=kb)
        try: await update.message.delete()
        except: pass
        asyncio.create_task(auto_delete_task(context, update.effective_chat.id, msg.message_id, 180))
    else:
        aviso = await update.message.reply_text(f"⚠️ {servico.upper()} vazio!")
        asyncio.create_task(auto_delete_task(context, update.effective_chat.id, aviso.message_id, 5))

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id in [int(query.data.split("_")[1]), OWNER_ID]:
        try: await query.message.delete()
        except: pass

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def h(): return "Bot Ativo", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    if not TOKEN:
        logger.error("❌ TOKEN NÃO ENCONTRADO!")
    else:
        bot = ApplicationBuilder().token(TOKEN).connect_timeout(30).read_timeout(30).build()
        bot.add_handler(CommandHandler('bot', bot_intro))
        bot.add_handler(CallbackQueryHandler(query_handler))
        for s in SERVICOS:
            bot.add_handler(CommandHandler(s.capitalize(), lambda u,c,s=s: gerar_servico(u,c,s)))
        
        logger.info("🚀 INICIANDO POLLING...")
        bot.run_polling(drop_pending_updates=True)
