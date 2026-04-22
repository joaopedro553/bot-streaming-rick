import telebot
import os
import threading
import time
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
TOKEN = "8479454342:AAH8qyPoDFyTEfzaUQGP3wsEjnbB3Z_aI2s"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"
ALLOWED_GROUP_ID = -1003429027149 

bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

@bot.message_handler(commands=['bot'])
def send_intro(message):
    if message.chat.id != ALLOWED_GROUP_ID: return
    estoque = ""
    for s in SERVICOS:
        qtd = db[s].count_documents({})
        estoque += f"▪️ /{s.capitalize()}: {qtd}\n"
    bot.reply_to(message, f"👋 *Botricks Online*\n\n📊 *ESTOQUE:* \n{estoque}", parse_mode='Markdown')

@bot.message_handler(commands=SERVICOS + [s.capitalize() for s in SERVICOS])
def handle_gerar(message):
    if message.chat.id != ALLOWED_GROUP_ID: return
    servico = message.text.replace("/", "").lower()
    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    if res:
        dados = res[0].get('dados', 'erro:erro')
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🛒 COMPRAR", url="https://t.me/RickSpaces"))
        bot.send_message(message.chat.id, f"✅ *{servico.upper()} GERADA*\n\n`{dados}`", parse_mode='Markdown', reply_markup=kb)
    else:
        bot.reply_to(message, f"⚠️ {servico} vazio!")

# --- SERVER PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    # Inicia o Flask
    threading.Thread(target=run_flask).start()
    
    # Limpeza e início
    print("🚀 Limpando e iniciando...")
    bot.remove_webhook()
    time.sleep(2)
    
    # Polling com skip_pending=True limpa as mensagens acumuladas
    bot.infinity_polling(skip_pending=True)
