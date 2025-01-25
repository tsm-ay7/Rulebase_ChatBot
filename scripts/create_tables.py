import sqlite3

# データベースに接続
conn = sqlite3.connect('DataBase\App.db')
# カーソルを作成
cursor = conn.cursor()

# greetingsテーブルを作成
cursor.execute('''
CREATE TABLE IF NOT EXISTS  greetings(
    id integer primary key,
    greeting
)
''')

# QAテーブルを作成
cursor.execute('''
CREATE TABLE IF NOT EXISTS  QA(
    id integer primary key,
    category, var, question, answer
)
''')

# 変更を保存して接続を閉じる
conn.commit()
conn.close()
print("tables created successfully.")