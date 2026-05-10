import telebot
import os
import threading
import time
import re
import io
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
TOKEN = "8479454342:AAEaNuwOS9WJnTrDb_LmSvWHAw0AbFRB7iU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
OWNER_ID = 1031830691 # Thomas
VENDAS_LINK = "https://t.me/ThomasObscuro"
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']

# --- SERVIÇOS ---
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
FILES_SERVICES = ['prime', 'youtube', 'canva']
SPECIAL_SERVICES = ['netflix', 'iptv']
ALL_SERVICES = STREAMING + FILES_SERVICES + SPECIAL_SERVICES

def escape_md(text):
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_', r'=']:
        text = str(text).replace(char, f"\\{char}")
    return text

def criar_txt_memoria(servico, conteudo):
    buf = io.BytesIO(conteudo.encode('utf-8'))
    buf.name = f"{servico.upper()}_CONTA.txt"
    return buf

# --- COMANDOS DE GESTÃO (SÓ THOMAS - PRIORIDADE MÁXIMA) ---

# Comando de Limpeza (Aceita /Limpa_ ou /limpa_)
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("/limpa_"))
def clear_db(message):
    if message.from_user.id != OWNER_ID: return
    # Extrai o nome do serviço
    try:
        servico_para_limpar = message.text.lower().split("_")[1]
        if servico_para_limpar in ALL_SERVICES:
            db[servico_para_limpar].delete_many({})
            bot.reply_to(message, f"🗑️ *Thomas, o banco de {servico_para_limpar.upper()} foi zerado!*", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ Serviço `{servico_para_limpar}` não existe na lista.")
    except:
        bot.reply_to(message, "❌ Use: `/Limpa_servico` (Ex: /Limpa_netflix)")

# Abastecer via Arquivo
@bot.message_handler(content_types=['document'])
def handle_upload(message):
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
        bot.reply_to(message, "❌ Legenda inválida! Use o nome de um serviço.")

# --- COMANDOS DO GRUPO ---

@bot.message_handler(commands=['bot'])
def menu_v3(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    txt = (f"👋 *Olá {message.from_user.first_name}\! ID:* `{message.from_user.id}`\n\n"
           f"🚀 *QUER CONTAS EXCLUSIVAS E SEM LIMITES?*\n"
           f"Adquira o *VIP 30 DIAS* chamando {escape_md(CREDITOS)}\n\n"
           f"📊 *ESTOQUE DISPONÍVEL:* \n")
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

    try:
        res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
        if not res:
            bot.reply_to(message, f"⚠️ Estoque de {cmd.upper()} vazio!")
            return

        dados = res[0].get('dados', 'erro')
        anuncio = (f"👋 *Olá {escape_md(message.from_user.first_name)}\! ID:* `{message.from_user.id}`\n"
                   f"👑 Adquira seu *VIP 30 DIAS* com {escape_md(CREDITOS)} agora\!")
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
               types.InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_LINK))

        if cmd == 'iptv':
            msg = f"✅ *IPTV GERADA\!*\n\n```\n{dados}\n```\n🚀 *Créditos:* {escape_md(CREDITOS)}"
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            bot.send_message(message.chat.id, msg, parse_mode='MarkdownV2', reply_markup=kb)
        elif cmd == 'netflix':
            msg = f"✅ *NETFLIX GERADA\!*\n\n🔗 [CLIQUE AQUI PARA ACESSAR]({dados})\n\n🚀 *By:* {escape_md(CREDITOS)}"
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            bot.send_message(message.chat.id, msg, parse_mode='MarkdownV2', reply_markup=kb)
        elif cmd in FILES_SERVICES:
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            arquivo = criar_txt_memoria(cmd, dados)
            bot.send_document(message.chat.id, arquivo, caption=f"✅ {cmd.upper()} em arquivo \.txt", reply_markup=kb, parse_mode='MarkdownV2')
        else:
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            if ":" in dados:
                u, s = dados.split(":", 1)
                final = f"✅ *{cmd.upper()} GERADA\!*\n\n✉️ *E\-mail:* `{u}`\n🔑 *Senha:* `{s}`"
            else:
                final = f"✅ *{cmd.upper()} GERADA\!*\n\n`{dados}`"
            bot.send_message(message.chat.id, final + f"\n\n🚀 *By:* {escape_md(CREDITOS)}", parse_mode='MarkdownV2', reply_markup=kb)

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
    bot.infinity_polling(skip_pending=True)
