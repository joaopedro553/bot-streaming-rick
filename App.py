import telebot
import os
import threading
import time
from flask import Flask
from pymongo import MongoClient
from telebot import types

# --- CONFIGURAÇÕES ---
# TOKEN NOVO ATUALIZADO
TOKEN = "8479454342:AAEQC1Ar2R-zwdD6tWb1fIzDqUlIP3q7RfU"
MONGO_URI = "mongodb+srv://Botuser:BotRick2025@cluster0.uk43shk.mongodb.net/?appName=Cluster0"

# IDs DOS GRUPOS AUTORIZADOS
ALLOWED_GROUPS = [-1003429027149, -1003961419582]
OWNER_ID = 1031830691 # Seu ID: Thomas
VENDAS_URL = "https://t.me/RickSpaces"

# Inicialização
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['streaming_db']
SERVICOS = ['netflix', 'disney', 'max', 'prime', 'crunchyroll', 'apple', 'globoplay', 'clarotv']

# --- FILTROS DE SEGURANÇA ---
def is_allowed(message):
    # Permite se for um dos grupos autorizados
    if message.chat.id in ALLOWED_GROUPS:
        return True
    # Permite se for o DONO no privado
    if message.from_user.id == OWNER_ID and message.chat.type == 'private':
        return True
    return False

# --- COMANDOS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.from_user.id == OWNER_ID and message.chat.type == 'private':
        bot.reply_to(message, "👑 Olá Thomas! Sistema ativado no privado para você.\nUse /bot para ver o estoque ou envie um arquivo .txt para abastecer.")
    elif message.chat.id in ALLOWED_GROUPS:
        bot.reply_to(message, "🚀 Olá! Use /bot no grupo para ver o estoque disponível.")

@bot.message_handler(commands=['bot'])
def send_intro(message):
    if not is_allowed(message): return
    
    estoque = ""
    for s in SERVICOS:
        try:
            qtd = db[s].count_documents({})
            estoque += f"▪️ /{s.capitalize()}: {qtd}\n"
        except: estoque += f"▪️ /{s.capitalize()}: 0\n"
    
    bot.reply_to(message, f"👋 *Botricks Online*\n\n📊 *ESTOQUE ATUAL:* \n{estoque}\n\n💡 _Sorteio aleatório ativado (Estoque Infinito)_", parse_mode='Markdown')

@bot.message_handler(commands=SERVICOS + [s.capitalize() for s in SERVICOS])
def handle_gerar(message):
    if not is_allowed(message): return
    
    servico = message.text.replace("/", "").lower()
    # Sorteia 1 conta sem apagar do banco
    res = list(db[servico].aggregate([{"$sample": {"size": 1}}]))
    
    if res:
        dados = res[0].get('dados', 'erro:erro')
        # Separa email e senha se houver dois pontos
        if ":" in dados:
            email, senha = dados.split(":", 1)
            msg_final = f"✅ *{servico.upper()} GERADA*\n\n✉️ E-mail: `{email}`\n🔑 Senha: `{senha}`"
        else:
            msg_final = f"✅ *{servico.upper()} GERADA*\n\n`{dados}`"

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑️ APAGAR", callback_data=f"del_{message.from_user.id}"),
               types.InlineKeyboardButton("🛒 COMPRAR", url=VENDAS_URL))
        
        bot.send_message(message.chat.id, msg_final, parse_mode='Markdown', reply_markup=kb)
        
        # Apaga o comando do usuário apenas se for no grupo
        if message.chat.type != 'private':
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
    else:
        bot.reply_to(message, f"⚠️ {servico} sem estoque no momento!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def handle_delete(call):
    owner_id = int(call.data.split('_')[1])
    # Só apaga se for quem pediu ou se for o Thomas
    if call.from_user.id == owner_id or call.from_user.id == OWNER_ID:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

# --- GESTÃO DE ABASTECIMENTO (SÓ DONO NO PRIVADO) ---

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
            bot.reply_to(message, f"🚀 Sucesso! {len(docs)} contas subidas para {servico}!")
    else:
        bot.reply_to(message, "❌ Erro! Envie o arquivo e escreva o nome do serviço na legenda (ex: netflix).")

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
def home(): return "BOT RICK ONLINE", 200

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.remove_webhook()
    print("🚀 Bot Iniciado! (Grupos autorizados + Privado do Dono)")
    bot.infinity_polling(skip_pending=True)
