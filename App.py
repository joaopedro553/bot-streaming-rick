import telebot
import os
import threading
import time
import re
import io
from datetime import datetime
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES CRÍTICAS ---
# Usando o seu Token mais recente
TOKEN = "8479454342:AAEaNuwOS9WJnTrDb_LmSvWHAw0AbFRB7iU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

# GRUPOS AUTORIZADOS
ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
OWNER_ID = 1031830691 # Thomas
LINK_GRUPO_GRATIS = "https://t.me/ThomasAccount01"
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)
db = client['streaming_db']

# --- DEFINIÇÃO DE SERVIÇOS ---
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
FILES_SERVICES = ['prime', 'youtube', 'canva']
SPECIAL_SERVICES = ['netflix', 'iptv']
ALL_SERVICES = STREAMING + FILES_SERVICES + SPECIAL_SERVICES

# --- FUNÇÕES DE ESTILO ---

def escape_md(text):
    """Limpa caracteres que costumam dar erro no Telegram"""
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_', r'=']:
        text = str(text).replace(char, f"\\{char}")
    return text

def criar_txt_memoria(servico, conteudo):
    """Gera o arquivo .txt na memória sem gastar espaço"""
    buf = io.BytesIO(conteudo.encode('utf-8'))
    buf.name = f"{servico.upper()}_CONTA.txt"
    return buf

# --- FILTROS E TRAVAS ---

def is_allowed(message):
    if message.chat.id in ALLOWED_GROUPS: return True
    if message.from_user.id == OWNER_ID and message.chat.type == 'private': return True
    return False

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def block_strangers(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⭐ GRUPO THOMAS FREE", url=LINK_GRUPO_GRATIS))
    msg = (f"👋 Olá {message.from_user.first_name}\! ID: `{message.from_user.id}`\n\n"
           f"❌ *Acesso Negado\!*\n\nEu funciono apenas no grupo oficial para membros\.\n"
           f"Adquira seu *VIP 30 DIAS* chamando {escape_md(CREDITOS)}")
    bot.reply_to(message, msg, parse_mode='MarkdownV2', reply_markup=kb)

# --- COMANDOS DE GESTÃO (SÓ THOMAS) ---

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("/limpa_"))
def clear_category(message):
    if message.from_user.id != OWNER_ID: return
    try:
        s_limpar = message.text.lower().split("_", 1)[1]
        if s_limpar in ALL_SERVICES:
            db[s_limpar].delete_many({})
            bot.reply_to(message, f"🗑️ *Thomas, o estoque de {s_limpar.upper()} foi apagado!*")
    except: pass

@bot.message_handler(content_types=['document'])
def receive_stock(message):
    if message.from_user.id != OWNER_ID: return
    serv = message.caption.lower() if message.caption else ""
    if serv in ALL_SERVICES:
        content = bot.download_file(bot.get_file(message.document.file_id).file_path).decode('utf-8')
        if serv == 'iptv':
            hits = content.split('--------------------------------------------------')
            docs = [{"dados": h.strip()} for h in hits if len(h.strip()) > 10]
        else:
            docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
        
        if docs:
            db[serv].insert_many(docs)
            bot.reply_to(message, f"🚀 Thomas, adicionei {len(docs)} itens em {serv.upper()}!")
    else:
        bot.reply_to(message, "❌ Legenda inválida! Use o nome do serviço.")

# --- COMANDOS DO GRUPO ---

@bot.message_handler(commands=['bot'])
def send_menu(message):
    if not is_allowed(message): return
    txt = (f"👋 *Olá {message.from_user.first_name}\! ID:* `{message.from_user.id}`\n\n"
           f"💎 *ACESSO VIP 30 DIAS:* Chama {escape_md(CREDITOS)}\n\n"
           f"📊 *ESTOQUE ATUAL:* \n")
    for s in ALL_SERVICES:
        qtd = db[s].count_documents({})
        txt += f" ├ /{s.capitalize()}: `{qtd}`\n"
    txt += f"\n👑 *Dono:* {escape_md(CREDITOS)}"
    bot.reply_to(message, txt, parse_mode='MarkdownV2')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def delivery_logic(message):
    if not is_allowed(message): return
    cmd = message.text.split('@')[0].lower().replace("/", "")
    if cmd not in ALL_SERVICES: return

    try:
        res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
        if not res:
            bot.reply_to(message, f"⚠️ Estoque de {cmd.upper()} vazio!")
            return

        dados = res[0].get('dados', 'erro')
        u_name = escape_md(message.from_user.first_name)
        u_id = message.from_user.id

        anuncio = (f"👋 *Olá {u_name}\! ID:* `{u_id}`\n"
                   f"👑 Adquira seu *VIP 30 DIAS* com {escape_md(CREDITOS)} agora\!")
        
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{u_id}"),
               types.InlineKeyboardButton("🛒 COMPRAR VIP", url="https://t.me/ThomasObscuro"))

        # --- ENVIO POR FORMATO ---
        if cmd == 'iptv':
            msg = f"✅ *IPTV GERADA*\n\n```\n{dados}\n```\n🚀 *Créditos:* {escape_md(CREDITOS)}"
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            bot.send_message(message.chat.id, msg, parse_mode='MarkdownV2', reply_markup=kb)
        
        elif cmd == 'netflix':
            msg = f"✅ *NETFLIX GERADA*\n\n🔗 [CLIQUE PARA ACESSAR]({dados})\n\n🚀 *Créditos:* {escape_md(CREDITOS)}"
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            bot.send_message(message.chat.id, msg, parse_mode='MarkdownV2', reply_markup=kb)
            
        elif cmd in FILES_SERVICES:
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            arquivo = criar_txt_memoria(cmd, dados)
            bot.send_document(message.chat.id, arquivo, caption=f"✅ {cmd.upper()} enviada em arquivo \.txt\n\n🚀 *By:* {CREDITOS}", reply_markup=kb)
            
        else:
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            txt_final = f"✅ *{cmd.upper()} GERADA*\n\n`{escape_md(dados)}`" if ":" not in dados else f"✅ *{cmd.upper()} GERADA*\n\n✉️ E-mail: `{escape_md(dados.split(':')[0])}`\n🔑 Senha: `{escape_md(dados.split(':')[1])}`"
            bot.send_message(message.chat.id, txt_final + f"\n\n🚀 *Créditos:* {escape_md(CREDITOS)}", parse_mode='MarkdownV2', reply_markup=kb)

        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_del(call):
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
    else:
        bot.answer_callback_query(call.id, "❌ Essa conta não é sua!", show_alert=True)

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    print("🚀 THOMAS CHECKER BLACK EDITION ONLINE!")
    bot.infinity_polling(skip_pending=True)
