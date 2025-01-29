# Rulebase_ChatBot
-ルールベース型のチャットボット（未実装）
-用途は大学の文化祭の質疑応答等
-ユーザーの入力に基づいてデータベース上のデータから回答

## Reference Image
![チャットボット参考１](Readme\チャットボット１.gif)
![チャットボット参考２](Readme\チャットボット２.gif)


## Dependency
【開発言語】
Python

【ライブラリ】（google colabで実行する場合は頭に!を付ける）
pip install janome
pip install transformers
pip install fugashi
pip install unidic_lite
pip install gradio==5.8.0
pip install torch
pip install requests


## Usage
-teamsへの送信ロジックのコメント(193～266行目と379行目)を解除
192行目のwebhook_urlを入力：webhook_url = 'ここにurlを入力'
webhookのurlの生成はこちらを参考：https://qiita.com/k_adc/items/62d27d7941cec604d3de

-chatbot.pyを実行
-生成されたローカルのurlにアクセス
（* Running on local URL:  http:　　）
-入力例
ユーザー：開催場所
ボット　：〇〇で開催します。


## References
［teamsへの送信ロジック］
https://qiita.com/k_adc/items/62d27d7941cec604d3de
［感情分析］
https://toukei-lab.com/chatbot_python