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

def extract_nftoken(texto_bruto):
    """Extrai o token ct e formata para o link oficial da Netflix"""
    try:
        decodificado = urllib.parse.unquote(texto_bruto.strip())
        if "ct=" in decodificado:
            token = decodificado.split("ct=")[1].split("&")[0].split()[0].split(";")[0]
        elif "NetflixId=" in decodificado:
            token = decodificado.split("NetflixId=")[1].split()[0].split(";")[0]
        else:
            token = texto_bruto.strip()
        
        token = token.replace('-', '+').replace('_', '/')
        while len(token) % 4 != 0: token += '='
        return f"https://netflix.com/?nftoken={token}"
    except:
        return None

def check_netflix_live(texto_bruto):
    """Verifica se o cookie da Netflix ainda está funcionando"""
    url_teste = "https://www.netflix.com/browse"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        # Tenta extrair o NetflixId para o teste
        nid = ""
        if "NetflixId=" in texto_bruto:
            nid = texto_bruto.split("NetflixId=")[1].split()[0].split(";")[0]
        else:
            return False # Sem ID não dá pra checar
            
        res = requests.get(url_teste, cookies={"NetflixId": nid}, headers=headers, timeout=8, allow_redirects=False)
        # Se retornar 200 ou 302 para /browse, está VIVA
        if res.status_code == 200 or (res.status_code == 302 and "/browse" in res.headers.get('Location', '')):
            return True
        return False
    except:
        return False

def escape_md(text):
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_', r'=']:
        text = str(text).replace(char, f"\\{char}")
    return text

def criar_txt_memoria(servico, conteudo):
    buf = io.BytesIO(conteudo.encode('utf-8'))
    buf.name = f"{servico.upper()}_CONTA.txt"
    return buf

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def send_menu(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    txt = (f"👋 *Olá {message.from_user.first_name}\! ID:* `{message.from_user.id}`\n\n"
           f"💎 *VIP 30 DIAS:* Chama {escape_md(CREDITOS)}\n\n"
           f"📊 *ESTOQUE:* \n")
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

    # Mensagem de espera para o Checker
    msg_wait = bot.reply_to(message, "⏳ *Consultando estoque e verificando validade...*", parse_mode='Markdown')

    try:
        user_name = escape_md(message.from_user.first_name)
        anuncio = f"👋 *Olá {user_name}\! ID:* `{message.from_user.id}`\n👑 VIP 30 DIAS com {escape_md(CREDITOS)}"
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
               types.InlineKeyboardButton("🛒 COMPRAR VIP", url="https://t.me/ThomasObscuro"))

        # --- LÓGICA ESPECIAL NETFLIX (CHECKER + TOKEN) ---
        if cmd == 'netflix':
            # Tenta achar uma conta viva no banco (tentativas limitadas para não travar)
            found = False
            for _ in range(5):
                res = list(db['netflix'].aggregate([{"$sample": {"size": 1}}]))
                if not res: break
                
                bruto = res[0].get('dados', '')
                if check_netflix_live(bruto):
                    link = extract_nftoken(bruto)
                    if link:
                        bot.delete_message(message.chat.id, msg_wait.message_id)
                        bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
                        bot.send_message(message.chat.id, f"✅ *NETFLIX VIVA ENCONTRADA\!*\n\n🔗 [CLIQUE AQUI PARA LOGAR]({link})\n\n🚀 *By:* {escape_md(CREDITOS)}", parse_mode='MarkdownV2', reply_markup=kb)
                        found = True
                        break
            
            if not found:
                bot.edit_message_text("⚠️ *No momento não encontrei cookies válidos no estoque. Tente novamente em instantes!*", message.chat.id, msg_wait.message_id, parse_mode='Markdown')

        # --- LÓGICA IPTV ---
        elif cmd == 'iptv':
            res = list(db['iptv'].aggregate([{"$sample": {"size": 1}}]))
            if res:
                bot.delete_message(message.chat.id, msg_wait.message_id)
                bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
                bot.send_message(message.chat.id, f"✅ *IPTV GERADA*\n\n```\n{res[0]['dados']}\n```", parse_mode='MarkdownV2', reply_markup=kb)
            else: bot.edit_message_text("⚠️ Estoque vazio!", message.chat.id, msg_wait.message_id)

        # --- LÓGICA FILES (.TXT) ---
        elif cmd in FILES_SERVICES:
            res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
            if res:
                bot.delete_message(message.chat.id, msg_wait.message_id)
                bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
                arquivo = criar_txt_memoria(cmd, res[0]['dados'])
                bot.send_document(message.chat.id, arquivo, caption=f"✅ {cmd.upper()} em .txt", reply_markup=kb)

        # --- LÓGICA PADRÃO ---
        else:
            res = list(db[cmd].aggregate([{"$sample": {"size": 1}}]))
            if res:
                bot.delete_message(message.chat.id, msg_wait.message_id)
                bot.send_message(message.chat.id, anuncio, parse_mode='MarkdownV2')
                dados = res[0]['dados']
                final_txt = f"✅ *{cmd.upper()} GERADA*\n\n`{escape_md(dados)}`"
                if ":" in dados:
                    u, s = dados.split(":", 1)
                    final_txt = f"✅ *{cmd.upper()} GERADA*\n\n✉️ E-mail: `{escape_md(u)}`\n🔑 Senha: `{escape_md(s)}`"
                bot.send_message(message.chat.id, final_txt, parse_mode='MarkdownV2', reply_markup=kb)

        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass

    except:
        bot.edit_message_text("❌ Erro ao processar. Tente novamente.", message.chat.id, msg_wait.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_del(call):
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

# --- GESTÃO THOMAS (Upload/Limpa) ---
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

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("/limpa_"))
def clear_category(message):
    if message.from_user.id != OWNER_ID: return
    try:
        s_limpar = message.text.lower().split("_")[1]
        db[s_limpar].delete_many({})
        bot.reply_to(message, f"🗑️ Thomas, estoque de {s_limpar.upper()} limpo!")
    except: pass

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
