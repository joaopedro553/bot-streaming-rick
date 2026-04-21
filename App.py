import os
import logging
import asyncio
import threading
import re
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from pymongo import MongoClient

# --- CONFIGURAÇÕES DE LOGS ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DADOS FIXOS ---
TOKEN = "8479454342:AAH8qyPoDFyTEfzaUQGP3wsEjnbB3Z_aI2s"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"
ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"

# Conectar MongoDB
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
db = client['streaming_db']
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']
cooldowns = {}

def escape_md(text):
    """Limpa caracteres para evitar erro no MarkdownV2"""
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+']:
        text = str(text).replace(char, f"\\{char}")
    return text

# --- FUNÇÕES DE APOIO ---
async def auto_delete_task(context, chat_id, msg_id, tempo):
    await asyncio.sleep(tempo)
    try:
        await context.bot.delete_message(chat_id, msg_id)
    except:
        pass

# --- COMANDOS ---
async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.id != ALLOWED_GROUP_ID: return
    
    est = ""
    for s in SERVICOS:
        qtd = db[s].count_documents({})
        est += f"▪️ /{s.capitalize()}: {qtd}\n"
    
    txt = fr"👋 *Botricks Online*" + "\n\n" + fr"📊 *ESTOQUE DISPONÍVEL:*" + "\n" + est
    msg = await update.message.reply_text(txt, parse_mode='MarkdownV2')
    # Auto deleta a apresentação em 30 segundos
    asyncio.create_task(auto_delete_task(context, update.effective_chat.id, msg.message_id, 30))

async def gerar_servico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.id != ALLOWED_GROUP_ID: return
    
    servico = update.message.text.replace("/", "").lower()
    if servico not in SERVICOS: return
    
    uid = update.effective_user.id
    agora = datetime.now()

    # Cooldown de 60s para evitar abuso (Dono não tem cooldown)
    if uid in cooldowns and agora < cooldowns[uid] and uid != OWNER_ID:
        try: await update.message.delete()
        except: pass
        return

    # Sorteia 1 conta aleatória (Estoque Infinito)
    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    
    if res:
        cooldowns[uid] = agora + timedelta(seconds=60)
        dados = res[0].get('dados', 'erro:erro')
        email, senha = dados.split(':', 1) if ":" in dados else (dados, "---")
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ APAGAR CONTA", callback_data=f"del_{uid}")],
            [InlineKeyboardButton("🛒 COMPRE SEUS STREAMING", url=VENDAS_URL)]
        ])
        
        txt = (
            fr"✅ *{servico.upper()} GERADA*" + "\n\n" +
            fr"✉️ E\-mail: `{escape_md(email)}`" + "\n" +
            fr"🔑 Senha: `{escape_md(senha)}`" + "\n\n" +
            fr"⚠️ Apagando em 3 minutos\."
        )
        
        msg = await update.message.reply_text(txt, parse_mode='MarkdownV2', reply_markup=kb)
        try: await update.message.delete()
        except: pass
        
        # Inicia delete automático em 180 segundos
        asyncio.create_task(auto_delete_task(context, update.effective_chat.id, msg.message_id, 180))
    else:
        aviso = await update.message.reply_text(f"⚠️ {servico.upper()} sem estoque!")
        asyncio.create_task(auto_delete_task(context, update.effective_chat.id, aviso.message_id, 5))

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid_clicou = query.from_user.id
    uid_owner_da_conta = int(query.data.split("_")[1])
    
    if uid_clicou == uid_owner_da_conta or uid_clicou == OWNER_ID:
        try: await query.message.delete()
        except: pass
    else:
        await query.answer("❌ Essa conta não é sua!", show_alert=True)

# --- SERVER PARA RENDER ---
server = Flask(__name__)
@server.route('/')
def h(): return "Bot Ativo", 200

def run_flask():
    server.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- EXECUÇÃO ---
if __name__ == '__main__':
    # Flask em thread separada
    threading.Thread(target=run_flask, daemon=True).start()

    # Inicia o Bot usando o método run_polling (Cria o loop sozinho)
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('bot', bot_intro))
    application.add_handler(CallbackQueryHandler(query_handler))
    
    for s in SERVICOS:
        application.add_handler(CommandHandler(s.capitalize(), gerar_servico))
        application.add_handler(CommandHandler(s.lower(), gerar_servico))

    logger.info("🚀 BOT INICIADO COM SUCESSO!")
    # drop_pending_updates=True limpa o conflito e mensagens velhas
    application.run_polling(drop_pending_updates=True)
