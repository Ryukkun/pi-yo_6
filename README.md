# &nbsp;　ピーよ6号

テキストチャンネルに送られてくる 一癖も二癖もあるメッセージ達を<br>ぽめーらのアイドル「ぴーよ」が、華麗なる美声で朗読するよ！<br>


## ☆ コマンド一覧
### 読み上げ
- `.join` ぴーよがぽめーらの通話に突撃するよ！ 喜べ！
- `.bye` ぴーよが通話からおさらばするよ！ 阿鼻叫喚だね！
- `.register (単語) (読み)` ぴーよに文字の読み方を教えることができるよ！
- `.delete (単語)` ぴーよに覚えさせた単語の読みを 忘れさせることができるよ！
- `.s | .shoutup` 無駄口をほざいてるピーよの息の根を簡単に止めるよ！ ぶちぶちのおミンチに差し上げましてよ！
- `/pi-yo6 auto_join (True|False)` これを有効にしておくと、呼んでないのに ぴーよが空気を読んで自動的に ぽめーらの通話に突撃するようになるよ！ オフロスキーだね！<br>


## ☆ ぴーよの賢さ
- ローマ字を自動的に変換
- 英単語をカタカナ読み
- URL メンション などの不要な読み上げを省略
- 声帯変更マジック &nbsp; etc....

## ☆ 声帯変更マジックショー
- `voice: <str>` ※Voiceファイルの場所はConfigから設定
- `speed: <int>` 読む速さ
- `tone: <int>` 声のトーン
- `jf: <int>` しらん
- `a: <int>` わからん

例:
`voice:takumi_normal speed:10 生麦生米生卵 voice:mei_happy tone:5 speed:0.5 隣の客はよくきゃき食う客だ`<br>

## ☆ 開発頑張った偉いね

### 環境構築
- Python 3.8.10にて制作
- Open_Jtalk
- ffmpeg
- OS : Windows MacOS Linux(Ubuntu) にて動作確認済み

### 注意
- 一度起動したら作成される ｢Config.py｣ にて PathやTokenなどを設定することが出来ます
- 自分で用意が必要なもの
  - htsvoice >> Open_Jtalk の再生に必要
  - [VoiceVox Core](https://github.com/VOICEVOX/voicevox_core) >> 無くてもいいが、声の幅が広がる
    - 現在の最新バージョン(ver.0.13.3) では、onnxruntime(ver.1.13.1) が必要とされておる
    - GPUを使用する場合は、CUDAや、CUDNN などが要求されると思う。バージョン毎に変わってるかもしれないから、そこら辺は自分で調べてー！
    

## 連絡はこちらから
[とぅいたー](https://twitter.com/Ryukkun8)
