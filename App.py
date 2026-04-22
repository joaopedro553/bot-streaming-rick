import telebot
import os
import threading
import time
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
TOKEN = "8479454342:AAEtmo-XK5QpurATxBbUSFNrciwymEk3h40"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

# LISTA DE GRUPOS AUTORIZADOS (Adicionei o novo aqui)
ALLOWED_GROUPS = [-1003429027149, -1003961419582] 
OWNER_ID = 1031830691
VENDAS_URL = "https://t.me/RickSpaces"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

# --- FILTRO DE SEGURANÇA ---
def is_group_allowed(chat_id):
    return chat_id in ALLOWED_GROUPS

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def send_intro(message):
    if not is_group_allowed(message.chat.id): return
    
    estoque = ""
    for s in SERVICOS:
        try:
            qtd = db[s].count_documents({})
            estoque += f"▪️ /{s.capitalize()}: {qtd}\n"
        except: estoque += f"▪️ /{s.capitalize()}: 0\n"
    
    bot.reply_to(message, f"👋 *Botricks Online*\n\n📊 *ESTOQUE:* \n{estoque}", parse_mode='Markdown')

@bot.message_handler(commands=SERVICOS + [s.capitalize() for s in SERVICOS])
def handle_gerar(message):
    if not is_group_allowed(message.chat.id): return
    
    servico = message.text.replace("/", "").lower()
    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    
    if res:
        dados = res[0].get('dados', 'erro:erro')
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
               types.InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_URL))
        
        bot.send_message(message.chat.id, f"✅ *{servico.upper()} GERADA*\n\n`{dados}`", parse_mode='Markdown', reply_markup=kb)
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
    else:
        bot.reply_to(message, f"⚠️ {servico} vazio!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete(call):
    # Apenas o dono da conta ou o dono do bot podem apagar
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

# --- COMANDOS ADMIN (ABASTECER) ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if message.from_user.id != OWNER_ID: return
    servico = message.caption.lower() if message.caption else ""
    if servico in SERVICOS:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8')
        docs = [{"dados": l.strip()} for l in content.splitlines() if ":" in l]
        if docs:
            db[servico].insert_many(docs)
            bot.reply_to(message, f"🚀 {len(docs)} contas em {servico}!")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def handle_limpa(message):
    if message.from_user.id != OWNER_ID: return
    s = message.text.lower().replace("/limpa_", "")
    if s in SERVICOS:
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ {s.upper()} zerado!")

# --- SERVER FLASK PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.remove_webhook()
    print("🚀 Bot Iniciado em 2 Grupos!")
    bot.infinity_polling(skip_pending=True)
