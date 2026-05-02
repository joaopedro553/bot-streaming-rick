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
# NOVO TOKEN ATUALIZADO
TOKEN = "8479454342:AAEaNuwOS9WJnTrDb_LmSvWHAw0AbFRB7iU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

# GRUPOS AUTORIZADOS
ALLOWED_GROUPS = [-1003429027149, -1003961419582, -1003802687191]
OWNER_ID = 1031830691 # Thomas
LINK_GRUPO_GRATIS = "https://t.me/ThomasAccount01"
CREDITOS = "@ThomasObscuro"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']

# --- CATEGORIAS AO EXTREMO ---
CATEGORIAS = {
    "🎬 FILMES E SÉRIES": ['netflix', 'disney', 'max', 'prime', 'paramount', 'apple', 'star', 'hulu', 'vix', 'peacock'],
    "🍪 COOKIES": ['netflix_cookies', 'prime_cookies'],
    "📺 TV E CANAIS": ['globoplay', 'clarotv', 'vivoplay', 'telecine', 'directv', 'plex'],
    "⚽ ESPORTES": ['premiere', 'espn', 'dazn'],
    "🛠️ FERRAMENTAS": ['duolingo', 'canva', 'scribd', 'youtube'],
    "📡 LISTAS": ['iptv', 'p2p']
}
SERVICOS_FLAT = [item for sublist in CATEGORIAS.values() for item in sublist]

# --- FUNÇÕES INTELIGENTES ---

def escape_md(text):
    """Protege o texto contra erros de formatação do Telegram"""
    for char in [r'.', r'-', r'!', r'(', r')', r'{', r'}', r'[', r']', r'#', r'+', r'_']:
        text = str(text).replace(char, f"\\{char}")
    return text

def formatar_entrega(servico, dados):
    """Analisa o conteúdo e formata de acordo com o tipo de conta"""
    servico_title = servico.upper().replace("_", " ")
    
    # Se for Bloco de Texto (Claro TV, Cookies ou Listas Longas)
    if "║" in dados or dados.startswith("[") or dados.startswith("{") or "\n" in dados:
        return (f"✅ *{servico_title} GERADA\!*\n\n"
                f"```\n{dados}\n```\n\n"
                f"🚀 *Créditos:* {CREDITOS}")
    
    # Se for formato padrão email:senha
    if ":" in dados:
        email, senha = dados.split(":", 1)
        return (f"✅ *{servico_title} GERADA\!*\n\n"
                f"✉️ *E\-mail:* `{email}`\n"
                f"🔑 *Senha:* `{senha}`\n\n"
                f"🚀 *Créditos:* {CREDITOS}")
    
    # Se for apenas um link ou código
    return f"✅ *{servico_title} GERADA\!*\n\n`{dados}`\n\n🚀 *Créditos:* {CREDITOS}"

# --- FILTROS DE PRIVADO ---

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID)
def restringir_acesso(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⭐ ENTRAR NO GRUPO", url=LINK_GRUPO_GRATIS))
    bot.reply_to(message, "❌ *Acesso Restrito\!*\n\nEu respondo apenas ao meu dono no privado\. Para gerar contas, entre no nosso grupo oficial abaixo:", parse_mode='Markdown', reply_markup=kb)

# --- COMANDOS ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, "👑 *Thomas, o sistema está pronto\!*\n\nUse /bot para ver o estoque ou mande o arquivo \.txt para abastecer\.")
    elif message.chat.id in ALLOWED_GROUPS:
        bot.reply_to(message, "🚀 *Botricks V2 Online\!*\nUse /bot para ver o estoque disponível\.")

@bot.message_handler(commands=['bot'])
def menu_completo(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
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

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def gerador_automatico(message):
    if message.chat.id not in ALLOWED_GROUPS and message.from_user.id != OWNER_ID: return
    
    # Limpa comando: /Netflix@bot -> netflix
    raw_cmd = message.text.split('@')[0].lower().replace("/", "")
    if raw_cmd not in SERVICOS_FLAT: return

    try:
        # Sorteio aleatório (Sample size 1)
        res = list(db[raw_cmd].aggregate([{"$sample": {"size": 1}}]))
        if res:
            dados_conta = res[0].get('dados', 'erro:erro')
            msg_final = formatar_entrega(raw_cmd, dados_conta)
            
            kb = types.InlineKeyboardMarkup()
            kb.row(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
                   types.InlineKeyboardButton("🛒 COMPRAR", url="https://t.me/ThomasObscuro"))
            
            bot.send_message(message.chat.id, msg_final, parse_mode='Markdown', reply_markup=kb)
            
            # Limpa o chat
            if message.chat.type != 'private':
                try: bot.delete_message(message.chat.id, message.message_id)
                except: pass
        else:
            bot.reply_to(message, f"⚠️ Estoque de {raw_cmd.upper()} vazio\!")
    except Exception as e:
        print(f"Erro: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def deletar_msg(call):
    # Dono ou criador da conta podem apagar
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

# --- ABASTECER E LIMPAR (SÓ DONO) ---

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
        bot.reply_to(message, "❌ Legenda inválida\! Use o nome de um serviço (ex: netflix\_cookies)\.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def zerar_banco(message):
    if message.from_user.id != OWNER_ID: return
    s = message.text.lower().replace("/limpa_", "")
    if s in SERVICOS_FLAT:
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ Thomas, estoque de {s.upper()} zerado\!")

# --- SERVER PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.remove_webhook()
    print("🚀 Bot Thomas V2 - Sistema Definitivo Online!")
    bot.infinity_polling(skip_pending=True)
