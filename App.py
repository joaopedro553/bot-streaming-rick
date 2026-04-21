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

# --- CONFIGURAÇÕES DO BOT ---
TOKEN = "8479454342:AAH8qyPoDFyTEfzaUQGP3wsEjnbB3Z_aI2s"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"
RENDER_URL = "https://bot-streaming-rick.onrender.com"

ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"
LINK_GRUPO = "https://t.me/+B57LHwEBCAhiYzc5"

SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

# Conectar MongoDB
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
db = client['streaming_db']
cooldowns = {}

# Variável global para o loop de eventos
main_loop = None

def escape_md(text):
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+']:
        text = str(text).replace(char, f"\\{char}")
    return text

# --- INSTÂNCIA DO BOT ---
application = ApplicationBuilder().token(TOKEN).build()

# --- COMANDOS ADMIN ---
async def abastecer_guia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text("📦 *Envie o .txt e escreva o serviço na legenda (ex: netflix).*")

async def receber_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    servico = update.message.caption.lower() if update.message.caption else ""
    if servico in SERVICOS:
        file = await context.bot.get_file(update.message.document.file_id)
        content = (await file.download_as_bytearray()).decode('utf-8')
        docs = [{"dados": l.strip()} for l in content.splitlines() if ":" in l]
        if docs:
            db[servico].insert_many(docs)
            await update.message.reply_text(f"🚀 Sucesso! {len(docs)} contas em {servico}!")

async def limpa_generic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    s = update.message.text.lower().replace("/limpa_", "")
    if s in SERVICOS:
        db[s].delete_many({})
        await update.message.reply_text(f"🗑️ Estoque de {s.upper()} zerado!")

# --- MOTOR DO GRUPO ---
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

# --- WEB SERVER (FLASK) ---
app = Flask(__name__)

@app.route(f'/{TOKEN}', methods=['POST'])
def respond():
    # Esta função agora é síncrona para evitar o erro do Flask
    update = Update.de_json(request.get_json(force=True), application.bot)
    # Enviamos o processamento para o loop principal do bot
    asyncio.run_coroutine_threadsafe(application.process_update(update), main_loop)
    return 'ok', 200

@app.route('/')
def index():
    return "BOT RICK STATUS: ONLINE", 200

async def setup_webhook():
    application.add_handler(CommandHandler('bot', lambda u, c: u.message.reply_text("👋 Use os comandos /Servico")))
    application.add_handler(CommandHandler('abastecer', abastecer_guia))
    application.add_handler(CallbackQueryHandler(query_handler))
    application.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), receber_arquivo))
    for s in SERVICOS:
        application.add_handler(CommandHandler(s.capitalize(), gerar_servico))
        application.add_handler(CommandHandler(s.lower(), gerar_servico))
        application.add_handler(CommandHandler(f"Limpa_{s}", limpa_generic))
    
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    logger.info(f"✅ WEBHOOK SETADO: {webhook_url}")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Salva o loop atual para uso global
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    
    # Prepara o bot
    main_loop.run_until_complete(setup_webhook())
    
    # Inicia o servidor Flask em uma thread separada
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Mantém o loop principal rodando para processar mensagens
    main_loop.run_forever()
