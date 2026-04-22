import telebot
import os
import threading
import time
from flask import Flask
from pymongo import MongoClient
from telebot import types
from telebot.apihelper import ApiTelegramException

# --- CONFIGURAÇÕES ---
TOKEN = "8479454342:AAEQC1Ar2R-zwdD6tWb1fIzDqUlIP3q7RfU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

ALLOWED_GROUPS = [-1003429027149, -1003961419582]
OWNER_ID = 1031830691 
VENDAS_URL = "https://t.me/RickSpaces"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

# --- FILTROS ---
def is_allowed(message):
    if message.chat.id in ALLOWED_GROUPS:
        return True
    if message.from_user.id == OWNER_ID and message.chat.type == 'private':
        return True
    return False

# --- COMANDOS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.from_user.id == OWNER_ID and message.chat.type == 'private':
        bot.reply_to(message, "👑 Thomas, sistema liberado no seu privado!")
    elif message.chat.id in ALLOWED_GROUPS:
        bot.reply_to(message, "🚀 Use /bot para ver o estoque!")

@bot.message_handler(commands=['bot'])
def send_intro(message):
    if not is_allowed(message): return
    estoque = ""
    for s in SERVICOS:
        try:
            qtd = db[s].count_documents({})
            estoque += f"▪️ /{s.capitalize()}: {qtd}\n"
        except: estoque += f"▪️ /{s.capitalize()}: 0\n"
    bot.reply_to(message, f"👋 *Botricks Online*\n\n📊 *ESTOQUE:* \n{estoque}", parse_mode='Markdown')

@bot.message_handler(commands=SERVICOS + [s.capitalize() for s in SERVICOS])
def handle_gerar(message):
    if not is_allowed(message): return
    servico = message.text.replace("/", "").lower()
    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    if res:
        dados = res[0].get('dados', 'erro:erro')
        email, senha = dados.split(':', 1) if ":" in dados else (dados, "---")
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
               types.InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_URL))
        
        txt = f"✅ *{servico.upper()} GERADA*\n\n✉️ E-mail: `{email}`\n🔑 Senha: `{senha}`"
        bot.send_message(message.chat.id, txt, parse_mode='Markdown', reply_markup=kb)
        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
    else:
        bot.reply_to(message, f"⚠️ {servico} sem estoque!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete(call):
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if message.from_user.id != OWNER_ID: return
    servico = message.caption.lower() if message.caption else ""
    if servico in SERVICOS:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8')
        docs = [{"dados": l.strip()} for l in content.splitlines() if ":" in l]
        if docs:
            db[servico].insert_many(docs)
            bot.reply_to(message, f"🚀 Sucesso! {len(docs)} contas em {servico}!")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/Limpa_"))
def handle_limpa(message):
    if message.from_user.id != OWNER_ID: return
    s = message.text.lower().replace("/limpa_", "")
    if s in SERVICOS:
        db[s].delete_many({})
        bot.reply_to(message, f"🗑️ Estoque de {s.upper()} zerado!")

# --- SERVER PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    
    print("🚀 Iniciando Botricks...")
    
    while True:
        try:
            bot.remove_webhook()
            # Inicia o bot. Se der erro 409, ele cai no except abaixo.
            bot.infinity_polling(skip_pending=True, timeout=20)
        except ApiTelegramException as e:
            if e.error_code == 409:
                print("⚠️ Conflito de Token (outra instância ligada). Aguardando 10 segundos...")
                time.sleep(10)
            else:
                print(f"❌ Erro na API: {e}")
                time.sleep(5)
        except Exception as e:
            print(f"❌ Erro desconhecido: {e}")
            time.sleep(5)
