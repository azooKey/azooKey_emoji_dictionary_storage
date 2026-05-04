from collections import defaultdict, namedtuple
import os
import re
import jaconv
# 実行中のディレクトリを取得する
cwd = os.path.dirname(os.path.abspath(__file__))
# cwdの1つ上の階層を取得する
parent_dir = os.path.dirname(cwd)


# Emojiのデータを自動生成する
# emoji_data.tsvは以下のフォーマット
# >
# The data format is tab separated fields as follows:
# 1) unicode code point
# 2) actual data (in utf-8)
# 3) space separated Yomi
# 4) unicode name
# 5) Japanese name
# 6) space separated descriptions
# 7) unicode emoji version
# Sample:
# 1F1E6 1F1E8	🇦🇨	はた あせんしょんとう				E2.0
#
# emoji-sequences.txt, emoji-zwj-sequences.txtは以下のフォーマット
# >
# Format:
#   code_point(s) ; type_field ; description # comments
# Fields:
#   code_point(s): one or more code points in hex format, separated by spaces
#   type_field, one of the following:
#       Basic_Emoji
#       Emoji_Keycap_Sequence
#       RGI_Emoji_Flag_Sequence
#       RGI_Emoji_Tag_Sequence
#       RGI_Emoji_Modifier_Sequence
#     The type_field is a convenience for parsing the emoji sequence files, and is not intended to be maintained as a property.
#   short name: CLDR short name of sequence; characters may be escaped with \x{hex}.

# Emojiのデータ型をnamedtupleで定義する
# fieldはgenre, codepoints, variations, search keywords, emoji version
Emoji = namedtuple(
    'Emoji', ["genre", "codepoints", "variations", "keywords", "version", "order"])


LEGACY_FAMILY_EMOJIS = {
    "👨‍👦", "👨‍👦‍👦", "👨‍👧", "👨‍👧‍👦", "👨‍👧‍👧",
    "👨‍👨‍👦", "👨‍👨‍👦‍👦", "👨‍👨‍👧", "👨‍👨‍👧‍👦", "👨‍👨‍👧‍👧",
    "👨‍👩‍👦", "👨‍👩‍👦‍👦", "👨‍👩‍👧", "👨‍👩‍👧‍👦", "👨‍👩‍👧‍👧",
    "👩‍👦", "👩‍👦‍👦", "👩‍👧", "👩‍👧‍👦", "👩‍👧‍👧",
    "👩‍👩‍👦", "👩‍👩‍👦‍👦", "👩‍👩‍👧", "👩‍👩‍👧‍👦", "👩‍👩‍👧‍👧",
}


def load_emoji_data(emojis):
    # genreは一旦全てNoneで初期化する
    # 基本的にはemoji_data.tsvのデータを格納し、emoji-sequences.txt、emoji-zwj-sequences.txtのデータからSkin Tone Modifierのついているバージョンを`variations`のフィールドに追加する。
    # emoji_data.tsvを読み込む
    with open(f'{parent_dir}/data/emoji_data.tsv', 'r') as f:
        for line in f:
            # コメント行は読み飛ばす
            if line.startswith('#'):
                continue
            # Emoji 16.0対応のコミット（faf76adc290fc9241b07c501a8224e7a1a6d00fb）以降、CLDRデータのエラーのためにバーが全角になっていて処理が間違っていることがある。
            # 応急処置として、半角スペースに変換する
            if "｜" in line:
                line = line.replace("｜", " ")
            # データをタブで分割する
            data = line.strip().split('\t')
            # データの数が7個でなければエラー
            if len(data) != 7:
                raise ValueError('Invalid data: {}'.format(line))
            # データを変数に格納する
            codepoints, unicode_emoji, name, _, jname, _, version = data
            # codepointsを空白で分割し、intに変換する
            codepoints = [int(cp, 16) for cp in codepoints.strip().split(' ')]
            # nameを空白で分割する
            name = name.split(' ')
            # jnameを空白で分割する
            jname = jname.split(' ')
            # nameとjnameを結合する
            keywords = name + jname
            # Emojiのデータを作成する
            emoji = Emoji(None, unicode_emoji, [], keywords, version, None)
            # Emojiのデータをリストに追加する
            emojis.append(emoji)


def apply_emoji_sequence(emojis):
    # emoji-sequences.txtを読み込み、Skin Tone Modifierのついているバージョンを`variations`のフィールドに追加する
    with open(f'{parent_dir}/data/emoji-sequences.txt', 'r') as f:
        for line in f:
            # コメント行は読み飛ばす
            if line.startswith('#'):
                continue
            if not line.strip():
                continue
            # データをタブで分割する
            data = line.strip().split(';')
            # print(data)
            # データの数が3個でなければエラー
            if len(data) != 3:
                raise ValueError('Invalid data: {}'.format(line))
            # データを変数に格納する
            codepoints, genre, _ = data
            # codepointsに「..」が含まれている場合は読み飛ばす
            if '..' in codepoints:
                continue
            # codepointsを空白で分割し、intに変換する
            codepoints = [int(cp, 16) for cp in codepoints.strip().split(' ')]
            # skin tone modifierは0x1F3FB, 0x1F3FC, 0x1F3FD, 0x1F3FE, 0x1F3FFの5つ
            # codepointsにこれらが含まれていない場合は読み飛ばす
            if not any(cp in codepoints for cp in range(0x1F3FB, 0x1F3FF + 1)):
                continue
            # codepointsからSkin Tone Modifierを除外する
            base_codepoints = [cp for cp in codepoints if cp not in range(
                0x1F3FB, 0x1F3FF + 1)]
            base_unicode_emoji = "".join([chr(cp) for cp in base_codepoints])
            base_unicode_emoji_fe0f = base_unicode_emoji + chr(0xFE0F)
            # Skin Tone Modifierのついているバージョンを`variations`のフィールドに追加する
            for emoji in emojis:
                if emoji.codepoints == base_unicode_emoji or emoji.codepoints == base_unicode_emoji_fe0f:
                    unicode_emoji = "".join([chr(cp) for cp in codepoints])
                    emoji.variations.append(unicode_emoji)
                    break
            else:
                print(data)


def zwj_sequence_skin_tone_pattern_match(codepoints, pattern):
    """
    skin-tone modifierは-1で指定する
    """
    if len(codepoints) != len(pattern):
        return False
    for cp, p in zip(codepoints, pattern):
        if p == -1:
            if cp not in range(0x1F3FB, 0x1F3FF + 1):
                return False
        else:
            if cp != p:
                return False
    return True


def apply_emoji_zwj_sequences(emoji):
    # emoji-zwj-sequences.txtを読み込み、Skin Tone Modifierのついているバージョンを`variations`のフィールドに追加する
    with open(f'{parent_dir}/data/emoji-zwj-sequences.txt', 'r') as f:
        for line in f:
            # コメント行は読み飛ばす
            if line.startswith('#'):
                continue
            if not line.strip():
                continue
            # データをタブで分割する
            data = line.strip().split(';')
            # print(data)
            # データの数が3個でなければエラー
            if len(data) != 3:
                raise ValueError('Invalid data: {}'.format(line))
            # データを変数に格納する
            codepoints, genre, _ = data
            # codepointsに「..」が含まれている場合は読み飛ばす
            if '..' in codepoints:
                continue
            # codepointsを空白で分割し、intに変換する
            codepoints = [int(cp, 16) for cp in codepoints.strip().split(' ')]
            unicode_emoji = "".join([chr(cp)for cp in codepoints])
            # 特定のコードポイントは追加だけして終わる
            if codepoints == [0x1F468, 0x200D, 0x1F9B0]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "男性", "男", "おとこ", "顔", "かお", "赤い髪", "髪", "赤髪"], "E11.0", None))
                continue
            elif codepoints == [0x1F468, 0x200D, 0x1F9B1]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "男性", "男", "おとこ", "顔", "かお", "カール", "髪", "巻き毛"], "E11.0", None))
                continue
            elif codepoints == [0x1F468, 0x200D, 0x1F9B2]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "男性", "男", "おとこ", "顔", "かお", "ハゲ", "脱毛"], "E11.0", None))
                continue
            elif codepoints == [0x1F468, 0x200D, 0x1F9B3]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "男性", "男", "おとこ", "顔", "かお", "白い髪", "髪", "白髪"], "E11.0", None))
                continue
            elif codepoints == [0x1F469, 0x200D, 0x1F9B0]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "女性", "女", "おんな", "顔", "かお", "赤い髪", "髪", "赤髪"], "E11.0", None))
                continue
            elif codepoints == [0x1F469, 0x200D, 0x1F9B1]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "女性", "女", "おんな", "顔", "かお", "カール", "髪", "巻き毛"], "E11.0", None))
                continue
            elif codepoints == [0x1F469, 0x200D, 0x1F9B2]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "女性", "女", "おんな", "顔", "かお", "ハゲ", "脱毛"], "E11.0", None))
                continue
            elif codepoints == [0x1F469, 0x200D, 0x1F9B3]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "女性", "女", "おんな", "顔", "かお", "白い髪", "髪", "白髪"], "E11.0", None))
                continue
            elif codepoints == [0x1F9D1, 0x200D, 0x1F9B0]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "顔", "かお", "赤い髪", "髪", "赤髪"], "E11.0", None))
                continue
            elif codepoints == [0x1F9D1, 0x200D, 0x1F9B1]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "顔", "かお", "カール", "髪", "巻き毛"], "E11.0", None))
                continue
            elif codepoints == [0x1F9D1, 0x200D, 0x1F9B2]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "顔", "かお", "ハゲ", "脱毛"], "E11.0", None))

                continue
            elif codepoints == [0x1F9D1, 0x200D, 0x1F9B3]:
                emojis.append(Emoji(None, unicode_emoji, [], [
                    "顔", "かお", "白い髪", "髪", "白髪"], "E11.0", None))

                continue

            # skin tone modifierは0x1F3FB, 0x1F3FC, 0x1F3FD, 0x1F3FE, 0x1F3FFの5つ
            # codepointsにこれらが含まれていない場合は読み飛ばす
            if not any(cp in codepoints for cp in range(0x1F3FB, 0x1F3FF + 1)):
                continue

            # codepointsの特殊なルールを適用
            # 1F9D1 _ 200D 2764 FE0F 200D 1F9D1 _のパターンにマッチする場合、0x1F491のvariationにする
            if zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F9D1, -1, 0x200D, 0x2764, 0xFE0F, 0x200D, 0x1F9D1, -1]):
                base_codepoints = [0x1F491]
            # 1F9D1 _ 200D 2764 FE0F 200D 1F48B 200D 1F9D1 _のパターンにマッチする場合、0x1F48Fのvariationにする
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F9D1, -1, 0x200D, 0x2764, 0xFE0F, 0x200D, 0x1F48B, 0x200D, 0x1F9D1, -1]):
                base_codepoints = [0x1F48F]
            # 1F468 _ 200D 1F91D 200D 1F468 _のパターンにマッチする場合、0x1F46Cのvariationにする
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F468, -1, 0x200D, 0x1F91D, 0x200D, 0x1F468, -1]):
                base_codepoints = [0x1F46C]
            # 1F469 _ 200D 1F91D 200D 1F468 _のパターンにマッチする場合、0x1F46Bのvariationにする
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F469, -1, 0x200D, 0x1F91D, 0x200D, 0x1F468, -1]):
                base_codepoints = [0x1F46B]
            # 1F469 _ 200D 1F91D 200D 1F469 _のパターンにマッチする場合、0x1F46Dのvariationにする
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F469, -1, 0x200D, 0x1F91D, 0x200D, 0x1F469, -1]):
                base_codepoints = [0x1F46D]
            # handshake: 1F91C, pattern: 1FAF1 _ 200D 1FAF2 _
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1FAF1, -1, 0x200D, 0x1FAF2, -1]):
                base_codepoints = [0x1F91D]
            # mixed skin tone variants added in Emoji 17.0 for bunny ears / wrestling
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F468, -1, 0x200D, 0x1F430, 0x200D, 0x1F468, -1]):
                base_codepoints = [0x1F46F, 0x200D, 0x2642, 0xFE0F]
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F469, -1, 0x200D, 0x1F430, 0x200D, 0x1F469, -1]):
                base_codepoints = [0x1F46F, 0x200D, 0x2640, 0xFE0F]
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F9D1, -1, 0x200D, 0x1F430, 0x200D, 0x1F9D1, -1]):
                base_codepoints = [0x1F46F]
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F468, -1, 0x200D, 0x1FAEF, 0x200D, 0x1F468, -1]):
                base_codepoints = [0x1F93C, 0x200D, 0x2642, 0xFE0F]
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F469, -1, 0x200D, 0x1FAEF, 0x200D, 0x1F469, -1]):
                base_codepoints = [0x1F93C, 0x200D, 0x2640, 0xFE0F]
            elif zwj_sequence_skin_tone_pattern_match(codepoints, [0x1F9D1, -1, 0x200D, 0x1FAEF, 0x200D, 0x1F9D1, -1]):
                base_codepoints = [0x1F93C]
            else:
                # codepointsからSkin Tone Modifierを除外する
                base_codepoints = [cp for cp in codepoints if cp not in range(
                    0x1F3FB, 0x1F3FF + 1) and cp != 0xFE0F]
            base_unicode_emoji = "".join([chr(cp)for cp in base_codepoints])
            normalized_base_unicode_emoji = base_unicode_emoji.replace(chr(0xFE0F), "")
            # print(base_codepoints)
            # print(base_unicode_emoji)
            # Skin Tone Modifierのついているバージョンを`variations`のフィールドに追加する
            for emoji in emojis:
                if emoji.codepoints.replace(chr(0xFE0F), "") == normalized_base_unicode_emoji:
                    unicode_emoji = "".join([chr(cp)for cp in codepoints])
                    emoji.variations.append(unicode_emoji)
                    # print(emoji)
                    break
            else:
                print(base_unicode_emoji)
                print(data, base_codepoints)


def apply_cldr_data(emojis: list[Emoji], file_name: str):
    # ja.xmlを読み込んで絵文字の検索クエリを追加する
    # ja.xmlのフォーマットは、<annotation cp="emoji.codepoints" type="tts">'|'-separated queries</annotation>
    # <annotation cp="😖">困惑 | 困惑した顔 | 混乱 | 顔</annotation>
    with open(f"{parent_dir}/data/{file_name}", "r") as f:
        for line in f:
            if not line.strip():
                continue
            codepoints = None
            queries = set()
            # 正規表現を使う
            match = re.findall(
                r'<annotation cp=".+?" type="tts">.+</annotation>', line)
            if match:
                codepoints = match[0].split("\"")[1]
                _queries = re.sub(r"</?annotation.*?>", "", match[0])
                # Emoji 16.0対応のコミット（632c93a93da35653d43bc4e7b20d23ff46d19c8c）以降、バーが全角になっている場合がある。
                # そこで、処理の前にバーを半角に変換する
                _queries = _queries.replace("｜", "|")
                queries |= {query.strip() for query in _queries.split("|")}
            match = re.findall(
                r'<annotation cp=".+?">.+</annotation>', line)
            if match:
                codepoints = match[0].split("\"")[1]
                _queries = re.sub(r"</?annotation.*?>", "", match[0])
                # Emoji 16.0対応のコミット（632c93a93da35653d43bc4e7b20d23ff46d19c8c）以降、バーが全角になっている場合がある。
                # そこで、処理の前にバーを半角に変換する
                _queries = _queries.replace("｜", "|")
                queries |= {query.strip() for query in _queries.split("|")}
            if codepoints is None:
                continue
            codepoints2 = "".join(
                [cp for cp in codepoints if ord(cp) != 0xFE0F])

            for i in range(len(emojis)):
                if emojis[i].codepoints in [codepoints, codepoints2]:
                    for query in queries:
                        # queryのフィルタ
                        if query.startswith("旗: "):
                            query = query[3:]
                        emojis[i].keywords.append(query)


def apply_emoji_test_data(emojis):
    # emoji-test.txtを読み込んでジャンルの情報を追加する
    # emoji-test.txtのフォーマットは、genre_name\temoji_list(comma-separated)
    with open(f"{parent_dir}/data/emoji-test.txt", "r") as f:
        current_group = ""
        count = 0
        for line in f:
            if not line.strip():
                continue
            if line.startswith("# group:"):
                current_group = line.split(":")[1].strip()
                # ジャンルの統合
                if current_group == "Smileys & Emotion":
                    current_group = "Smileys & People"
                if current_group == "People & Body":
                    current_group = "Smileys & People"
                continue
            elif line.startswith("#"):
                continue
            count += 1
            codepoints = [int(cp, 16)
                          for cp in line.split(";")[0].strip().split(" ")]
            unicode_emoji1 = "".join([chr(cp)for cp in codepoints] + [chr(0xFE0F)])
            unicode_emoji2 = "".join([chr(cp)for cp in codepoints])
            unicode_emoji3 = "".join([chr(cp)
                                     for cp in codepoints if cp != 0xFE0F])
            for i in range(len(emojis)):
                if emojis[i].codepoints in [unicode_emoji1, unicode_emoji2, unicode_emoji3]:
                    # namedtupleのフィールドを変更するには、_replaceを使う
                    emojis[i] = emojis[i]._replace(genre=current_group)
                    emojis[i] = emojis[i]._replace(order=count)
                    emojis[i] = emojis[i]._replace(codepoints=unicode_emoji1)
            # print(genre, emoji_list)


def apply_additional_dict(emojis):
    with open(f"{parent_dir}/data/emoji_additional.tsv", "r") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            # tsvファイルで、1列目が絵文字、2列目がsearch keywordsなので、それを取得
            emoji = line.split("\t")[0]
            search_keywords = line.split("\t")[1]
            # search keywordsを,で分割
            search_keywords = search_keywords.split(",")
            emoji2 = emoji.replace(chr(0xFE0F), "")

            # emojisに追加
            for i in range(len(emojis)):
                if emojis[i].codepoints in [emoji, emoji2]:
                    # namedtupleのフィールドを変更するには、_replaceを使う
                    emojis[i].keywords.extend(search_keywords)


def apply_manual_filter(emojis):
    # フィルタリング
    for i in range(len(emojis)):
        # keywordsの「絵文字」を除去する
        if "絵文字" in emojis[i].keywords:
            emojis[i].keywords.remove("絵文字")
        # keywordsの空文字を除去する
        if "" in emojis[i].keywords:
            emojis[i].keywords.remove("")
        # keywordsのカタカナをひらがなに、大文字を小文字に置き換え、重複を除去する
        new_keywords = [
            jaconv.kata2hira(query.lower())
            for query in emojis[i].keywords
        ]
        new_keywords = list(sorted(set(new_keywords)))
        emojis[i] = emojis[i]._replace(keywords=new_keywords)
        if emojis[i].genre is None:
            print("Error genre not found", emojis[i].codepoints, [ord(c) for c in emojis[i].codepoints])
            continue


def load_surface_aliases():
    aliases = {}
    with open(f"{parent_dir}/data/emoji_surface_aliases.tsv", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            normalized_emoji, surface_aliases = line.split("\t")
            aliases[normalized_emoji] = surface_aliases.split(",")
    return aliases


def surface_aliases_for(emoji: Emoji, surface_aliases: dict[str, list[str]]) -> list[str]:
    normalized_codepoints = emoji.codepoints.replace(chr(0xFE0F), "")
    return surface_aliases.get(normalized_codepoints, [])


def unique(items: list[str]) -> list[str]:
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def version_greater_or_equal(version1, version2):
    return float(version1[1:]) <= float(version2[1:])


def should_include_emoji(emoji: Emoji, maximum_version: str):
    if not version_greater_or_equal(emoji.version, maximum_version):
        return False
    # From Emoji 15.1 onward, keep the new silhouette-style family set and
    # drop the legacy detailed family ZWJ sequences from generated outputs.
    if float(maximum_version[1:]) >= 15.1:
        if emoji.codepoints.replace(chr(0xFE0F), "") in LEGACY_FAMILY_EMOJIS:
            return False
    return True


def output(emojis, version_targets: list[str], surface_aliases: dict[str, list[str]]):
    # ジャンルの出力順を固定する
    genre_order = [
        "Activities",
        "Travel & Places",
        "Symbols",
        "Smileys & People",
        "Objects",
        "Flags",
        "Component",
        "Food & Drink",
        "Animals & Nature",
    ]

    # ジャンルごとにソートする
    emojis_genre_sorted = {genre: [] for genre in genre_order}
    for emoji in emojis:
        emojis_genre_sorted.setdefault(emoji.genre, []).append(emoji)
    for genre in emojis_genre_sorted:
        emojis_genre_sorted[genre] = sorted(
            emojis_genre_sorted[genre], key=lambda emoji: emoji.order)

    emojis_sorted = sorted(emojis, key=lambda emoji: emoji.order)
    for maximum_version in version_targets:
        # ジャンルごとにソートし、genre\temojis,の形式で出力する
        with open(f"{parent_dir}/EmojiDictionary/emoji_genre_{maximum_version}.txt", "w") as f:
            lines = []
            for genre in genre_order:
                lines.append(
                    genre
                    + "\t"
                    + ",".join(
                        [
                            emoji.codepoints
                            for emoji in emojis_genre_sorted.get(genre, [])
                            if should_include_emoji(emoji, maximum_version)
                        ]
                    )
                )
            f.write("\n".join(lines))

        # tsvにして./EmojiDictionary/emoji_all.tsv.genを出力する
        with open(f"{parent_dir}/EmojiDictionary/emoji_all_{maximum_version}.txt", "w") as f:
            # emojiの各行をtsvの行にする
            lines = []
            for emoji in emojis_sorted:
                if should_include_emoji(emoji, maximum_version):
                    variations = unique(emoji.variations + surface_aliases_for(emoji, surface_aliases))
                    line = "\t".join([
                        emoji.codepoints,
                        ",".join(emoji.keywords),
                        ",".join(variations)
                    ])
                    lines.append(line)
            # tsvの行を出力する
            f.write("\n".join(lines))

        # 辞書ファイル向けに./EmojiDictionary/emoji_dict.tsv.genを出力する
        with open(f"{parent_dir}/EmojiDictionary/emoji_dict_{maximum_version}.txt", "w") as f:
            # format例: アーティスト	👨‍🎤	5	5	501	-20
            lines = []
            for emoji in emojis_sorted:
                if should_include_emoji(emoji, maximum_version):
                    # keywordはカタカナ化して、重複を除去し、「ひらがな/英数字」に完全マッチするもののみ許す
                    keywords = [
                        jaconv.hira2kata(keyword)
                        for keyword in emoji.keywords
                        if re.fullmatch(r"[\u3040-\u309Fー・a-zA-Z0-9]+", keyword)
                    ]
                    for surface in unique([emoji.codepoints] + surface_aliases_for(emoji, surface_aliases)):
                        for keyword in keywords:
                            line = "\t".join([
                                keyword,
                                surface,
                                "5",
                                "5",
                                "501",
                                "-20"
                            ])
                            lines.append(line)
            f.write("\n".join(lines))
    print("Successfuly generated emoji data files")


if __name__ == "__main__":
    # Emojiのデータを格納するリスト
    emojis = []
    # setup
    # mkdir EmojiDictionary
    if not os.path.exists(f"{parent_dir}/EmojiDictionary"):
        os.makedirs(f"{parent_dir}/EmojiDictionary")

    load_emoji_data(emojis)
    apply_emoji_sequence(emojis)
    apply_emoji_zwj_sequences(emojis)
    apply_cldr_data(emojis, "ja.xml")
    apply_cldr_data(emojis, "ja_derived.xml")
    apply_additional_dict(emojis)
    apply_emoji_test_data(emojis)
    apply_manual_filter(emojis)
    output(
        emojis,
        version_targets=["E13.1", "E14.0", "E15.0", "E15.1", "E16.0", "E17.0"],
        surface_aliases=load_surface_aliases(),
    )
