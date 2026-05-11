import telebot
import os
import threading
import time
import re
import io
import urllib.parse
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
TOKEN = "8479454342:AAEaNuwOS9WJnTrDb_LmSvWHAw0AbFRB7iU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

OWNER_ID = 1031830691 
ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
VENDAS_LINK = "https://t.me/ThomasObscuro"
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN, threaded=True)
client = MongoClient(MONGO_URI)
db = client['streaming_db']
stats_col = db['usuarios_stats']

# Listas
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
FILES_SERVICES = ['prime', 'youtube', 'canva']
ALL_SERVICES = STREAMING + FILES_SERVICES + ['netflix', 'iptv']

# --- FUNÇÕES ---

def get_daily_count(user_id):
    hoje = datetime.now().strftime("%Y-%m-%d")
    user_data = stats_col.find_one({"user_id": user_id})
    if not user_data or user_data.get("data") != hoje:
        stats_col.update_one({"user_id": user_id}, {"$set": {"data": hoje, "contagem": 1}}, upsert=True)
        return 1
    nova_contagem = user_data["contagem"] + 1
    stats_col.update_one({"user_id": user_id}, {"$set": {"contagem": nova_contagem}})
    return nova_contagem

def converter_nftoken(bruto):
    try:
        texto = urllib.parse.unquote(bruto.strip())
        t = texto.split("ct=")[1].split("&")[0] if "ct=" in texto else (texto.split("NetflixId=")[1].split(";")[0] if "NetflixId=" in texto else bruto.strip())
        t = t.replace('-', '+').replace('_', '/')
        while len(t) % 4 != 0: t += '='
        return f"https://netflix.com/?nftoken={t}"
    except: return bruto

# --- HANDLERS DE GESTÃO (PRIORIDADE 1 - SÓ DONO) ---

@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.text and m.text.lower().startswith("/limpa_"))
def handle_limpeza(message):
    try:
        servico = message.text.lower().split("_")[1]
        if servico in ALL_SERVICES:
            db[servico].delete_many({})
            bot.reply_to(message, f"🗑️ *ESTOQUE DE {servico.upper()} ZERADO!*", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Serviço não encontrado.")
    except:
        bot.reply_to(message, "❌ Use: `/Limpa_netflix`")

@bot.message_handler(content_types=['document'])
def handle_upload(message):
    if message.from_user.id != OWNER_ID: return
    serv = message.caption.lower() if message.caption else ""
    if serv in ALL_SERVICES:
        content = bot.download_file(bot.get_file(message.document.file_id).file_path).decode('utf-8', errors='ignore')
        if serv == 'iptv':
            docs = [{"dados": h.strip()} for h in content.split('--------------------------------------------------') if len(h.strip()) > 10]
        else:
            docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
        if docs:
            db[serv].insert_many(docs)
            bot.reply_to(message, f"🚀 Thomas, adicionei {len(docs)} em {serv.upper()}!")
    else:
        bot.reply_to(message, "❌ Legenda inválida! Use o nome do serviço.")

# --- HANDLERS PÚBLICOS (PRIORIDADE 2) ---

@bot.message_handler(commands=['start', 'bot'])
def handle_menu(message):
    # Verifica se está no grupo ou se é o Thomas
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛒 COMPRAR ACESSO VIP", url=VENDAS_LINK))
        bot.reply_to(message, "❌ *Acesso Negado!*\nChame o dono para comprar seu VIP.", parse_mode='Markdown', reply_markup=kb)
        return

    estoque = "".join([f"🔹 /{s.capitalize()}: `{db[s].count_documents({})}`\n" for s in ALL_SERVICES])
    txt = (f"👋 Olá {message.from_user.first_name}!\n🆔 Seu ID: `{message.from_user.id}`\n\n"
           f"📊 *ESTOQUE THOMAS CHECKER:* \n{estoque}\n"
           f"👑 *By:* {CREDITOS}")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💎 COMPRAR ACESSO VIP", url=VENDAS_LINK))
    bot.reply_to(message, txt, parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_gerar(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    cmd = message.text.split('@')[0].lower().replace("/", "")
    if cmd not in ALL_SERVICES: return

    try:
        res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
        if not res:
            bot.reply_to(message, f"⚠️ {cmd.upper()} sem estoque!")
            return

        dados = res[0]['dados']
        count = get_daily_count(message.from_user.id)
        
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
               types.InlineKeyboardButton("💎 COMPRAR VIP", url=VENDAS_LINK))

        header = (f"👤 *Usuário:* {message.from_user.first_name}\n"
                  f"🆔 *ID:* `{message.from_user.id}`\n"
                  f"🎫 *Geradas hoje:* `{count}`\n\n")

        if cmd == 'netflix':
            msg = f"✅ *NETFLIX GERADA*\n\n{header}🔗 [CLIQUE AQUI PARA LOGAR]({converter_nftoken(dados)})\n\n🚀 {CREDITOS}"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=kb)
        elif cmd in FILES_SERVICES:
            buf = io.BytesIO(dados.encode('utf-8')); buf.name = f"{cmd.upper()}.txt"
            bot.send_document(message.chat.id, buf, caption=f"✅ {cmd.upper()} GERADA!\n\n{header}🚀 {CREDITOS}", parse_mode='Markdown', reply_markup=kb)
        elif cmd == 'iptv':
            bot.send_message(message.chat.id, f"✅ *IPTV GERADA*\n\n{header}```\n{dados}\n```\n🚀 {CREDITOS}", parse_mode='Markdown', reply_markup=kb)
        else:
            bot.send_message(message.chat.id, f"✅ *{cmd.upper()} GERADA*\n\n{header}`{dados}`\n\n🚀 {CREDITOS}", parse_mode='Markdown', reply_markup=kb)

        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_del(call):
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    print("🚀 Bot V9 Online!")
    bot.infinity_polling(skip_pending=True)
