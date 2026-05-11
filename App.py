import telebot
import os
import threading
import time
import re
import io
import urllib.parse
from datetime import datetime
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
users_col = db['usuarios_stats'] # Coleção para contar as gerações diárias

# Listas
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
FILES_SERVICES = ['prime', 'youtube', 'canva']
ALL_SERVICES = STREAMING + FILES_SERVICES + ['netflix', 'iptv']

# --- FUNÇÕES DE APOIO ---

def get_daily_count(user_id):
    """Gerencia o contador diário de cada usuário"""
    hoje = datetime.now().strftime("%Y-%m-%d")
    user_data = users_col.find_one({"user_id": user_id})
    
    if not user_data or user_data.get("data") != hoje:
        # Se é um novo dia ou novo usuário, reseta para 1
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"data": hoje, "contagem": 1}},
            upsert=True
        )
        return 1
    else:
        # Incrementa a contagem do dia
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

# --- FILTRO DE PRIVADO ---

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def restringir_privado(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🛒 COMPRAR ACESSO VIP", url=VENDAS_LINK))
    bot.reply_to(message, "❌ *Acesso Negado!*\n\nEu respondo apenas em grupos autorizados. Para comprar seu acesso VIP 30 dias e usar no privado, chame o dono.", parse_mode='Markdown', reply_markup=kb)

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def send_menu(message):
    # Responde em qualquer grupo ou para o dono no privado
    estoque = ""
    for s in ALL_SERVICES:
        qtd = db[s].count_documents({})
        estoque += f"🔹 /{s.capitalize()}: `{qtd}`\n"
    
    txt = (f"👋 Olá {message.from_user.first_name}!\n"
           f"🆔 Seu ID: `{message.from_user.id}`\n\n"
           f"📊 *ESTOQUE THOMAS CHECKER:* \n{estoque}\n"
           f"👑 *By:* {CREDITOS}")
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💎 COMPRAR ACESSO VIP", url=VENDAS_LINK))
    bot.reply_to(message, txt, parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_gerar(message):
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
        count = get_daily_count(u_id) # Pega contagem do dia
        
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{u_id}"),
               types.InlineKeyboardButton("💎 COMPRAR VIP", url=VENDAS_LINK))

        header = (f"👤 *Usuário:* {u_name}\n"
                  f"🆔 *ID:* `{u_id}`\n"
                  f"🎫 *Geradas hoje:* `{count}`\n\n")

        # 1. Netflix
        if cmd == 'netflix':
            link = converter_nftoken(dados)
            msg = f"✅ *NETFLIX GERADA*\n\n{header}🔗 [CLIQUE AQUI PARA LOGAR]({link})\n\n🚀 {CREDITOS}"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=kb)

        # 2. Arquivos (Prime, Youtube, Canva)
        elif cmd in FILES_SERVICES:
            arquivo = criar_txt(cmd, dados)
            cap = f"✅ {cmd.upper()} GERADA!\n\n{header}🚀 {CREDITOS}"
            bot.send_document(message.chat.id, arquivo, caption=cap, parse_mode='Markdown', reply_markup=kb)

        # 3. IPTV (Bloco de código)
        elif cmd == 'iptv':
            msg = f"✅ *IPTV GERADA*\n\n{header}```\n{dados}\n```\n🚀 {CREDITOS}"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=kb)

        # 4. Outros
        else:
            final = f"✅ *{cmd.upper()} GERADA*\n\n{header}`{dados}`\n\n🚀 {CREDITOS}"
            bot.send_message(message.chat.id, final, parse_mode='Markdown', reply_markup=kb)

        # Limpa o comando do usuário no grupo
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
            bot.reply_to(message, f"🚀 Sucesso! {len(docs)} contas em {serv.upper()}!")

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
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    print("🚀 Thomas Tracker V8 Online!")
    bot.infinity_polling(skip_pending=True)
