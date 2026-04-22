import telebot
import os
import threading
import time
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
# Pega das variáveis de ambiente da Render (Environment)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")

ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691
VENDAS_URL = "https://t.me/RickSpaces"

# Inicialização do Bot
bot = telebot.TeleBot(TOKEN)
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

# Conectar MongoDB
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    db = client['streaming_db']
    print("✅ BANCO DE DADOS CONECTADO!")
except Exception as e:
    print(f"⚠️ Erro no banco: {e}")

# --- COMANDOS ---

@bot.message_handler(commands=['bot'])
def send_intro(message):
    if message.chat.id != ALLOWED_GROUP_ID: return
    estoque = ""
    for s in SERVICOS:
        try:
            qtd = db[s].count_documents({})
            estoque += f"▪️ /{s.capitalize()}: {qtd}\n"
        except: estoque += f"▪️ /{s.capitalize()}: 0\n"
    
    txt = f"👋 *Botricks Online*\n\n📊 *ESTOQUE ATUAL:* \n{estoque}\n\n💡 _Sorteio aleatório ativado!_"
    bot.reply_to(message, txt, parse_mode='Markdown')

@bot.message_handler(commands=SERVICOS + [s.capitalize() for s in SERVICOS])
def handle_gerar(message):
    if message.chat.id != ALLOWED_GROUP_ID: return
    servico = message.text.replace("/", "").lower()
    
    try:
        # Sorteia 1 conta (Estoque Infinito)
        res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
        if res:
            dados = res[0].get('dados', 'erro:erro')
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_URL))
            
            bot.send_message(message.chat.id, f"✅ *{servico.upper()} GERADA*\n\n`{dados}`", parse_mode='Markdown', reply_markup=kb)
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
        else:
            bot.reply_to(message, f"⚠️ {servico} sem estoque!")
    except:
        bot.reply_to(message, "❌ Erro ao acessar o banco.")

# --- SERVER PARA RENDER (PORTA 10000) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "BOT IS LIVE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    # 1. Inicia o Flask para a Render não dar erro de porta
    threading.Thread(target=run_flask, daemon=True).start()
    print("🚀 Servidor Web iniciado...")

    # 2. Limpeza profunda de Webhook (Corrige o erro 409)
    print("🧹 Removendo Webhooks antigos...")
    bot.remove_webhook()
    time.sleep(1) # Pequena pausa para o Telegram processar

    # 3. Liga o Bot no modo Polling
    print("🤖 Bot Thomas Checker Online e pronto!")
    # skip_pending=True ignora mensagens enviadas enquanto o bot estava dando erro
    bot.infinity_polling(skip_pending=True)
