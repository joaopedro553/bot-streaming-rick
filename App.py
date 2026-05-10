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

# --- DEFINIÇÃO DE SERVIÇOS ---
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
COOKIES = ['netflix', 'prime', 'canva', 'youtube'] # Netflix vira link, Prime/YouTube viram arquivos, Canva link
LISTAS = ['iptv']

ALL_SERVICES = STREAMING + COOKIES + LISTAS

# --- FUNÇÕES INTELIGENTES ---

def escape_md(text):
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_']:
        text = str(text).replace(char, f"\\{char}")
    return text

def criar_arquivo_txt(nome, conteudo):
    """Cria um arquivo .txt virtual para envio"""
    buf = io.BytesIO(conteudo.encode('utf-8'))
    buf.name = f"{nome}_CONTA.txt"
    return buf

# --- FILTROS ---

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def block_private(message):
    bot.reply_to(message, f"👋 Olá {message.from_user.first_name}!\n\n❌ *Acesso Negado*\nPara gerar contas, entre no grupo oficial!\n\n💎 *QUER ACESSO VIP 30 DIAS?*\nChame agora: {CREDITOS}", parse_mode='Markdown')

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def menu_v3(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    txt = (f"👋 *Olá {message.from_user.first_name}\! ID:* `{message.from_user.id}`\n\n"
           f"🚀 *QUER CONTAS EXCLUSIVAS E SEM LIMITES?*\n"
           f"Adquira o *VIP 30 DIAS* chamando {escape_md(CREDITOS)}\n\n"
           f"📽️ *STREAMING:* \n")
    for s in STREAMING:
        qtd = db[s].count_documents({})
        txt += f" ├ /{s.capitalize()}: `{qtd}`\n"
    
    txt += f"\n🍪 *COOKIES:* \n"
    for s in COOKIES:
        qtd = db[s].count_documents({})
        txt += f" ├ /{s.capitalize()}: `{qtd}`\n"

    txt += f"\n📡 *LISTAS:* \n"
    for s in LISTAS:
        qtd = db[s].count_documents({})
        txt += f" └ /{s.capitalize()}: `{qtd}`\n"
    
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
        user_name = message.from_user.first_name
        user_id = message.from_user.id

        # --- GERAÇÃO DE MENSAGEM DE ANÚNCIO ---
        anuncio = (f"👋 *Olá {escape_md(user_name)}\! ID:* `{user_id}`\n"
                   f"💎 *DICA:* Compre acesso VIP 30 dias com {escape_md(CREDITOS)} e tenha o melhor estoque do Telegram\!")

        # --- LÓGICA DE ENVIO POR FORMATO ---
        
        # 1. IPTV (Template Estruturado)
        if cmd == 'iptv':
            msg_iptv = (f"✅ *IPTV GERADA COM SUCESSO\!*\n\n"
                        f"```\n{dados}\n```\n"
                        f"🚀 *Créditos:* {escape_md(CREDITOS)}")
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            bot.send_message(message.chat.id, msg_iptv, parse_mode='MarkdownV2')

        # 2. NETFLIX (Link NFT TOKEN)
        elif cmd == 'netflix':
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            bot.send_message(message.chat.id, f"✅ *NETFLIX GERADA\!*\n\n🔗 *Link Token:* [CLIQUE AQUI PARA ACESSAR]({dados})\n\n🚀 *By:* {escape_md(CREDITOS)}", parse_mode='MarkdownV2')

        # 3. PRIME E YOUTUBE (Envia arquivo .txt)
        elif cmd in ['prime', 'youtube']:
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            arquivo = criar_arquivo_txt(cmd.upper(), dados)
            bot.send_document(message.chat.id, arquivo, caption=f"✅ {cmd.upper()} enviada em arquivo .txt\n\n🚀 *Créditos:* {CREDITOS}", parse_mode='Markdown')

        # 4. CANVA (Link direto)
        elif cmd == 'canva':
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            bot.send_message(message.chat.id, f"✅ *CANVA GERADO\!*\n\n🔗 *Convite:* [CLIQUE AQUI]({dados})\n\n🚀 *By:* {escape_md(CREDITOS)}", parse_mode='MarkdownV2')

        # 5. STREAMING PADRÃO (Email:Senha)
        else:
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            if ":" in dados:
                u, s = dados.split(":", 1)
                final = f"✅ *{cmd.upper()} GERADA\!*\n\n✉️ *E\-mail:* `{u}`\n🔑 *Senha:* `{s}`"
            else:
                final = f"✅ *{cmd.upper()} GERADA\!*\n\n`{dados}`"
            
            bot.send_message(message.chat.id, final + f"\n\n🚀 *Créditos:* {escape_md(CREDITOS)}", parse_mode='MarkdownV2')

        # Deleta o comando do usuário no grupo
        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass

    except Exception as e:
        print(f"Erro: {e}")

# --- GESTÃO THOMAS ---
@bot.message_handler(content_types=['document'])
def handle_txt(message):
    if message.from_user.id != OWNER_ID: return
    serv = message.caption.lower() if message.caption else ""
    if serv in ALL_SERVICES:
        content = bot.download_file(bot.get_file(message.document.file_id).file_path).decode('utf-8')
        docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
        if docs:
            db[serv].insert_many(docs)
            bot.reply_to(message, f"🚀 Thomas, adicionei as contas em {serv}!")
    else:
        bot.reply_to(message, "❌ Nome do serviço inválido na legenda!")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def handle_clear(message):
    if message.from_user.id != OWNER_ID: return
    s = message.text.lower().replace("/limpa_", "")
    if s in ALL_SERVICES:
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ Banco `{s.upper()}` zerado!")

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    print("🚀 Bot Thomas V3.0 - MEGA ATUALIZAÇÃO!")
    bot.infinity_polling(skip_pending=True)
