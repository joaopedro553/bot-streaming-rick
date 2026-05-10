import telebot
import os
import threading
import time
import re
import io
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
TOKEN = "8479454342:AAEaNuwOS9WJnTrDb_LmSvWHAw0AbFRB7iU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
OWNER_ID = 1031830691 
VENDAS_LINK = "https://t.me/ThomasObscuro"
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=20) # Aumentado para 3.000 membros
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)
db = client['streaming_db']

# Listas de serviços
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
COOKIES_FILES = ['prime', 'youtube', 'canva']
SPECIAL = ['netflix', 'iptv']
ALL_SERVICES = STREAMING + COOKIES_FILES + SPECIAL

# --- FUNÇÕES ---

def criar_txt_memoria(servico, conteudo):
    buf = io.BytesIO(conteudo.encode('utf-8'))
    buf.name = f"{servico.upper()}_CONTA.txt"
    return buf

def is_allowed(message):
    if message.chat.id in ALLOWED_GROUPS: return True
    if message.from_user.id == OWNER_ID: return True
    return False

# --- GESTÃO THOMAS (PRIVADO) ---

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("/limpa_"))
def clear_db(message):
    if message.from_user.id != OWNER_ID: return
    try:
        s_limpar = message.text.lower().split("_", 1)[1]
        db[s_limpar].delete_many({})
        bot.reply_to(message, f"🗑️ Thomas, estoque de {s_limpar.upper()} zerado!")
    except: pass

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
            bot.reply_to(message, f"🚀 Thomas, {len(docs)} contas em {serv.upper()}!")
    else:
        bot.reply_to(message, "❌ Nome do serviço inválido na legenda!")

# --- COMANDOS DO GRUPO ---

@bot.message_handler(commands=['bot'])
def send_menu(message):
    if not is_allowed(message): return
    
    estoque = ""
    for s in ALL_SERVICES:
        try:
            qtd = db[s].count_documents({})
            estoque += f"🔹 /{s.capitalize()}: {qtd}\n"
        except: pass

    txt = (f"👋 Olá {message.from_user.first_name}! ID: `{message.from_user.id}`\n\n"
           f"💎 *VIP 30 DIAS:* Chama {CREDITOS}\n\n"
           f"📊 *ESTOQUE ATUAL:* \n{estoque}\n"
           f"👑 *By:* {CREDITOS}")
    bot.reply_to(message, txt, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_gerar(message):
    if not is_allowed(message): 
        if message.chat.type == 'private':
            bot.reply_to(message, f"❌ Acesso Negado! Entre no grupo VIP ou chame {CREDITOS}")
        return

    cmd = message.text.split('@')[0].lower().replace("/", "")
    if cmd not in ALL_SERVICES: return

    try:
        res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
        if not res:
            bot.reply_to(message, f"⚠️ Estoque de {cmd.upper()} vazio!")
            return

        dados = res[0].get('dados', 'erro')
        u_name = message.from_user.first_name
        u_id = message.from_user.id
        
        anuncio = (f"👋 Olá {u_name}! ID: `{u_id}`\n"
                   f"👑 Adquira seu *VIP 30 DIAS* com {CREDITOS} agora!")

        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{u_id}"),
               types.InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_LINK))

        if cmd == 'iptv':
            msg = f"✅ *IPTV GERADA*\n\n```\n{dados}\n```\n🚀 *Créditos:* {CREDITOS}"
            bot.send_message(message.chat.id, anuncio)
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=kb)
        elif cmd == 'netflix':
            msg = f"✅ *NETFLIX GERADA*\n\n🔗 [CLIQUE AQUI PARA ACESSAR]({dados})\n\n🚀 *Créditos:* {CREDITOS}"
            bot.send_message(message.chat.id, anuncio)
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=kb)
        elif cmd in COOKIES_FILES:
            bot.send_message(message.chat.id, anuncio)
            arquivo = criar_txt_memoria(cmd, dados)
            bot.send_document(message.chat.id, arquivo, caption=f"✅ {cmd.upper()} em .txt\n\n🚀 *By:* {CREDITOS}", reply_markup=kb)
        else:
            bot.send_message(message.chat.id, anuncio)
            if ":" in dados:
                u, s = dados.split(":", 1)
                final = f"✅ *{cmd.upper()} GERADA*\n\n✉️ E-mail: `{u}`\n🔑 Senha: `{s}`"
            else:
                final = f"✅ *{cmd.upper()} GERADA*\n\n`{dados}`"
            bot.send_message(message.chat.id, final + f"\n\n🚀 *By:* {CREDITOS}", parse_mode='Markdown', reply_markup=kb)

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

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("🧹 Limpando fila e iniciando...")
    bot.remove_webhook()
    time.sleep(2)
    
    # skip_pending=True é o segredo para ele não travar ao ligar
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
