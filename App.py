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

# --- DADOS DIRETOS (ATUALIZADOS COM O NOVO TOKEN) ---
TOKEN = "8479454342:AAH8qyPoDFyTEfzaUQGP3wsEjnbB3Z_aI2s"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"
LINK_GRUPO = "https://t.me/+B57LHwEBCAhiYzc5"
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

# Conectar MongoDB
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
db = client['streaming_db']
cooldowns = {}

def escape_md(text):
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+']:
        text = str(text).replace(char, f"\\{char}")
    return text

async def auto_delete_task(bot, chat_id, msg_id, tempo):
    await asyncio.sleep(tempo)
    try: await bot.delete_message(chat_id, msg_id)
    except: pass

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
            await update.message.reply_text(f"🚀 {len(docs)} contas subidas para {servico}!")

async def limpa_generic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    s = update.message.text.lower().replace("/limpa_", "")
    if s in SERVICOS:
        db[s].delete_many({})
        await update.message.reply_text(f"🗑️ Estoque de {s.upper()} zerado!")

# --- MOTOR DO GRUPO ---
async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    est = "".join([f"▪️ /{s.capitalize()}: {db[s].count_documents({})}\n" for s in SERVICOS])
    txt = f"👋 *Botricks Online*\n\n📊 *ESTOQUE:* \n{est}"
    m = await update.message.reply_text(txt, parse_mode='MarkdownV2')
    asyncio.create_task(auto_delete_task(context.bot, update.effective_chat.id, m.message_id, 20))
    try: await update.message.delete()
    except: pass

async def gerar_servico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    servico = update.message.text.replace("/", "").lower()
    if servico not in SERVICOS: return
    
    uid = update.effective_user.id
    if uid in cooldowns and datetime.now() < cooldowns[uid] and uid != OWNER_ID:
        try: await update.message.delete()
        except: pass
        return

    # Sorteio Aleatório (Estoque Infinito)
    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    if res:
        cooldowns[uid] = datetime.now() + timedelta(seconds=60)
        dados = res[0].get('dados', 'erro:erro')
        email, senha = dados.split(':', 1) if ":" in dados else (dados, "---")
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ APAGAR CONTA", callback_data=f"del_{uid}")],
            [InlineKeyboardButton("🛒 COMPRE SEUS STREAMING", url=VENDAS_URL)]
        ])
        
        txt = (
            f"✅ *{servico.upper()} GERADA*\n\n"
            f"✉️ E-mail: `{escape_md(email)}`\n"
            f"🔑 Senha: `{escape_md(senha)}`"
        )
        
        msg = await update.message.reply_text(txt, parse_mode='MarkdownV2', reply_markup=kb)
        try: await update.message.delete()
        except: pass
        asyncio.create_task(auto_delete_task(context.bot, update.effective_chat.id, msg.message_id, 180))
    else:
        aviso = await update.message.reply_text(f"⚠️ {servico.upper()} vazio!")
        asyncio.create_task(auto_delete_task(context.bot, update.effective_chat.id, aviso.message_id, 5))

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id in [int(query.data.split("_")[1]), OWNER_ID]:
        try: await query.message.delete()
        except: pass

# --- SERVER FLASK ---
app = Flask(__name__)
@app.route('/')
def health(): return "Bot Ativo", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- FUNÇÃO PRINCIPAL (ASYNC) ---
async def start_bot():
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Adicionado timeouts para evitar desconexão na Render
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )
    
    application.add_handler(CommandHandler('bot', bot_intro))
    application.add_handler(CommandHandler('abastecer', abastecer_guia))
    application.add_handler(CallbackQueryHandler(query_handler))
    application.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), receber_arquivo))
    
    for s in SERVICOS:
        application.add_handler(CommandHandler(f'Limpa_{s}', limpa_generic))
        application.add_handler(CommandHandler(s.capitalize(), gerar_servico))
        application.add_handler(CommandHandler(s.lower(), gerar_servico))

    async with application:
        await application.initialize()
        await application.start()
        logger.info("🚀 BOT RICK OPERANTE COM NOVO TOKEN!")
        await application.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        pass
