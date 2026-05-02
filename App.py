import telebot
import os
import threading
import time
import re
from datetime import datetime
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
TOKEN = "8479454342:AAEaNuwOS9WJnTrDb_LmSvWHAw0AbFRB7iU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
OWNER_ID = 1031830691 
LINK_GRUPO_GRATIS = "https://t.me/ThomasAccount01"
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']

CATEGORIAS = {
    "🎬 FILMES E SÉRIES": ['netflix', 'disney', 'max', 'prime', 'paramount', 'apple', 'star', 'hulu', 'vix', 'peacock'],
    "🍪 COOKIES": ['netflix_cookies', 'prime_cookies'],
    "📺 TV E CANAIS": ['globoplay', 'clarotv', 'vivoplay', 'telecine', 'directv', 'plex'],
    "⚽ ESPORTES": ['premiere', 'espn', 'dazn'],
    "🛠️ FERRAMENTAS": ['duolingo', 'canva', 'scribd', 'youtube'],
    "📡 LISTAS": ['iptv', 'p2p']
}
SERVICOS_FLAT = [item for sublist in CATEGORIAS.values() for item in sublist]

# --- FUNÇÕES ---

def escape_md(text):
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_']:
        text = str(text).replace(char, f"\\{char}")
    return text

def formatar_entrega(servico, dados):
    servico_title = servico.upper().replace("_", " ")
    if "║" in dados or dados.startswith("[") or dados.startswith("{") or "\n" in dados:
        return f"✅ *{servico_title} GERADA\!*\n\n```\n{dados}\n```\n\n🚀 *Créditos:* {CREDITOS}"
    if ":" in dados:
        email, senha = dados.split(":", 1)
        return f"✅ *{servico_title} GERADA\!*\n\n✉️ *E\-mail:* `{email}`\n🔑 *Senha:* `{senha}`\n\n🚀 *Créditos:* {CREDITOS}"
    return f"✅ *{servico_title} GERADA\!*\n\n`{dados}`\n\n🚀 *Créditos:* {CREDITOS}"

# --- HANDLERS (ORDEM DE IMPORTÂNCIA) ---

# 1. Trava para estranhos no privado
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def restringir_acesso(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⭐ ENTRAR NO GRUPO", url=LINK_GRUPO_GRATIS))
    bot.reply_to(message, "❌ *Acesso Restrito\!*\n\nEu respondo apenas ao meu dono no privado\. Entre no grupo oficial:", parse_mode='Markdown', reply_markup=kb)

# 2. Comando Start
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, "👑 *Thomas, o sistema está pronto\!*")
    else:
        bot.reply_to(message, "🚀 *Botricks Online\!* Use /bot para ver o estoque\.")

# 3. Comandos de Limpeza (Exclusivo Dono)
@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def zerar_banco(message):
    if message.from_user.id != OWNER_ID: return
    s = message.text.lower().replace("/limpa_", "")
    if s in SERVICOS_FLAT:
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ Thomas, estoque de {s.upper()} zerado\!")

# 4. Receber Arquivos (Abastecer)
@bot.message_handler(content_types=['document'])
def cadastrar_txt(message):
    if message.from_user.id != OWNER_ID: return
    servico = message.caption.lower() if message.caption else ""
    if servico in SERVICOS_FLAT:
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8')
        docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
        if docs:
            db[servico].insert_many(docs)
            bot.reply_to(message, f"🚀 Thomas, {len(docs)} itens adicionados em {servico}\!")
    else:
        bot.reply_to(message, "❌ Legenda inválida\! Use o nome de um serviço\.")

# 5. Comando do Menu /bot
@bot.message_handler(commands=['bot'])
def menu_completo(message):
    txt = f"🛡️ *SISTEMA THOMAS CHECKER ATIVO*\n👤 *Thomas:* {CREDITOS}\n\n"
    for cat, lista in CATEGORIAS.items():
        txt += f"*{cat}*\n"
        for s in lista:
            try:
                qtd = db[s].count_documents({})
                txt += f"🔹 /{s.capitalize()}: `{qtd}`\n"
            except: txt += f"🔹 /{s.capitalize()}: `0`\n"
        txt += "\n"
    bot.reply_to(message, txt, parse_mode='Markdown')

# 6. Gerador Geral (Qualquer comando /)
@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def gerador_automatico(message):
    # Limpa comando: /Netflix@bot -> netflix
    raw_cmd = message.text.split('@')[0].lower().replace("/", "")
    if raw_cmd not in SERVICOS_FLAT: return

    try:
        res = list(db[raw_cmd].aggregate([{"$sample": {"size": 1}}]))
        if res:
            dados_conta = res[0].get('dados', 'erro:erro')
            msg_final = formatar_entrega(raw_cmd, dados_conta)
            kb = types.InlineKeyboardMarkup()
            kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
                   types.InlineKeyboardButton("🛒 COMPRAR", url="https://t.me/ThomasObscuro"))
            bot.send_message(message.chat.id, msg_final, parse_mode='Markdown', reply_markup=kb)
            if message.chat.type != 'private':
                try: bot.delete_message(message.chat.id, message.message_id)
                except: pass
        else:
            bot.reply_to(message, f"⚠️ Estoque de {raw_cmd.upper()} vazio\!")
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def deletar_msg(call):
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
    print("🚀 Bot Thomas V2.2 - Correção de Prioridade Ativa!")
    bot.infinity_polling(skip_pending=True)
