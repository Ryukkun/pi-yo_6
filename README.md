# &nbsp;　ぴーよ6号

テキストチャンネルに送られてくる 一癖も二癖もあるメッセージ達を<br>ぽめーらのアイドル「ぴーよ」が、華麗なる美声で朗読するよ！<br>


## ☆ コマンド一覧
- `.join` ぴーよがぽめーらの通話に突撃するよ！ 喜べ！
- `.bye` ぴーよが通話からおさらばするよ！ 阿鼻叫喚だね！
- `.register 単語 読み` ぴーよに文字の読み方を教えることができるよ！
- `.delete 単語` ぴーよに覚えさせた単語の読みを 忘れさせることができるよ！
- `.黙れ` ぴーよを黙らせるよ！ ぶちぶちのおミンチに差し上げましてよ！<br>

## ☆ 声帯変更マジックショー
- `voice: <str>`
    - open_jtalk
    - mei
        - mei_normal (Default)
        - mei_angry
        - mei_bashful
        - mei_happy
        - mei_sad
    - takumi
        - takumi_normal
        - takumi_angry
        - takumi_happy
        - takumi_sad
    -tohoku
        - tohoku_angry
        - tohoku_hppy
        - tohoku_neutral
        - tohoku_sad

- `speed: <int>` 読む速さ
- `tone: <int>` 声のトーン
- `jf: <int>` しらん
- `a: <int>` わからん

例:
`voice:takumi_normal speed:10 生麦生米生卵 voice:mei_happy tone:5 speed:0.5 隣の客はよくきゃき食う客だ`<br>

## ☆ 開発向け

### 環境建築
- Python 3.8.10にて制作
- Open_Jtalk
- ffmpeg

- OS
    - ○ Linux
    - ⬡ Windows wanakana がちょっとバグルかも  
    - △ Mac いけるっぽい匂いする

一度起動したら作成される ｢Config.ini｣ に記載されている Pathが ほとんどLinux向けなんで、windows の人頑張って書き換えてね<br>

## 連絡はこちらから
[とぅいたー](https://twitter.com/Ryukkun8)