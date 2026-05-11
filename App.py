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

OWNER_ID = 1031830691 # Thomas
VENDAS_LINK = "https://t.me/ThomasObscuro"
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN, threaded=True)
client = MongoClient(MONGO_URI)
db = client['streaming_db']
users_col = db['usuarios_stats']

# Listas
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
FILES_SERVICES = ['prime', 'youtube', 'canva']
ALL_SERVICES = STREAMING + FILES_SERVICES + ['netflix', 'iptv']

# --- FUNÇÕES DE APOIO ---

def get_daily_count(user_id):
    hoje = datetime.now().strftime("%Y-%m-%d")
    user_data = users_col.find_one({"user_id": user_id})
    if not user_data or user_data.get("data") != hoje:
        users_col.update_one({"user_id": user_id}, {"$set": {"data": hoje, "contagem": 1}}, upsert=True)
        return 1
    else:
        nova_contagem = user_data["contagem"] + 1
        users_col.update_one({"user_id": user_id}, {"$set": {"contagem": nova_contagem}})
        return nova_contagem

def converter_nftoken(bruto):
    try:
        texto = urllib.parse.unquote(bruto.strip())
        if "ct=" in texto:
            token = texto.split("ct=")[1].split("&")[0].split()[0].split(";")[0]
        elif "NetflixId=" in texto:
            token = texto.split("NetflixId=")[1].split()[0].split(";")[0]
        else:
            token = bruto.strip()
        token = token.replace('-', '+').replace('_', '/')
        while len(token) % 4 != 0: token += '='
        return f"https://netflix.com/?nftoken={token}"
    except: return bruto

def criar_txt(servico, conteudo):
    buf = io.BytesIO(conteudo.encode('utf-8'))
    buf.name = f"{servico.upper()}_HIT.txt"
    return buf

# --- VERIFICAÇÃO DE PERMISSÃO ---
def can_use_bot(message):
    # Se for no grupo, qualquer um usa
    if message.chat.type in ['group', 'supergroup']:
        return True
    # Se for no privado, só o Thomas (Dono) usa
    if message.chat.type == 'private' and message.from_user.id == OWNER_ID:
        return True
    return False

# --- COMANDOS ---

@bot.message_handler(commands=['start', 'bot'])
def send_menu(message):
    if not can_use_bot(message):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💎 COMPRAR ACESSO VIP", url=VENDAS_LINK))
        bot.reply_to(message, "❌ *Acesso Negado!*\n\nEu respondo apenas em grupos. Para comprar seu acesso VIP e usar no privado, chame o dono.", parse_mode='Markdown', reply_markup=kb)
        return

    estoque = ""
    for s in ALL_SERVICES:
        qtd = db[s].count_documents({})
        estoque += f"🔹 /{s.capitalize()}: `{qtd}`\n"
    
    txt = (f"👋 Olá {message.from_user.first_name}!\n"
           f"🆔 Seu ID: `{message.from_user.id}`\n\n"
           f"📊 *ESTOQUE ATUAL:* \n{estoque}\n"
           f"👑 *By:* {CREDITOS}")
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💎 COMPRAR ACESSO VIP", url=VENDAS_LINK))
    bot.reply_to(message, txt, parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_gerar(message):
    if not can_use_bot(message): return

    cmd = message.text.split('@')[0].lower().replace("/", "")
    if cmd not in ALL_SERVICES: return

    try:
        res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
        if not res:
            bot.reply_to(message, f"⚠️ Estoque de {cmd.upper()} vazio!")
            return

        dados = res[0]['dados']
        u_name = message.from_user.first_name
        u_id = message.from_user.id
        count = get_daily_count(u_id)
        
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{u_id}"),
               types.InlineKeyboardButton("💎 COMPRAR VIP", url=VENDAS_LINK))

        header = (f"👤 *Usuário:* {u_name}\n"
                  f"🆔 *ID:* `{u_id}`\n"
                  f"🎫 *Geradas hoje:* `{count}`\n\n")

        if cmd == 'netflix':
            link = converter_nftoken(dados)
            msg = f"✅ *NETFLIX GERADA*\n\n{header}🔗 [CLIQUE AQUI PARA LOGAR]({link})\n\n🚀 {CREDITOS}"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=kb)
        elif cmd in FILES_SERVICES:
            arquivo = criar_txt(cmd, dados)
            bot.send_document(message.chat.id, arquivo, caption=f"✅ {cmd.upper()} GERADA!\n\n{header}🚀 {CREDITOS}", parse_mode='Markdown', reply_markup=kb)
        elif cmd == 'iptv':
            bot.send_message(message.chat.id, f"✅ *IPTV GERADA*\n\n{header}```\n{dados}\n```\n🚀 {CREDITOS}", parse_mode='Markdown', reply_markup=kb)
        else:
            bot.send_message(message.chat.id, f"✅ *{cmd.upper()} GERADA*\n\n{header}`{dados}`\n\n🚀 {CREDITOS}", parse_mode='Markdown', reply_markup=kb)

        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
    except Exception as e:
        print(f"Erro: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete(call):
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

# --- GESTÃO THOMAS ---

@bot.message_handler(content_types=['document'])
def handle_upload(message):
    if message.from_user.id != OWNER_ID: return
    serv = message.caption.lower() if message.caption else ""
    if serv in ALL_SERVICES:
        content = bot.download_file(bot.get_file(message.document.file_id).file_path).decode('utf-8', errors='ignore')
        if serv == 'iptv':
            hits = content.split('--------------------------------------------------')
            docs = [{"dados": h.strip()} for h in hits if len(h.strip()) > 10]
        else:
            docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
        if docs:
            db[serv].insert_many(docs)
            bot.reply_to(message, f"🚀 Adicionadas {len(docs)} contas em {serv.upper()}!")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def clear_category(message):
    if message.from_user.id != OWNER_ID: return
    try:
        s_limpar = message.text.lower().split("_")[1]
        db[s_limpar].delete_many({})
        bot.reply_to(message, f"🗑️ Estoque de {s_limpar.upper()} limpo!")
    except: pass

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000), daemon=True).start()
    bot.remove_webhook()
    print("🚀 Thomas Tracker V8.1 Online!")
    bot.infinity_polling(skip_pending=True)
