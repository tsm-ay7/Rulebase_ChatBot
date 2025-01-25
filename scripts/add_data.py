import sqlite3

# データを追加する
# データベースに接続
conn = sqlite3.connect('DataBase\App.db')
cursor = conn.cursor()

# greetingsテーブルに追加
#sql = """INSERT INTO greetings(greeting) VALUES(?)"""

# QAテーブルに追加
sql = """INSERT INTO QA(category, var, question, answer) VALUES(?,?,?,?)"""

# data = [
# ]
# cursor.executemany(sql, data)

# # 変更を保存
# conn.commit()

# 結果を表示
cursor.execute('SELECT * FROM log')
rows = cursor.fetchall() #全レコードを取り出す
#取得したデータの各行についてループを実行
for row in rows:
    print(row)

conn.close()