import os
import logging
import asyncio
import threading
import re
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from pymongo import MongoClient

# --- CONFIGURAÇÕES DE LOGS ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DADOS DO BOT ---
TOKEN = "8479454342:AAH8qyPoDFyTEfzaUQGP3wsEjnbB3Z_aI2s"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"
RENDER_URL = "https://bot-streaming-rick.onrender.com"

ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

# Conectar MongoDB
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
db = client['streaming_db']
cooldowns = {}

def escape_md(text):
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+']:
        text = str(text).replace(char, f"\\{char}")
    return text

# --- INSTÂNCIA DO BOT ---
application = ApplicationBuilder().token(TOKEN).build()

# --- COMANDOS DO GRUPO ---
async def gerar_servico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.id != ALLOWED_GROUP_ID: return
    
    servico = update.message.text.replace("/", "").lower()
    if servico not in SERVICOS: return
    
    uid = update.effective_user.id
    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    
    if res:
        dados = res[0].get('dados', 'erro:erro')
        email, senha = dados.split(':', 1) if ":" in dados else (dados, "---")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{uid}"), InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_URL)]])
        
        txt = f"✅ *{servico.upper()}*\n\n✉️ E-mail: `{escape_md(email)}`\n🔑 Senha: `{escape_md(senha)}`"
        await update.message.reply_text(txt, parse_mode='MarkdownV2', reply_markup=kb)
        try: await update.message.delete()
        except: pass
    else:
        await update.message.reply_text(f"⚠️ {servico.upper()} vazio!")

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id in [int(query.data.split("_")[1]), OWNER_ID]:
        try: await query.message.delete()
        except: pass

async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    est = "".join([f"▪️ /{s.capitalize()}: {db[s].count_documents({})}\n" for s in SERVICOS])
    await update.message.reply_text(f"👋 *Botricks Online*\n\n📊 *ESTOQUE:* \n{est}", parse_mode='MarkdownV2')

# --- WEB SERVER (FLASK) ---
app = Flask(__name__)

@app.route(f'/{TOKEN}', methods=['POST'])
async def respond(): # O Flask agora aceita 'async def' por causa do flask[async]
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return 'ok', 200

@app.route('/')
def index():
    return "BOT RICK STATUS: ONLINE", 200

async def setup_bot():
    application.add_handler(CommandHandler('bot', bot_intro))
    application.add_handler(CallbackQueryHandler(query_handler))
    for s in SERVICOS:
        application.add_handler(CommandHandler(s.capitalize(), gerar_servico))
        application.add_handler(CommandHandler(s.lower(), gerar_servico))
    
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    logger.info(f"✅ WEBHOOK SETADO: {webhook_url}")

if __name__ == '__main__':
    # Inicializa o bot dentro de um loop de eventos
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_bot())
    
    # Inicia o servidor Flask (A Render cuida do loop daqui pra frente)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
