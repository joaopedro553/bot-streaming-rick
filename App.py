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

# GRUPOS AUTORIZADOS
ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
OWNER_ID = 1031830691 
CREDITOS = "@ThomasObscuro"
VENDAS_LINK = "https://t.me/ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']

# --- DEFINIÇÃO DE SERVIÇOS ---
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
# Serviços que o bot vai gerar um arquivo .txt na hora
FILES_SERVICES = ['prime', 'youtube', 'canva']
# Serviços com links longos ou blocos de código
SPECIAL_SERVICES = ['netflix', 'iptv']

ALL_SERVICES = STREAMING + FILES_SERVICES + SPECIAL_SERVICES

# --- FUNÇÕES DE FORMATO ---

def escape_md(text):
    """Protege contra erros do Telegram MarkdownV2"""
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_', r'=']:
        text = str(text).replace(char, f"\\{char}")
    return text

def criar_txt_memoria(servico, conteudo):
    """Cria o arquivo .txt sem gastar memória do celular ou servidor"""
    buf = io.BytesIO(conteudo.encode('utf-8'))
    buf.name = f"{servico.upper()}_CONTA.txt"
    return buf

# --- FILTROS ---

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def r_private(message):
    bot.reply_to(message, f"👋 Olá {message.from_user.first_name}!\n\n❌ *ACESSO NEGADO*\nEu funciono apenas no grupo VIP.\n\n💎 *QUER ACESSO TOTAL?*\nChama agora: {CREDITOS}", parse_mode='Markdown')

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def menu_v3(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    txt = (f"👋 *Olá {message.from_user.first_name}\! ID:* `{message.from_user.id}`\n\n"
           f"🚀 *QUER CONTAS EXCLUSIVAS E SEM LIMITES?*\n"
           f"Adquira o *VIP 30 DIAS* chamando {escape_md(CREDITOS)}\n\n"
           f"📊 *ESTOQUE DISPONÍVEL:* \n")
    
    for s in ALL_SERVICES:
        try:
            qtd = db[s].count_documents({})
            txt += f" ├ /{s.capitalize()}: `{qtd}`\n"
        except: pass
    
    txt += f"\n👑 *By:* {escape_md(CREDITOS)}"
    bot.reply_to(message, txt, parse_mode='MarkdownV2')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def logic_gerar(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    cmd = message.text.split('@')[0].lower().replace("/", "")
    if cmd not in ALL_SERVICES: return

    try:
        # Sorteia 1 conta aleatória
        res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
        if not res:
            bot.reply_to(message, f"⚠️ Estoque de {cmd.upper()} em reposição!")
            return

        dados = res[0].get('dados', 'erro')
        user_name = escape_md(message.from_user.first_name)
        user_id = message.from_user.id

        # Mensagem de Boas-vindas e Propaganda VIP
        anuncio = (f"👋 *Olá {user_name}\! ID:* `{user_id}`\n"
                   f"👑 Adquira seu *VIP 30 DIAS* com {escape_md(CREDITOS)} agora\!")

        # Botões Universais
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🗑️ APAGAR CONTA", callback_data=f"del_{user_id}"),
               types.InlineKeyboardButton("🛒 COMPRAR VIP", url=VENDAS_LINK))

        # --- LÓGICA DE ENTREGA POR FORMATO ---

        # 1. IPTV (Formatação em Bloco de Código - Click to Copy)
        if cmd == 'iptv':
            txt_final = (f"✅ *IPTV GERADA COM SUCESSO\!*\n\n"
                         f"```\n{dados}\n```\n"
                         f"🚀 *Créditos:* {escape_md(CREDITOS)}")
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            bot.send_message(message.chat.id, txt_final, parse_mode='MarkdownV2', reply_markup=kb)

        # 2. NETFLIX (Link NFT Token)
        elif cmd == 'netflix':
            txt_final = (f"✅ *NETFLIX GERADA\!*\n\n"
                         f"🔗 *TOKEN:* [CLIQUE AQUI PARA ACESSAR]({dados})\n\n"
                         f"🚀 *By:* {escape_md(CREDITOS)}")
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            bot.send_message(message.chat.id, txt_final, parse_mode='MarkdownV2', reply_markup=kb)

        # 3. FILES (Prime, Youtube, Canva - Envia como .txt)
        elif cmd in FILES_SERVICES:
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            arquivo = criar_txt_memoria(cmd, dados)
            bot.send_document(message.chat.id, arquivo, caption=f"✅ {cmd.upper()} enviada em arquivo \.txt\n\n🚀 *By:* {CREDITOS}", parse_mode='MarkdownV2', reply_markup=kb)

        # 4. STREAMING PADRÃO (Email:Pass)
        else:
            bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
            if ":" in dados:
                u, s = dados.split(":", 1)
                final = f"✅ *{cmd.upper()} GERADA\!*\n\n✉️ *E\-mail:* `{escape_md(u)}`\n🔑 *Senha:* `{escape_md(s)}`"
            else:
                final = f"✅ *{cmd.upper()} GERADA\!*\n\n`{escape_md(dados)}`"
            
            bot.send_message(message.chat.id, final + f"\n\n🚀 *By:* {escape_md(CREDITOS)}", parse_mode='MarkdownV2', reply_markup=kb)

        # Deleta o comando do usuário no grupo
        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass

    except Exception as e:
        print(f"Erro no Gerador: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_del(call):
    # Dono ou quem gerou podem apagar
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

# --- GESTÃO THOMAS (PRIVADO) ---

@bot.message_handler(content_types=['document'])
def abastecer_estoque(message):
    if message.from_user.id != OWNER_ID: return
    serv = message.caption.lower() if message.caption else ""
    if serv in ALL_SERVICES:
        content = bot.download_file(bot.get_file(message.document.file_id).file_path).decode('utf-8')
        
        # Se for IPTV, ele separa pelo traço que você usa no seu arquivo
        if serv == 'iptv':
            hits = content.split('--------------------------------------------------')
            docs = [{"dados": h.strip()} for h in hits if len(h.strip()) > 10]
        else:
            # Para o resto, cada linha é uma conta
            docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
            
        if docs:
            db[serv].insert_many(docs)
            bot.reply_to(message, f"🚀 Thomas, adicionei {len(docs)} itens em {serv}!")
    else:
        bot.reply_to(message, "❌ Legenda inválida! Use o nome do serviço.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def clear_db(message):
    if message.from_user.id != OWNER_ID: return
    s = message.text.lower().replace("/limpa_", "")
    if s in ALL_SERVICES:
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ Banco `{s.upper()}` limpo com sucesso!")

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "SISTEMA THOMAS ONLINE", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    print("🚀 Botricks V4.0 - Versão Suprema Thomas Ativada!")
    bot.infinity_polling(skip_pending=True)
