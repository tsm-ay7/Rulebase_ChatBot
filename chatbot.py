from janome.tokenizer import Tokenizer
from janome.analyzer import Analyzer
from janome.tokenfilter import CompoundNounFilter, POSKeepFilter
import sqlite3
from datetime import datetime
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
import torch
import random
import requests
import json
import csv
import os
import gradio as gr

tokenizer = Tokenizer() # トークナイザーの初期化
user_select_global = [] # グローバル変数として user_select を定義


## データベースに接続
def db_connect():
  try:
    conn = sqlite3.connect('DataBase\App.db')
    return conn
  except sqlite3.OperationalError as oe:
       print(f"データベース接続エラー:{oe}")
  except Exception as e:
       print(f"エラーが発生しました:{e}")



## データベースから挨拶用語を取得
def get_greetings(message):
  #１行ごと取り出す
  try:
      conn = db_connect()
      cursor = conn.cursor() #カーソルオブジェクトを作成
      cursor.execute("SELECT greeting FROM greetings") # クエリの実行
      gr_list = []   #空のリスト1
      #print(f"message:{message}") #debug用
      for row in cursor.fetchall():
          gr_list.append(row[0]) # DBの挨拶用語をgr_listに格納
      # ユーザーの入力と挨拶用語を比較（一致していたら挨拶を返す）
      for token in tokenizer.tokenize(message):
        if token.surface in gr_list:
          return token.surface
        else:
          return False
  except sqlite3.OperationalError as oe:
         print(f"データベース接続エラーor存在しないテーブルや列:{oe}")
  except sqlite3.ProgrammingError as pe:
         print(f"無効なSQL文です:{pe}")
  except Exception as e:
         print(f"エラーが発生しました:{e}")



## 感情分析（ネガティブな言葉に励ましの言葉を返す）
# 事前学習済みモデルの読み込み
def load_sentiment_analysis_model(model_name):
  model = AutoModelForSequenceClassification.from_pretrained(model_name)
  tokenizer = AutoTokenizer.from_pretrained(model_name)
  sentiment_analysis_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)
  return sentiment_analysis_pipeline

# 感情分析
def detect_negative_sentiment(text, sentiment_analysis_pipeline):
  result = sentiment_analysis_pipeline(text)
  sentiment = result[0]["label"]
  score = result[0]["score"]
  #print(f"Sentiment: {sentiment}, Score: {score}")
  return sentiment , score

# 応答ルール
def comfort_bot(message, sent_analysis_model):
  sentiment, score = detect_negative_sentiment(message, sent_analysis_model)
  if sentiment == "negative" and score > 0.9999: # ユーザーの入力がnegativeかつ、その単語のscore > 0.9999である
    return random.choice(encouragement_messages)
  else:
    return False

sentiment_analysis_model_name = "jarvisx17/japanese-sentiment-analysis"
sentiment_analysis_model = load_sentiment_analysis_model(sentiment_analysis_model_name)

# negativeな言葉に対する返答
encouragement_messages = [
    "よく頑張りました！",
    "辛い時期もありますが、きっと乗り越えられます！",
    "自分を信じてください！",
    "前向きな気持ちでいきましょう！"
]




## カテゴリー選択による出力
# 選択したカテゴリーによるメッセージ
def generate_msg(user_select):
  msg = "\n"
  if not user_select:
    msg += "アルファベットを選択してください。"
    return msg
  if "A" in user_select:
    msg += "日時・開催場所　"
  if "B" in user_select:
    msg += "イベント・タイムスケジュール　"
  if "C" in user_select:
    msg += "出店　"
  if "D" in user_select:
    msg += "アクセス　"
  if "E" in user_select:
    msg += "質問を入力してください。\n"
    return msg
  msg += "についての質問を入力してください。\n"
  return msg

# ユーザーがどのカテゴリーを選択したか判断
def handle_user_selection(user_select):
  global user_select_global
  user_select_global = user_select  # user_selectをグローバル変数に保存
  msg = generate_msg(user_select)
  if any(char in "ABCDE" for char in user_select):
    return [(f"ユーザーの選択：{', '.join(user_select)}",msg)]
  elif not user_select:
    return [(f"ユーザーの選択：",msg)]

# カテゴリー選択のクエリ
def cat_select(user_select):
  categories = []
  categories_and = ""  # 変数を初期化
  for cha in "ABCDE":
      if cha in user_select:
        categories.append(f"category = '{cha}'")
        categories_and = " OR ".join(categories)
  return categories_and



## 最初のチャットボットのテキスト表示
def display_msg():
  text = ("\n〇〇大学の文化祭について質問したい内容に当てはまるアルファベットを入力してください。(複数可)\n\n"
          "A，日時・開催場所について\n"
          "B，イベント・タイムスケジュールについて\n"
          "C，出店について\n"
          "D，アクセスについて\n"
          "E，その他\n")
  return text




## ユーザー入力の処理
def response(user_select,message):
  # トークンフィルターの設定
  token_filters = [POSKeepFilter(['名詞','動詞'])] # 名詞と動詞のトークンだけにする
  analyzer = Analyzer(tokenizer=tokenizer, token_filters=token_filters) #Analyzerが解析
  #ユーザの入力をトークンに分割
  tokens = list(analyzer.analyze(message))
  if not tokens:
    return False
  # ユーザ入力の名詞と動詞だけをリストに格納
  user_token = [token.surface for token in tokens if token.part_of_speech.startswith('名詞') or token.part_of_speech.startswith('動詞')]
  categories_and = cat_select(user_select) # カテゴリー選択
  if not user_token:
    return False
  # カテゴリー選択をしていない場合
  elif not categories_and:
    return "アルファベットを選択してください。"
  else:
    condition = [] # 空のリスト作成
    for user_surface in user_token:
      condition.append(f"question LIKE '%{user_surface}%'")
      condition_and = " AND ".join(condition)
    condition_where = f"WHERE ({categories_and}) AND {condition_and}"
    query = f"SELECT DISTINCT answer FROM QA {condition_where}"

    conn = db_connect() # 関数の呼び出し
    cursor = conn.cursor() # カーソルを作成
    cursor.execute(query) # クエリの実行

    result_list = [] # 空のリスト
    for row in cursor.fetchall(): # 実行したクエリの結果をリストに格納
      result_list.append(row[0])
    if len(result_list) > 1: # リストが２個になった場合はログ出力できないため文字列として結合
      result = " \n ".join(result_list)
      return result
    elif not result_list: # DBにユーザーの質問がなかった場合
      return False
    else:
      return result_list[0]



## テーブルQA全体にユーザの質問がなかったらteamsに送信
## teamsに送信するロジック(379行目のコメント状態を解除して実行)
# def teams_trans(message):
#   # TeamsのWebhook URL
#   webhook_url = ''
#   # 送信するメッセージ
#   message = {
#     "attachments": [
#       {
#         "contentType": "application/vnd.microsoft.card.adaptive",
#         "content": {
#           "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
#           "type": "AdaptiveCard",
#           "version": "1.2",
#           "body": [
#             {
#               "type": "TextBlock",
#               "text": message,
#               "wrap": True,
#               "markdown": True
#             }
#           ]
#         }
#       }
#     ]
#   }

#   # POSTリクエストを送信
#   response = requests.post(
#       url=webhook_url,
#       data=json.dumps(message),
#       headers={'Content-Type': 'application/json'}
#   )

# # テーブルQA全体にユーザの質問がなかったらteamsに送信
# def trans(message):
#   # トークンフィルターの設定
#   token_filters = [POSKeepFilter(['名詞','動詞'])] # 名詞と動詞のトークンだけにする
#   analyzer = Analyzer(tokenizer=tokenizer, token_filters=token_filters) #Analyzerが解析
#   #ユーザの入力をトークンに分割
#   tokens = list(analyzer.analyze(message))
#   if not tokens:
#     pass
#   # ユーザ入力の名詞と動詞だけをリストに格納
#   user_token = [token.surface for token in tokens if token.part_of_speech.startswith('名詞') or token.part_of_speech.startswith('動詞')]
#   #print(user_token) # デバック用
#   if not user_token:
#     pass
#   else:
#     condition = [] # 空のリスト作成
#     for user_surface in user_token:
#       condition.append(f"question LIKE '%{user_surface}%'")
#       condition_and = " AND ".join(condition)
#     condition_where = f"WHERE {condition_and}"
#     query = f"SELECT DISTINCT answer FROM QA {condition_where}"
#     #print(query) # debug

#     conn = db_connect() # 関数の呼び出し
#     cursor = conn.cursor() # カーソルを作成
#     cursor.execute(query) # クエリの実行

#     try:
#       result_list = [] # 空のリスト
#       for row in cursor.fetchall(): # 実行したクエリの結果をリストに格納
#         result_list.append(row[0])
#       if not result_list:
#         print(f"Teams送信: メッセージは「{message}」です")
#         teams_trans(message)
#         bot_response = "わかりませんでした。"
#       else:
#         bot_response = "アルファベットを選びなおしてください。"
#       return bot_response
#     except Exception:
#       pass




## ログをデータベースに格納
def log_output(message, bot_response):
    try:
        conn = db_connect()
        cursor = conn.cursor()
        # テーブルを作成
        cursor.execute('''CREATE TABLE IF NOT EXISTS log (id integer primary key, 処理日時, ユーザの入力, ボットの回答結果, 回答率)''')
        log_query = """INSERT INTO log(処理日時, ユーザの入力, ボットの回答結果) VALUES(?,?,?)"""

        # ログの最大保存数を指定
        max_log = 500

        # ログの総数を取得
        cursor.execute("SELECT COUNT(*) FROM log")
        total_num = cursor.fetchone()[0] + 1

        # 最大保存数を超えたら古いデータを削除
        if total_num >= max_log:
          cursor.execute("DELETE FROM log WHERE id = (SELECT MIN(id) FROM log)")

        # 回答できた質問数を取得
        cursor.execute('SELECT COUNT(ボットの回答結果) FROM log WHERE ボットの回答結果 != "わかりませんでした。" ')
        answered_num = cursor.fetchone()[0] + 1

        # 回答率を計算
        if total_num != 0:
          response_rate = round((answered_num / total_num) * 100,2)
        else:
          response_rate = None

        #データを挿入
        log_query = """INSERT INTO log(処理日時, ユーザの入力, ボットの回答結果, 回答率) VALUES(?,?,?,?)"""
        now = datetime.now()
        now_datetime = f"{now.year}/{now.month}/{now.day} - {now.hour}:{now.minute}:{now.second}"
        data0 = [(now_datetime, message, bot_response, response_rate)]
        cursor.executemany(log_query, data0)#複数のデータを追加したい場合はexecutemanyメソッドを使う
        conn.commit()

        # csv出力するデータ
        cursor.execute('SELECT 処理日時,ユーザの入力,ボットの回答結果,回答率 FROM log ORDER BY id DESC')
        csv_row = cursor.fetchone()
        if csv_row:
          csv_date = csv_row[0]
          csv_user = csv_row[1]
          csv_bot = csv_row[2]
          csv_rate = csv_row[3]
          rate_data = [
              ["date", "user_imput","bot_response","total_num","answered_num","response_rate"],
              [csv_date, csv_user, csv_bot,total_num,answered_num, csv_rate]
          ]

          file_path = "DataBase\log.csv"
          file_exists = os.path.exists(file_path) # ファイルが存在するか確認
          # csvに保存
          with open(file_path,'a', encoding='utf-8', newline='') as f:
            dataWriter = csv.writer(f)
            if not file_exists:
              dataWriter.writerow(rate_data[0])
            dataWriter.writerows(rate_data[1:])
          # csvに保存するデータの数を制限
          if file_exists:
              with open(file_path, 'r', encoding='utf-8') as f:
                  reader = csv.reader(f)
                  lines = list(reader)
                  if len(lines) > max_log:
                    lines = lines[-max_log:]
              with open(file_path,'w',encoding="utf-8", newline='') as f:
                dataWriter = csv.writer(f)
                dataWriter.writerows(lines)
          else:
            pass
        return cursor.fetchall() #クエリの結果を取得
    except sqlite3.OperationalError as oe:
        print(f"データベース接続エラーor存在しないテーブルや列:{oe}")
    except sqlite3.ProgrammingError as pe:
        print(f"無効なSQL文です:{pe}")
    except Exception as e:
        print(f"ログ出力のエラーが発生しました:{e}")



## 応答条件（チャットに表示）
def response_loop(message, user_select):
  user_select = user_select_global
  res = response(user_select,message)
  comfort = comfort_bot(message, sentiment_analysis_model)
  greeting = get_greetings(message)

  # テキストが空の場合
  if not message:
    return "質問を入力してください。"
  # 感情分析による出力
  elif comfort:
    bot_response = comfort
    log_output(message, bot_response) # ログをデータベースに格納
    return comfort
  # 挨拶返答
  elif greeting:
    bot_response = greeting
    log_output(message, bot_response) # ログをデータベースに格納
    return greeting
  # 文化祭の質問に対しての返答
  elif res:
     bot_response = res
     log_output(message, bot_response) # ログをデータベースに格納
     return res
  # ユーザーの入力がどの条件にも当てはまらない場合
  else:
    #bot_response = trans(message) # teams送信の条件
    log_output(message, bot_response) # ログをデータベースに格納
    return bot_response
  # DB接続を閉じる
  conn = db_connect()
  conn.close()


## ログイン認証（パスワードがユーザー名＋ユーザー名の文字数の場合）
def auth(user_name, password):
    if user_name == "test" and password == "pass":
        return True # 認証成功
    else:
        return False # 認証失敗

# UI
category = ["A", "B", "C", "D", "E"]
with gr.Blocks() as demo:
    gr.Markdown("## 〇〇大学＿文化祭チャットボット") # タイトル
    gr.Markdown(display_msg(),line_breaks=True) # 最初のテキスト表示
    user_select = gr.CheckboxGroup(choices=category, label="選択肢を選んでください") # チェックボックス
    #gr.btn = gr.Button("決定")
    # カスタムチャットボットの作成
    custom_chatbot = gr.Chatbot()

    # ボタンがクリックされたときに関数を呼び出し、結果をチャットボットに表示
    #gr_btn.click(fn=handle_user_selection, inputs=user_select, outputs=custom_chatbot)
    gr.CheckboxGroup.select(fn=handle_user_selection,inputs=user_select, outputs=custom_chatbot, block=user_select)
    # テキスト入力による表示
    gr.ChatInterface(fn=response_loop,chatbot=custom_chatbot)

#demo.launch(auth=auth, share=True) # ログイン認証付き出力
demo.launch(share=True)
#demo.launch(debug=True) # debaugあり出力