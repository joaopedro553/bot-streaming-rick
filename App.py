import telebot
import os
import threading
import time
import re
import io
import urllib.parse
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
TOKEN = "8479454342:AAEaNuwOS9WJnTrDb_LmSvWHAw0AbFRB7iU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
OWNER_ID = 1031830691 
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN, threaded=True)
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)
db = client['streaming_db']

# Listas
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
FILES_SERVICES = ['prime', 'youtube', 'canva']
ALL_SERVICES = STREAMING + FILES_SERVICES + ['netflix', 'iptv']

# --- FUNÇÕES DE CONVERSÃO ---

def converter_nftoken(bruto):
    """Converte cookie/ct para link nftoken oficial"""
    try:
        texto = urllib.parse.unquote(bruto.strip())
        # Tenta pegar o valor de ct=
        if "ct=" in texto:
            token = texto.split("ct=")[1].split("&")[0].split()[0].split(";")[0]
        elif "NetflixId=" in texto:
            token = texto.split("NetflixId=")[1].split()[0].split(";")[0]
        else:
            token = bruto.strip()
        
        # Ajusta base64 para Web
        token = token.replace('-', '+').replace('_', '/')
        while len(token) % 4 != 0: token += '='
        return f"https://netflix.com/?nftoken={token}"
    except:
        return bruto # Se falhar, manda o que tiver

def criar_txt(servico, conteudo):
    buf = io.BytesIO(conteudo.encode('utf-8'))
    buf.name = f"{servico.upper()}_HIT.txt"
    return buf

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def send_menu(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    estoque = ""
    for s in ALL_SERVICES:
        qtd = db[s].count_documents({})
        estoque += f"🔹 /{s.capitalize()}: `{qtd}`\n"

    txt = (f"👋 Olá {message.from_user.first_name}! ID: `{message.from_user.id}`\n\n"
           f"📊 *ESTOQUE THOMAS CHECKER:* \n{estoque}\n"
           f"👑 *By:* {CREDITOS}")
    bot.reply_to(message, txt, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_gerar(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: 
        if message.chat.type == 'private':
            bot.reply_to(message, "❌ Use os grupos oficiais!")
        return

    cmd = message.text.split('@')[0].lower().replace("/", "")
    if cmd not in ALL_SERVICES: return

    try:
        # Sorteia 1 hit aleatório do banco
        res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
        if not res:
            bot.reply_to(message, f"⚠️ Estoque de {cmd.upper()} vazio!")
            return

        dados = res[0]['dados']
        u_name = message.from_user.first_name
        u_id = message.from_user.id
        
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{u_id}"),
               types.InlineKeyboardButton("🛒 COMPRAR VIP", url="https://t.me/ThomasObscuro"))

        # 1. Lógica Netflix
        if cmd == 'netflix':
            link = converter_nftoken(dados)
            msg = f"✅ *NETFLIX GERADA*\n\n🔗 [CLIQUE AQUI PARA LOGAR]({link})\n\n👤 Para: {u_name}\n🚀 {CREDITOS}"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=kb)

        # 2. Lógica Arquivos (Prime, Youtube, Canva)
        elif cmd in FILES_SERVICES:
            arquivo = criar_txt(cmd, dados)
            cap = f"✅ {cmd.upper()} GERADA!\n👤 Para: {u_name}\n🚀 {CREDITOS}"
            bot.send_document(message.chat.id, arquivo, caption=cap, reply_markup=kb)

        # 3. Lógica IPTV (Bloco de código)
        elif cmd == 'iptv':
            msg = f"✅ *IPTV GERADA*\n\n```\n{dados}\n```\n🚀 {CREDITOS}"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=kb)

        # 4. Outros Streaming
        else:
            final = f"✅ *{cmd.upper()} GERADA*\n\n`{dados}`\n\n🚀 {CREDITOS}"
            bot.send_message(message.chat.id, final, parse_mode='Markdown', reply_markup=kb)

        # Limpa o comando do usuário no grupo
        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass

    except Exception as e:
        print(f"Erro: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_del(call):
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
            # Separa pelos traços
            docs = [{"dados": h.strip()} for h in content.split('--------------------------------------------------') if len(h.strip()) > 10]
        else:
            # Separa por linha
            docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
        if docs:
            db[serv].insert_many(docs)
            bot.reply_to(message, f"🚀 Sucesso! {len(docs)} contas em {serv.upper()}!")
    else:
        bot.reply_to(message, "❌ Legenda inválida!")

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
    print("🚀 Bot Thomas V7 - Versão Ultra Rápida Online!")
    bot.infinity_polling(skip_pending=True)
