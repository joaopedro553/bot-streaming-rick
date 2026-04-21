import os
import logging
import asyncio
import re
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from pymongo import MongoClient

# --- CONFIGURAÇÕES DE LOGS ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES DO BOT ---
TOKEN = "8479454342:AAFq34sWRk16JgmOIUWDq7ZVY7hLpfPLMjo"
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

# Instância do Bot e Flask
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

def escape_md(text):
    """Escapa caracteres para MarkdownV2"""
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_']:
        text = str(text).replace(char, f"\\{char}")
    return text

# --- COMANDOS DO GRUPO ---

async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    est = ""
    for s in SERVICOS:
        qtd = db[s].count_documents({})
        est += f"▪️ /{s.capitalize()}: {qtd}\n"
    
    txt = fr"👋 *Botricks Online*" + "\n\n" + fr"📊 *ESTOQUE DISPONÍVEL:*" + "\n" + est
    await update.message.reply_text(txt, parse_mode='MarkdownV2')

async def gerar_servico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    servico = update.message.text.replace("/", "").lower()
    if servico not in SERVICOS: return
    
    uid = update.effective_user.id
    if uid in cooldowns and datetime.now() < cooldowns[uid] and uid != OWNER_ID:
        return

    # Sorteia conta sem apagar (Estoque Infinito)
    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    
    if res:
        cooldowns[uid] = datetime.now() + timedelta(seconds=60)
        dados = res[0].get('dados', 'erro:erro')
        email, senha = dados.split(':', 1) if ":" in dados else (dados, "---")
        
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{uid}"),
            InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_URL)
        ]])
        
        txt = (
            fr"✅ *{servico.upper()} GERADA*" + "\n\n" +
            fr"✉️ E\-mail: `{escape_md(email)}`" + "\n" +
            fr"🔑 Senha: `{escape_md(senha)}`"
        )
        await update.message.reply_text(txt, parse_mode='MarkdownV2', reply_markup=kb)
        try: await update.message.delete()
        except: pass
    else:
        await update.message.reply_text(f"⚠️ {servico.upper()} sem estoque!")

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id in [int(query.data.split("_")[1]), OWNER_ID]:
        try: await query.message.delete()
        except: pass

# --- ROTAS WEBHOOK ---

@app.route(f'/{TOKEN}', methods=['POST'])
async def webhook_handler():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "ok", 200

@app.route('/')
def index():
    return "BOT RICK STATUS: ONLINE", 200

# --- INICIALIZAÇÃO ---

async def main():
    # Registrar comandos
    application.add_handler(CommandHandler('bot', bot_intro))
    application.add_handler(CallbackQueryHandler(query_handler))
    for s in SERVICOS:
        application.add_handler(CommandHandler(s.capitalize(), gerar_servico))
        application.add_handler(CommandHandler(s.lower(), gerar_servico))
    
    # Configurar Webhook no Telegram
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    logger.info(f"✅ Webhook ativado em: {webhook_url}")

if __name__ == '__main__':
    # Inicia o Webhook em background
    asyncio.run(main())
    
    # Inicia o servidor Flask na porta da Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
