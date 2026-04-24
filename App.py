import telebot
import os
import threading
import time
import re
from datetime import datetime
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
TOKEN = "8479454342:AAEQC1Ar2R-zwdD6tWb1fIzDqUlIP3q7RfU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

# GRUPOS E DONO
ALLOWED_GROUPS = [-1003429027149, -1003961419582]
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"
CREDITOS_DONO = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']

# Coleções
users_db = db['usuarios']
logs_db = db['logs_geracao']

# --- CATEGORIAS ---
CATEGORIAS = {
    "🎬 FILMES E SÉRIES": ['netflix', 'disney', 'max', 'prime', 'paramount', 'apple', 'star', 'hulu'],
    "📺 TV E CANAIS": ['globoplay', 'clarotv', 'vivoplay', 'telecine', 'directv', 'vix', 'plex'],
    "⚽ ESPORTES": ['premiere', 'espn', 'dazn'],
    "🛠️ FERRAMENTAS": ['duolingo', 'canva', 'scribd', 'youtube'],
    "🎵 MÚSICA": ['spotify', 'deezer', 'tidal'],
    "📡 LISTAS": ['iptv']
}
SERVICOS_FLAT = [item for sublist in CATEGORIAS.values() for item in sublist]

# --- FUNÇÕES ---

def registrar_usuario(user):
    users_db.update_one(
        {"_id": user.id},
        {"$set": {"nome": user.first_name, "username": user.username, "last_seen": datetime.now()}},
        upsert=True
    )

def is_allowed(message):
    if message.chat.id in ALLOWED_GROUPS: return True
    if message.from_user.id == OWNER_ID and message.chat.type == 'private': return True
    return False

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def send_menu(message):
    if not is_allowed(message): return
    registrar_usuario(message.from_user)
    
    total_users = users_db.count_documents({})
    
    txt = (f"🛡️ *SISTEMA BOTRICKS ATIVO*\n"
           f"👤 *Olá:* {message.from_user.first_name}\n"
           f"🆔 *ID:* `{message.from_user.id}`\n"
           f"👥 *Membros Atendidos:* `{total_users}`\n\n"
           f"📊 *ESTOQUE ATUALIZADO:*\n")
    
    for cat, lista in CATEGORIAS.items():
        txt += f"\n*{cat}*\n"
        for s in lista:
            try:
                qtd = db[s].count_documents({})
                txt += f"🔹 /{s.capitalize()}: `{qtd}`\n"
            except: txt += f"🔹 /{s.capitalize()}: `0`\n"
    
    txt += f"\n👑 *Criador:* {CREDITOS_DONO}\n"
    txt += f"🛒 *Loja:* [Rick Spaces]({VENDAS_URL})"
    
    bot.reply_to(message, txt, parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_commands(message):
    if not is_allowed(message): return
    registrar_usuario(message.from_user)

    raw_cmd = message.text.split('@')[0].lower()
    servico = raw_cmd.replace("/", "")

    if servico not in SERVICOS_FLAT: return

    try:
        # Sorteia conta aleatória
        res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
        if res:
            dados = res[0].get('dados', 'erro:erro')
            email, senha = dados.split(":", 1) if ":" in dados else (dados, "---")
            
            kb = types.InlineKeyboardMarkup()
            kb.row(types.InlineKeyboardButton("🗑️ APAGAR MENSAGEM", callback_data=f"del_{message.from_user.id}"))
            kb.row(types.InlineKeyboardButton("🛒 COMPRE SEUS STREAMING", url=VENDAS_URL))
            
            msg_txt = (f"✅ *{servico.upper()} GERADA COM SUCESSO\!*\n\n"
                       f"👤 *Usuário:* {message.from_user.first_name}\n"
                       f"🆔 *ID:* `{message.from_user.id}`\n\n"
                       f"✉️ *E-mail:* `{email}`\n"
                       f"🔑 *Senha:* `{senha}`\n\n"
                       f"🚀 *Créditos:* {CREDITOS_DONO}\n"
                       f"📢 *Grupo:* [Clique Aqui](https://t.me/+B57LHwEBCAhiYzc5)\n\n"
                       f"⚠️ _Toque no e-mail ou senha para copiar!_")

            bot.send_message(message.chat.id, msg_txt, parse_mode='Markdown', reply_markup=kb, disable_web_page_preview=True)
            
            if message.chat.type != 'private':
                try: bot.delete_message(message.chat.id, message.message_id)
                except: pass
        else:
            bot.reply_to(message, f"⚠️ O estoque de {servico.upper()} está em reposição!")
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete(call):
    owner_id = int(call.data.split('_')[1])
    if call.from_user.id == owner_id or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
    else:
        bot.answer_callback_query(call.id, "❌ Apenas quem gerou a conta pode apagar!", show_alert=True)

# --- GESTÃO (SÓ DONO) ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if message.from_user.id != OWNER_ID: return
    servico = message.caption.lower() if message.caption else ""
    if servico in SERVICOS_FLAT:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8')
        docs = [{"dados": l.strip()} for l in content.splitlines() if ":" in l]
        if docs:
            db[servico].insert_many(docs)
            bot.reply_to(message, f"🚀 Thomas, {len(docs)} contas subidas para {servico}!")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def handle_limpa(message):
    if message.from_user.id != OWNER_ID: return
    s = message.text.lower().replace("/limpa_", "")
    if s in SERVICOS_FLAT:
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ Thomas, estoque de {s.upper()} zerado!")

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "SISTEMA THOMAS ATIVO", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.remove_webhook()
    print("🚀 Thomas Checker V2 BLACK EDITION Ativado!")
    bot.infinity_polling(skip_pending=True)
