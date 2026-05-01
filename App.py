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
TOKEN = "8479454342:AAH8qyPoDFyTEfzaUQGP3wsEjnbB3Z_aI2s"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

# GRUPOS AUTORIZADOS
ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
OWNER_ID = 1031830691 
LINK_GRUPO_GRATIS = "https://t.me/ThomasAccount01"
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']

# --- CATEGORIAS ---
# Incluindo Cookies e as que você pediu
CATEGORIAS = {
    "🎬 FILMES E SÉRIES": ['netflix', 'disney', 'max', 'prime', 'paramount', 'apple', 'star', 'hulu', 'vix', 'peacock'],
    "🍪 COOKIES (Navegador)": ['netflix_cookies', 'prime_cookies'],
    "📺 TV E CANAIS": ['globoplay', 'clarotv', 'vivoplay', 'telecine', 'directv', 'plex'],
    "⚽ ESPORTES": ['premiere', 'espn', 'dazn'],
    "🛠️ FERRAMENTAS": ['duolingo', 'canva', 'scribd', 'youtube'],
    "📡 LISTAS": ['iptv', 'p2p']
}
SERVICOS_FLAT = [item for sublist in CATEGORIAS.values() for item in sublist]

# --- FUNÇÕES INTELIGENTES ---

def formatar_entrega(servico, dados):
    """Identifica o formato e deixa clicável da melhor forma"""
    servico_upper = servico.upper().replace("_", " ")
    
    # Se for formato de Bloco (Claro TV exemplo ou JSON de Cookies)
    if "║" in dados or "╔" in dados or dados.startswith("[") or "\n" in dados:
        return (f"✅ *{servico_upper} GERADA\!*\n\n"
                f"```\n{dados}\n```\n\n"
                f"🚀 *Créditos:* {CREDITOS}")
    
    # Se for formato email:pass
    if ":" in dados:
        partes = dados.split(":", 1)
        return (f"✅ *{servico_upper} GERADA\!*\n\n"
                f"✉️ *E-mail:* `{partes[0]}`\n"
                f"🔑 *Senha:* `{partes[1]}`\n\n"
                f"🚀 *Créditos:* {CREDITOS}")
    
    # Formato desconhecido (envia como código simples)
    return f"✅ *{servico_upper} GERADA\!*\n\n`{dados}`\n\n🚀 *Créditos:* {CREDITOS}"

# --- FILTROS ---

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def restringir_privado(message):
    bot.reply_to(message, f"❌ *Acesso Negado\!*\n\nEu funciono apenas no meu Grupo VIP\. Gere suas contas clicando no link abaixo:\n\n👉 [Thomas Account 01]({LINK_GRUPO_GRATIS})", parse_mode='Markdown')

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def send_menu(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    txt = f"🛡️ *SISTEMA THOMAS CHECKER* \n👤 *Olá:* {message.from_user.first_name}\n\n"
    for cat, lista in CATEGORIAS.items():
        txt += f"*{cat}*\n"
        for s in lista:
            try:
                qtd = db[s].count_documents({})
                txt += f"🔹 /{s.capitalize()}: `{qtd}`\n"
            except: txt += f"🔹 /{s.capitalize()}: `0`\n"
        txt += "\n"
    
    txt += f"👑 *Dono:* {CREDITOS}\n🛒 *Vendas:* @ThomasObscuro"
    bot.reply_to(message, txt, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_gen(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    # Limpa o comando (tira o @bot)
    raw_cmd = message.text.split('@')[0].lower().replace("/", "")
    if raw_cmd not in SERVICOS_FLAT: return

    # Sorteio
    res = list(db[raw_cmd].aggregate([{"$sample": {"size": 1}}]))
    if res:
        dados_brutos = res[0].get('dados', 'erro:erro')
        msg_formatada = formatar_entrega(raw_cmd, dados_brutos)
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
               types.InlineKeyboardButton("🛒 COMPRAR", url="https://t.me/ThomasObscuro"))
        
        bot.send_message(message.chat.id, msg_formatada, parse_mode='Markdown', reply_markup=kb)
        
        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
    else:
        bot.reply_to(message, f"⚠️ Estoque de {raw_cmd.upper()} vazio!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete(call):
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

# --- GESTÃO (SÓ THOMAS NO PRIVADO) ---

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if message.from_user.id != OWNER_ID: return
    servico = message.caption.lower() if message.caption else ""
    if servico in SERVICOS_FLAT:
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8')
        
        # Se for Cookies ou Listas longas, podemos subir o bloco inteiro ou por linhas
        # Aqui, vamos subir por linhas para o sorteio funcionar
        docs = [{"dados": l.strip()} for l in content.splitlines() if len(l.strip()) > 5]
        if docs:
            db[servico].insert_many(docs)
            bot.reply_to(message, f"🚀 Sucesso! {len(docs)} itens adicionados em {servico}!")
    else:
        bot.reply_to(message, "❌ Legenda inválida! Use o nome do serviço (ex: netflix_cookies).")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def handle_limpa(message):
    if message.from_user.id != OWNER_ID: return
    s = message.text.lower().replace("/limpa_", "")
    if s in SERVICOS_FLAT:
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ Estoque de {s.upper()} zerado!")

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "THOMAS CHECKER V2 ONLINE", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    print("🚀 Botriks Ultra V2 Ativado!")
    bot.infinity_polling(skip_pending=True)
