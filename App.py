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

def escape_md(text):
    """Limpa caracteres especiais para evitar erro no Telegram MarkdownV2"""
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+']:
        text = str(text).replace(char, f"\\{char}")
    return text

# --- INSTÂNCIA DO BOT ---
application = ApplicationBuilder().token(TOKEN).build()

# --- COMANDOS ADMIN (DONO) ---

async def abastecer_guia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    txt = "📦 *GUIA DE ABASTECIMENTO*\n\nEnvie o arquivo `\.txt` e na legenda escreva o serviço\.\nEx: `netflix` ou `disney`"
    await update.message.reply_text(txt, parse_mode='MarkdownV2')

async def receber_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    servico = update.message.caption.lower() if update.message.caption else ""
    if servico in SERVICOS:
        file = await context.bot.get_file(update.message.document.file_id)
        content_bytes = await file.download_as_bytearray()
        content = content_bytes.decode('utf-8')
        docs = [{"dados": l.strip()} for l in content.splitlines() if ":" in l]
        if docs:
            db[servico].insert_many(docs)
            await update.message.reply_text(f"🚀 Sucesso! {len(docs)} contas subidas para {servico}!")
        else:
            await update.message.reply_text("❌ Nenhuma conta válida encontrada (Formato email:pass).")

async def limpa_generic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    servico = update.message.text.lower().replace("/limpa_", "")
    if servico in SERVICOS:
        db[servico].delete_many({})
        await update.message.reply_text(f"🗑️ Estoque de {servico.upper()} zerado!")

# --- MOTOR DO GRUPO (ESTOQUE INFINITO) ---

async def gerar_servico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    servico = update.message.text.replace("/", "").lower()
    if servico not in SERVICOS: return
    
    uid = update.effective_user.id
    agora = datetime.now()

    # Cooldown 60s
    if uid in cooldowns and agora < cooldowns[uid] and uid != OWNER_ID:
        try: await update.message.delete()
        except: pass
        return

    # Sorteia 1 conta sem apagar do banco
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
            f"✅ *{servico.upper()} GERADA*\n\n"
            f"✉️ E\-mail: `{escape_md(email)}`\n"
            f"🔑 Senha: `{escape_md(senha)}`\n\n"
            f"🤖 Grupo: [Clique aqui]({escape_md(LINK_GRUPO)})"
        )
        await update.message.reply_text(txt, parse_mode='MarkdownV2', reply_markup=kb, disable_web_page_preview=True)
        try: await update.message.delete()
        except: pass
    else:
        await update.message.reply_text(f"⚠️ {servico.upper()} sem estoque!")

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid_clicou = query.from_user.id
    uid_dono = int(query.data.split("_")[1])
    if uid_clicou in [uid_dono, OWNER_ID]:
        try: await query.message.delete()
        except: pass

async def bot_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_GROUP_ID: return
    est = "".join([f"▪️ /{s.capitalize()}: {db[s].count_documents({})}\n" for s in SERVICOS])
    txt = f"👋 *Botricks Online*\n\n📊 *ESTOQUE:* \n{est}"
    await update.message.reply_text(txt, parse_mode='MarkdownV2')

# --- WEB SERVER (FLASK) ---
app = Flask(__name__)

@app.route(f'/{TOKEN}', methods=['POST'])
async def respond():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return 'ok'

@app.route('/')
def index():
    return "BOT STATUS: ONLINE", 200

async def setup_webhook():
    # Registrar comandos e botões
    application.add_handler(CommandHandler('bot', bot_intro))
    application.add_handler(CommandHandler('abastecer', abastecer_guia))
    application.add_handler(CallbackQueryHandler(query_handler))
    application.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), receber_arquivo))
    for s in SERVICOS:
        application.add_handler(CommandHandler(f'Limpa_{s}', limpa_generic))
        application.add_handler(CommandHandler(s.capitalize(), gerar_servico))
        application.add_handler(CommandHandler(s.lower(), gerar_servico))
    
    # Ativar Webhook
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    logger.info(f"✅ WEBHOOK ATIVADO: {webhook_url}")

if __name__ == '__main__':
    # Configuração de inicialização
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_webhook())
    
    # Roda o servidor na porta da Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
