import telebot
import os
import threading
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES DIRETAS ---
# Coloquei os dados direto aqui para não ter erro de leitura na Render
TOKEN = "8479454342:AAFq34sWRk16JgmOIUWDq7ZVY7hLpfPLMjo"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"
ALLOWED_GROUP_ID = -1003429027149 
OWNER_ID = 1031830691
VENDAS_URL = "https://t.me/RickSpaces"

bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

@bot.message_handler(commands=['bot'])
def send_intro(message):
    if message.chat.id != ALLOWED_GROUP_ID: return
    estoque = ""
    for s in SERVICOS:
        try:
            qtd = db[s].count_documents({})
            estoque += f"▪️ /{s.capitalize()}: {qtd}\n"
        except: estoque += f"▪️ /{s.capitalize()}: 0\n"
    bot.reply_to(message, f"👋 *Botricks Online*\n\n📊 *ESTOQUE:* \n{estoque}", parse_mode='Markdown')

@bot.message_handler(commands=SERVICOS + [s.capitalize() for s in SERVICOS])
def handle_gerar(message):
    if message.chat.id != ALLOWED_GROUP_ID: return
    servico = message.text.replace("/", "").lower()
    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    if res:
        dados = res[0].get('dados', 'erro:erro')
        email, senha = dados.split(':', 1) if ":" in dados else (dados, "---")
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
               types.InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_URL))
        bot.send_message(message.chat.id, f"✅ *{servico.upper()}*\n\n✉️ E-mail: `{email}`\n🔑 Senha: `{senha}`", parse_mode='Markdown', reply_markup=kb)
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
    else:
        bot.reply_to(message, f"⚠️ {servico} vazio!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete(call):
    if call.from_user.id == int(call.data.split('_')[1]) or call.from_user.id == OWNER_ID:
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- SERVER PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def home(): return "BOT RICK ONLINE", 200

def run_flask():
    # A Render exige que o bot escute na porta 10000
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("🚀 Bot Iniciado com Sucesso!")
    bot.infinity_polling(skip_pending=True)
