import json
import tqdm

from hanzipy.decomposer import HanziDecomposer
from hanzipy.dictionary import HanziDictionary

# Инициализация
decomposer = HanziDecomposer()
dictionary = HanziDictionary()

def get_component_meaning(component):
    """Получаем словесное описание компонента, если есть"""
    try:
        definition = dictionary.definition_lookup(component)
        
        # print(f"component: {component}, definition: {definition}")

        if definition:
            return [d.get('definition', '') for d in definition]
        else:
            return ''
    except Exception as e:
        # print(f"[{component}] Error: {e}")
        return ''

def build_hanzi_tree(char):
    """Рекурсивно строим дерево компонента"""
    comp = decomposer.decompose(char)
    
    # print(f"char: {char}, comp: {comp}")    
    # try:
    #     print(f"dictionary.definition_lookup(char): {dictionary.definition_lookup(char)}")
    # except Exception as e:
    #     print(f"Error: {e}")
    # print(comp['once'], [char])

    if not comp or comp['once'] == [char]:  # базовая часть
        return {
            'character': char,
            'meaning': get_component_meaning(char),
            'once': [],
            'radical': [],
            'graphical': []
        }
    
    tree = {
        'character': char,
        'meaning': get_component_meaning(char),
        'once': comp.get('once', []),
        'radical': comp.get('radical', []),
        'graphical': comp.get('graphical', [])
    }

    # рекурсивно строим для once-компонентов
    tree['children'] = {}
    for c in tree['once']:
        if c != "No glyph available":
            tree['children'][c] = build_hanzi_tree(c)
    return tree

def print_tree(node, radicals_dict, indent="", need_print_node=False):
    """Печать дерева с компонентами и значениями"""
    # print(node)
    if need_print_node:
        print(f"{indent}{node['character']} {[m[:20] for m in node['meaning']]}" + (" -> " + f"{[r['name_ru'] for r in radicals_dict[node['character']]]}" if node['character'] in radicals_dict else ""))
    if ('children' in node):
        for i, (k, v) in enumerate(node['children'].items()):
            connector = "└── " if i == len(node['children'])-1 else "├── "
            print(indent + connector + f"{k} ({[m[:20] for m in v['meaning']]})" + (" -> " + f"{[r['name_ru'] for r in radicals_dict[k]]}" if k in radicals_dict else ""))
            print_tree(v, radicals_dict, indent + ("    " if i == len(node['children'])-1 else "│   "), need_print_node=False)

def build_string(node, radicals_dict, indent="", need_add_node=False):
    result = ""
    if need_add_node:
        if node['character'] in radicals_dict:
            # print(', '.join(radicals_dict[node['character']][0]['name_ru']))
            # print(f"{node['character']} <{', '.join([','.join(r['name_ru']) for r in radicals_dict[node['character']]])}>")
            return f"{indent}{node['character']} \'{','.join([','.join(r['name_ru']) for r in radicals_dict[node['character']]])}\'"
        else:
            result += f"{indent}{node['character']}"
        result += "\n"
    if ('children' in node):
        children = []
        for i, (k, v) in enumerate(node['children'].items()):
            connector = "└── " if i == len(node['children'])-1 else "├── "
            if k in radicals_dict:
                children.append(f"{indent}{connector}{k} \'{','.join([','.join(r['name_ru']) for r in radicals_dict[k]])}\'")
            else:
                children.append(f"{indent}{connector}{k}")
                children.append(build_string(v, radicals_dict, indent + ('    ' if i == len(node['children'])-1 else '│   '), need_add_node=False))
        result += "\n".join(children)
        # if not need_add_node:
        #     result = "(" + result + ")"
    
    return result

# # Пример: иероглиф 的
# char = "的"
# tree = build_hanzi_tree(char)
# print(f"Дерево компонентов для '{char}':")
# print_tree(tree)

if __name__ == "__main__":
    INPUT_FILE = "/home/tony/repos/words/words/radicals_names/words_Китайский_20250822_192754.json"
    RADICALS_FILE = "/home/tony/repos/words/words/radicals_names/radicals_chat_gpt.json"

    OUTPUT_FILE = INPUT_FILE + ".new_radicals.json"

    LIMIT = 10_000

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(RADICALS_FILE, 'r', encoding='utf-8') as f:
        radicals_data = json.load(f)

    radicals_dict = {}
    for radical in radicals_data:
        for char in radical["char"]:
            if char in radicals_dict:
                print(f"char {char} already in radicals_dict")
            else:
                radicals_dict[char] = []
            radicals_dict[char].append(radical)

        for char in radical["radical"]:
            if char in radicals_dict:
                print(f"radical {char} already in radicals_dict")
            else:
                radicals_dict[char] = []
            radicals_dict[char].append(radical)

    print(f"radicals_dict: {len(radicals_dict)}")

    for entry in tqdm.tqdm(data["words"][:LIMIT]):
        word_lower = entry["word_foreign"].strip().lower()
        word_number = entry["word_number"]

        # print('-'*100)
        # print(f"[{word_number}] {word_lower}")
        new_radicals = []
        for char in word_lower:
            tree = {char: build_hanzi_tree(char)}
            # print('-'*100)
            # print(tree[word_lower])
            # print('-'*100)
            new_radical = build_string(tree[char], radicals_dict, need_add_node=True)
            new_radicals.append(new_radical)
            # print(new_radical)
            # print_tree(tree[char], radicals_dict, need_print_node=True)
        
        entry["radicals"] = "\n".join(new_radicals)
        # print(entry["radicals"])

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Exported {len(data['words'])} words to {OUTPUT_FILE}")

