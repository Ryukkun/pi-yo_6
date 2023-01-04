

# speaker_user = [
#     ["四国","めたん"],
#     ["ずんだ"],
#     ["春日部","つむぎ"],
#     ["雨晴","はう"],
#     ["波音","りつ","リツ"],
#     ["玄野","武宏"],
#     ["白上","虎太郎"],
#     ["青山","龍星"],
#     ["冥鳴","ひまり"],
#     ["九州","そら"],
#     ["もち子","もちこ"],
#     ["剣崎","雌雄"],
#     ["White","CUL"],
#     ["後鬼"],
#     ["No.7","No7"],
# ]

# speaker_id = [
#     {"name":"四国めたん","styles":[
#         {"id":2,"name":"ノーマル"},
#         {"id":0,"name":"あまあま"},
#         {"id":6,"name":"ツンツン"},
#         {"id":4,"name":"セクシー"},
#         {"id":36,"name":"ささやき"},
#         {"id":37,"name":"ヒソヒソ"}
#         ],"version":"0.13.2"},
#     {"name":"ずんだもん","styles":[
#         {"id":3,"name":"ノーマル"},
#         {"id":1,"name":"あまあま"},
#         {"id":7,"name":"ツンツン"},
#         {"id":5,"name":"セクシー"},
#         {"id":22,"name":"ささやき"},
#         {"id":38,"name":"ヒソヒソ"}
#         ],"version":"0.13.2"},
#     {"name":"春日部つむぎ","styles":[
#         {"id":8,"name":"ノーマル"}
#         ],"version":"0.13.2"},
#     {"name":"雨晴はう","styles":[
#         {"id":10,"name":"ノーマル"}
#         ],"version":"0.13.2"},
#     {"name":"波音リツ","styles":[
#         {"id":9,"name":"ノーマル"}
#         ],"version":"0.13.2"},
#     {"name":"玄野武宏","styles":[
#         {"id":11,"name":"ノーマル"}
#         ],"version":"0.13.2"},
#     {"name":"白上虎太郎","styles":[
#         {"id":12,"name":"ふつう"},
#         {"id":32,"name":"わーい"},
#         {"id":33,"name":"びくびく"},
#         {"id":34,"name":"おこ"},
#         {"id":35,"name":"びえーん"}
#         ],"version":"0.13.2"},
#     {"name":"青山龍星","styles":[
#         {"id":13,"name":"ノーマル"}
#         ],"version":"0.13.2"},
#     {"name":"冥鳴ひまり","styles":[
#         {"id":14,"name":"ノーマル"}
#         ],"version":"0.13.2"},
#     {"name":"九州そら","styles":[
#         {"id":16,"name":"ノーマル"},
#         {"id":15,"name":"あまあま"},
#         {"id":18,"name":"ツンツン"},
#         {"id":17,"name":"セクシー"},
#         {"id":19,"name":"ささやき"}
#         ],"version":"0.13.2"},
#     {"name":"もち子さん","styles":[
#         {"id":20,"name":"ノーマル"}
#         ],"version":"0.13.2"},
#     {"name":"剣崎雌雄","styles":[
#         {"id":21,"name":"ノーマル"}
#         ],"version":"0.13.2"},
#     {"name":"WhiteCUL","styles":[
#         {"id":23,"name":"ノーマル"},
#         {"id":24,"name":"たのしい"},
#         {"id":25,"name":"かなしい"},
#         {"id":26,"name":"びえーん"}
#         ],"version":"0.13.2"},
#     {"name":"後鬼","styles":[
#         {"id":27,"name":"人間ver."},
#         {"id":28,"name":"ぬいぐるみver."}
#         ],"version":"0.13.2"},
#     {"name":"No.7","styles":[
#         {"id":29,"name":"ノーマル"},
#         {"id":30,"name":"アナウンス"},
#         {"id":31,"name":"読み聞かせ"}
#         ],"version":"0.13.2"}]


# from discord.app_commands import Choice
# def speaker_list():
#     res = []
#     for name_dic in speaker_id:
#         name = name_dic['name']
#         for style_dic in name_dic['styles']:
#             style = style_dic['name']
#             id = style_dic['id']
#             res.append(Choice(name=f'{name}_{style}', value=str(id)))
#     return res

