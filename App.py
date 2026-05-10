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

# GRUPOS AUTORIZADOS (Incluindo o novo -1003961419582)
ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
OWNER_ID = 1031830691 
LINK_GRUPO_GRATIS = "https://t.me/ThomasAccount01"
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']

# --- DEFINIÇÃO DE SERVIÇOS ---
STREAMING = ['crunchyroll', 'disney', 'max', 'paramount', 'apple', 'globoplay', 'clarotv', 'vivoplay', 'plex', 'viki', 'vix', 'dazn', 'duolingo']
# Serviços que geram arquivo .txt
FILES_SERVICES = ['prime', 'youtube', 'canva']
# Serviços que são links ou blocos
SPECIAL_SERVICES = ['netflix', 'iptv']

ALL_SERVICES = STREAMING + FILES_SERVICES + SPECIAL_SERVICES

# --- FUNÇÕES ---

def escape_md(text):
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_']:
        text = str(text).replace(char, f"\\{char}")
    return text

def criar_txt_virtual(servico, conteudo):
    """Gera um arquivo .txt em memória para envio"""
    buf = io.BytesIO(conteudo.encode('utf-8'))
    buf.name = f"{servico.upper()}_CONTA.txt"
    return buf

# --- FILTROS DE PRIVADO ---

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def restringir_acesso(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⭐ ENTRAR NO GRUPO", url=LINK_GRUPO_GRATIS))
    msg = (f"👋 Olá {message.from_user.first_name}\! ID: `{message.from_user.id}`\n\n"
           f"❌ *Acesso Negado\!*\n\nEu respondo apenas no grupo oficial\. "
           f"Se quiser comprar o *VIP 30 DIAS* e ter acesso total, chame o {escape_md(CREDITOS)}")
    bot.reply_to(message, msg, parse_mode='MarkdownV2', reply_markup=kb)

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def menu_completo(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    txt = (f"👋 *Olá {message.from_user.first_name}\! ID:* `{message.from_user.id}`\n\n"
           f"💎 *ACESSO VIP 30 DIAS:* Chama {escape_md(CREDITOS)}\n\n"
           f"📊 *ESTOQUE ATUAL:* \n")
    
    for s in ALL_SERVICES:
        qtd = db[s].count_documents({})
        txt += f"🔹 /{s.capitalize()}: `{qtd}`\n"
    
    bot.reply_to(message, txt, parse_mode='MarkdownV2')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def gerador_automatico(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    raw_cmd = message.text.split('@')[0].lower().replace("/", "")
    if raw_cmd not in ALL_SERVICES: return

    try:
        res = list(db[raw_cmd].aggregate([{"$sample": {"size": 1}}]))
        if res:
            dados = res[0].get('dados', 'erro')
            user_name = message.from_user.first_name
            user_id = message.from_user.id

            # Mensagem de Saudação e Propaganda
            anuncio = (f"👋 *Olá {escape_md(user_name)}\! ID:* `{user_id}`\n"
                       f"👑 Adquira seu *VIP 30 DIAS* com {escape_md(CREDITOS)} agora\!")

            kb = types.InlineKeyboardMarkup()
            kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{user_id}"),
                   types.InlineKeyboardButton("🛒 COMPRAR", url="https://t.me/ThomasObscuro"))

            # --- LÓGICA DE ENVIO PERSONALIZADA ---

            # 1. IPTV (Bloco de Código para não cortar link)
            if raw_cmd == 'iptv':
                bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
                bot.send_message(message.chat.id, f"✅ *IPTV GERADA*\n\n```\n{dados}\n```", parse_mode='MarkdownV2', reply_markup=kb)

            # 2. NETFLIX (Link Direto nftoken)
            elif raw_cmd == 'netflix':
                bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
                bot.send_message(message.chat.id, f"✅ *NETFLIX GERADA*\n\n🔗 [CLIQUE AQUI PARA USAR O TOKEN]({dados})", parse_mode='MarkdownV2', reply_markup=kb)

            # 3. PRIME, YOUTUBE, CANVA (Arquivo .txt)
            elif raw_cmd in FILES_SERVICES:
                bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
                arquivo = criar_txt_virtual(raw_cmd, dados)
                bot.send_document(message.chat.id, arquivo, caption=f"✅ {raw_cmd.upper()} enviada em arquivo \.txt", reply_markup=kb, parse_mode='MarkdownV2')

            # 4. OUTROS (Email:Senha)
            else:
                bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
                if ":" in dados:
                    u, s = dados.split(":", 1)
                    txt_final = f"✅ *{raw_cmd.upper()} GERADA*\n\n✉️ E\-mail: `{u}`\n🔑 Senha: `{s}`"
                else:
                    txt_final = f"✅ *{raw_cmd.upper()} GERADA*\n\n`{dados}`"
                
                bot.send_message(message.chat.id, txt_final, parse_mode='MarkdownV2', reply_markup=kb)

            # Deleta o comando
            if message.chat.type != 'private':
                try: bot.delete_message(message.chat.id, message.message_id)
                except: pass
        else:
            bot.reply_to(message, f"⚠️ Estoque de {raw_cmd.upper()} vazio!")
    except Exception as e:
        print(f"Erro: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def deletar_msg(call):
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

# --- GESTÃO (SÓ THOMAS) ---

@bot.message_handler(content_types=['document'])
def cadastrar_txt(message):
    if message.from_user.id != OWNER_ID: return
    servico = message.caption.lower() if message.caption else ""
    if servico in ALL_SERVICES:
        content = bot.download_file(bot.get_file(message.document.file_id).file_path).decode('utf-8')
        
        # Lógica especial para IPTV (pode ter várias linhas por hit)
        if servico == 'iptv':
            # Separa por blocos que contenham o separador horizontal
            hits = content.split('--------------------------------------------------')
            docs = [{"dados": h.strip()} for h in hits if len(h.strip()) > 10]
        else:
            # Padrão: 1 linha = 1 conta
            docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
            
        if docs:
            db[servico].insert_many(docs)
            bot.reply_to(message, f"🚀 Thomas, {len(docs)} itens adicionados em {servico}!")
    else:
        bot.reply_to(message, "❌ Legenda inválida!")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def zerar_banco(message):
    if message.from_user.id != OWNER_ID: return
    s = message.text.lower().replace("/limpa_", "")
    if s in ALL_SERVICES:
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ Estoque de {s.upper()} zerado!")

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    print("🚀 Thomas Checker V4 - SUPREMO!")
    bot.infinity_polling(skip_pending=True)
