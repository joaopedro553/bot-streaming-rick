import telebot
import os
import threading
import time
import re
import io
import requests
import urllib.parse
from datetime import datetime
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
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']

STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
FILES_SERVICES = ['prime', 'youtube', 'canva']
ALL_SERVICES = STREAMING + FILES_SERVICES + ['netflix', 'iptv']

# --- FUNÇÕES DE INTELIGÊNCIA ---

def extract_nid(texto):
    """Busca o NetflixId para o Checker"""
    try:
        if "NetflixId=" in texto:
            return texto.split("NetflixId=")[1].split(";")[0].split()[0]
        return None
    except: return None

def check_netflix_live(texto_bruto):
    """Simula login para ver se a conta está ativa"""
    nid = extract_nid(texto_bruto)
    if not nid: return False
    
    url = "https://www.netflix.com/browse"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    try:
        res = requests.get(url, cookies={"NetflixId": nid}, headers=headers, timeout=10, allow_redirects=False)
        return res.status_code == 200 or (res.status_code == 302 and "/browse" in res.headers.get('Location', ''))
    except: return False

def fix_nftoken_link(dados):
    """Garante que o link saia no formato correto"""
    if dados.startswith("http"): return dados
    # Se for apenas o token, monta o link
    token = dados.replace('-', '+').replace('_', '/')
    while len(token) % 4 != 0: token += '='
    return f"https://netflix.com/?nftoken={token}"

def escape_md(text):
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_', r'=']:
        text = str(text).replace(char, f"\\{char}")
    return text

# --- FILTROS ---

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def r_private(message):
    bot.reply_to(message, f"❌ *Acesso Negado\!*\nPara gerar contas, entre no grupo VIP\.\n\n💎 *VIP 30 DIAS:* Chama {CREDITOS}", parse_mode='Markdown')

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def send_menu(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    txt = (f"👋 *Olá {message.from_user.first_name}\! ID:* `{message.from_user.id}`\n\n"
           f"📊 *ESTOQUE THOMAS CHECKER:* \n")
    for s in ALL_SERVICES:
        qtd = db[s].count_documents({})
        txt += f" ├ /{s.capitalize()}: `{qtd}`\n"
    txt += f"\n👑 *By:* {escape_md(CREDITOS)}"
    bot.reply_to(message, txt, parse_mode='MarkdownV2')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def logic_gerar(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    cmd = message.text.split('@')[0].lower().replace("/", "")
    if cmd not in ALL_SERVICES: return

    msg_wait = bot.reply_to(message, f"⏳ *Thomas está verificando uma conta {cmd.upper()} para você...*", parse_mode='Markdown')

    try:
        # --- LÓGICA ESPECIAL NETFLIX (LOOP INFINITO ATÉ ACHAR VIVA) ---
        if cmd == 'netflix':
            found = False
            attempts = 0
            while not found and attempts < 25: # Tenta até 25 contas por clique
                attempts += 1
                res = list(db['netflix'].aggregate([{"$sample": {"size": 1}}]))
                if not res: break
                
                bruto = res[0]['dados']
                obj_id = res[0]['_id']

                if check_netflix_live(bruto):
                    link = fix_nftoken_link(bruto)
                    bot.delete_message(message.chat.id, msg_wait.message_id)
                    
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
                           types.InlineKeyboardButton("🛒 COMPRAR VIP", url="https://t.me/ThomasObscuro"))
                    
                    bot.send_message(message.chat.id, f"👋 *Olá {message.from_user.first_name}\! ID:* `{message.from_user.id}`\n\n✅ *NETFLIX VIVA ENCONTRADA\!*\n\n🔗 [CLIQUE AQUI PARA LOGAR]({link})\n\n🚀 *Créditos:* {escape_md(CREDITOS)}", parse_mode='MarkdownV2', reply_markup=kb)
                    found = True
                else:
                    # CONTA MORTA: Deleta do banco para sempre
                    db['netflix'].delete_one({"_id": obj_id})
            
            if not found:
                bot.edit_message_text("⚠️ *Estoque limpo!* Tentei várias contas e todas estavam mortas. Thomas será notificado.", message.chat.id, msg_wait.message_id, parse_mode='Markdown')
                bot.send_message(OWNER_ID, "📢 *ALERTA:* O estoque de Netflix acabou ou os cookies expiraram!")

        # --- IPTV, PRIME, E OUTROS (MESMA LÓGICA ANTERIOR) ---
        else:
            res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
            if res:
                bot.delete_message(message.chat.id, msg_wait.message_id)
                dados = res[0]['dados']
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"))
                
                if cmd == 'iptv':
                    bot.send_message(message.chat.id, f"✅ *IPTV GERADA*\n\n```\n{dados}\n```\n🚀 *By:* {CREDITOS}", parse_mode='Markdown', reply_markup=kb)
                elif cmd in FILES_SERVICES:
                    buf = io.BytesIO(dados.encode('utf-8'))
                    buf.name = f"{cmd.upper()}_CONTA.txt"
                    bot.send_document(message.chat.id, buf, caption=f"✅ {cmd.upper()} gerada!", reply_markup=kb)
                else:
                    bot.send_message(message.chat.id, f"✅ *{cmd.upper()} GERADA*\n\n`{dados}`", parse_mode='Markdown', reply_markup=kb)
            else: bot.edit_message_text("⚠️ Estoque vazio!", message.chat.id, msg_wait.message_id)

    except: pass

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
            docs = [{"dados": h.strip()} for h in content.split('--------------------------------------------------') if len(h.strip()) > 10]
        else:
            docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
        if docs:
            db[serv].insert_many(docs)
            bot.reply_to(message, f"🚀 Adicionadas {len(docs)} contas em {serv}!")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("/limpa_"))
def clear_category(message):
    if message.from_user.id != OWNER_ID: return
    try:
        s = message.text.lower().split("_")[1]
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ Estoque de {s.upper()} limpo!")
    except: pass

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
