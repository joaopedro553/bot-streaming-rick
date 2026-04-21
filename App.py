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
logger = logging.getLogger(__name__)

# --- DADOS DIRETOS (SEM ERRO DE LEITURA) ---
TOKEN = "8479454342:AAFEX0k2XcKcLZB-q_77kIRH-CoPpmKlDVI"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

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

# --- COMANDOS ---
async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    est = "".join([f"▪️ /{s.capitalize()}: {db[s].count_documents({})}\n" for s in SERVICOS])
    txt = f"👋 *Botricks Online*\n\n📊 *ESTOQUE DISPONÍVEL:*\n{est}"
    await update.message.reply_text(txt, parse_mode='MarkdownV2')

async def gerar_servico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
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

# --- SERVER FLASK ---
server = Flask(__name__)
@server.route('/')
def h(): return "Bot Ativo", 200

def run_flask():
    server.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- FUNÇÃO PRINCIPAL ---
def main():
    # Inicia o Flask em segundo plano
    threading.Thread(target=run_flask, daemon=True).start()

    # Inicia o Bot
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('bot', bot_intro))
    application.add_handler(CallbackQueryHandler(query_handler))
    for s in SERVICOS:
        application.add_handler(CommandHandler(s.capitalize(), gerar_servico))
        application.add_handler(CommandHandler(s.lower(), gerar_servico))

    logger.info("🚀 BOT INICIADO COM SUCESSO!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
