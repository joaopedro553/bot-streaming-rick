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

# --- CONFIGS ---
# Pegando das variáveis de ambiente da Render
TOKEN = os.getenv("TELEGRAM_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"

# Conectar MongoDB
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
db = client['streaming_db']

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
    await update.message.reply_text("📦 *Envie o .txt e escreva o serviço na legenda.*", parse_mode='MarkdownV2')

async def receber_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    servico = update.message.caption.lower() if update.message.caption else ""
    if servico in SERVICOS:
        file = await context.bot.get_file(update.message.document.file_id)
        content = (await file.download_as_bytearray()).decode('utf-8')
        docs = [{"dados": l.strip()} for l in content.splitlines() if ":" in l]
        if docs:
            db[servico].insert_many(docs)
            await update.message.reply_text(f"🚀 {len(docs)} contas em {servico}!")

async def limpa_generic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    s = update.message.text.lower().replace("/limpa_", "")
    if s in SERVICOS:
        db[s].delete_many({})
        await update.message.reply_text(f"🗑️ {s.upper()} zerado!")

# --- COMANDOS GRUPO ---
async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    est = "".join([f"▪️ /{s.capitalize()}: `{db[s].count_documents({})}`\n" for s in SERVICOS])
    # Usando fr"" para evitar SyntaxWarning
    txt = fr"👋 *Botricks Online\!*" + "\n\n" + fr"📊 *ESTOQUE:* " + "\n" + est
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
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{uid}"), InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_URL)]])
        
        # Formatação usando Raw String para não bugar
        txt = (
            fr"✅ *{servico.upper()}*" + "\n\n" +
            fr"✉️ E\-mail: `{escape_md(email)}`" + "\n" +
            fr"🔑 Senha: `{escape_md(senha)}`"
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
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=os.getenv("PORT", 10000)), daemon=True).start()
    
    if not TOKEN:
        logger.error("❌ TOKEN NÃO ENCONTRADO!")
    else:
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
            application.add_handler(CommandHandler(s.capitalize(), lambda u,c,s=s: gerar_servico(u,c,s)))

        print("🚀 Iniciando Bot...")
        application.run_polling(drop_pending_updates=True)
