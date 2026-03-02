import re
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from openpyxl import Workbook

import os

TOKEN = os.environ.get("BOT_TOKEN")

# ================= DATABASE =================
conn = sqlite3.connect("finance.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    type TEXT,
    description TEXT,
    amount INTEGER
)
""")
conn.commit()

# ================= INPUT TRANSAKSI =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    match = re.search(r'^(\+|\-)\s+(.+)\s+([\d\.]+)$', text)

    if match:
        symbol = match.group(1)
        description = match.group(2)
        amount = int(match.group(3).replace(".", ""))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        trans_type = "INCOME" if symbol == "+" else "EXPENSE"

        cursor.execute(
            "INSERT INTO transactions (date, type, description, amount) VALUES (?, ?, ?, ?)",
            (now, trans_type, description, amount)
        )
        conn.commit()

        await update.message.reply_text(
            f"✅ {trans_type} dicatat\n📝 {description}\n💰 Rp {amount:,}"
        )

# ================= REKAP BULANAN =================
async def monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    month = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        SELECT type, amount FROM transactions
        WHERE strftime('%Y-%m', date) = ?
    """, (month,))

    rows = cursor.fetchall()

    total_income = 0
    total_expense = 0

    for r in rows:
        if r[0] == "INCOME":
            total_income += r[1]
        else:
            total_expense += r[1]

    balance = total_income - total_expense

    message = f"""
📅 REKAP BULAN {month}

💰 Total Income   : Rp {total_income:,}
💸 Total Expense  : Rp {total_expense:,}
📊 Saldo Bersih   : Rp {balance:,}
"""

    await update.message.reply_text(message)

# ================= EXPORT EXCEL =================
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT date, type, description, amount FROM transactions ORDER BY date ASC")
    rows = cursor.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Finance Report"

    ws.append(["Tanggal", "Tipe", "Keterangan", "Nominal"])

    for row in rows:
        ws.append(row)

    # Tambahkan total di bawah
    ws.append([])
    ws.append(["TOTAL INCOME", "", "", f"=SUMIF(B2:B1000,\"INCOME\",D2:D1000)"])
    ws.append(["TOTAL EXPENSE", "", "", f"=SUMIF(B2:B1000,\"EXPENSE\",D2:D1000)"])

    filename = "finance_report.xlsx"
    wb.save(filename)

    await update.message.reply_document(document=open(filename, "rb"))

async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("DELETE FROM transactions")
    conn.commit()

    await update.message.reply_text("⚠️ Semua data berhasil dihapus!")

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("monthly", monthly))
app.add_handler(CommandHandler("export", export_excel))
app.add_handler(CommandHandler("resetall", reset_all))
print("running...")
app.run_polling()