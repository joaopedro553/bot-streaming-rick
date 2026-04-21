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

# --- CONFIGS (Lendo da Render) ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")

ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"
LINK_GRUPO = "https://t.me/+B57LHwEBCAhiYzc5"

# Conectar MongoDB
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
    db = client['streaming_db']
    client.admin.command('ping')
    logger.info("✅ Conectado ao MongoDB!")
except Exception as e:
    logger.error(f"❌ Erro no MongoDB: {e}")

cooldowns = {}
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

def escape_md(text):
    return re.sub(r'([._\\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

async def auto_delete_task(context, chat_id, msg_id, tempo):
    await asyncio.sleep(tempo)
    try: await context.bot.delete_message(chat_id, msg_id)
    except: pass

# --- COMANDOS ADMIN ---
async def abastecer_guia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await update.message.reply_text(r"📦 *Envie o .txt e escreva o serviço na legenda.*", parse_mode='MarkdownV2')

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

# --- COMANDOS GRUPO (ESTOQUE INFINITO) ---
async def gerar_servico(update: Update, context: ContextTypes.DEFAULT_TYPE, servico: str):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    uid = update.effective_user.id
    if uid in cooldowns and datetime.now() < cooldowns[uid] and uid != OWNER_ID:
        try: await update.message.delete()
        except: pass
        return

    # Sorteio Aleatório (Sample)
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
            f"✅ *{servico.upper()} GERADA\!*\n\n"
            f"✉️ E\-mail: `{escape_md(email)}`\n"
            f"🔑 Senha: `{escape_md(senha)}`\n\n"
            f"🤖 Grupo: [Clique aqui]({LINK_GRUPO})"
        )
        
        msg = await update.message.reply_text(txt, parse_mode='MarkdownV2', reply_markup=kb, disable_web_page_preview=True)
        try: await update.message.delete()
        except: pass
        asyncio.create_task(auto_delete_task(context, update.effective_chat.id, msg.message_id, 180))
    else:
        aviso = await update.message.reply_text(f"⚠️ {servico.upper()} vazio!")
        asyncio.create_task(auto_delete_task(context, update.effective_chat.id, aviso.message_id, 5))

async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    est = "".join([f"▪️ /{s.capitalize()}: `{db[s].count_documents({})}`\n" for s in SERVICOS])
    txt = f"👋 *Botricks Online\!*\n\n📊 *ESTOQUE DISPONÍVEL:* \n{est}"
    m = await update.message.reply_text(txt, parse_mode='MarkdownV2')
    asyncio.create_task(auto_delete_task(context, update.effective_chat.id, m.message_id, 20))
    try: await update.message.delete()
    except: pass

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
        bot = ApplicationBuilder().token(TOKEN).build()
        bot.add_handler(CommandHandler('bot', bot_intro))
        bot.add_handler(CommandHandler('abastecer', abastecer_guia))
        bot.add_handler(CallbackQueryHandler(query_handler))
        bot.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), receber_arquivo))
        for s in SERVICOS:
            bot.add_handler(CommandHandler(s.capitalize(), lambda u,c,s=s: gerar_servico(u,c,s)))
        
        logger.info("🚀 Iniciando Polling...")
        bot.run_polling(drop_pending_updates=True)
