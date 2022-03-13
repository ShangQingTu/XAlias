import json
import os
from tqdm import tqdm
import requests
import argparse


def check_fout(path):
    if os.path.exists(path):
        os.remove(path)
    fout = open(path, 'a')
    return fout


def restrict_length(_text, max_len=512):
    sentences = _text.split("::;")
    final_text = ""
    total_len = 0
    for sentence in sentences:
        sent_len = len(sentence.split())
        total_len += sent_len
        if total_len > max_len:
            break
        final_text += sentence + ' '
    return final_text.strip()


def parse_xlink_text(text):
    raw_text = ""
    entity_list = []
    state = 0
    ent_id = None
    start_idx = None
    for index, ch in enumerate(text):
        if state == 0:
            if ch == '[':
                state = 1
            else:
                raw_text += ch
        elif ch == '[' and state == 1:
            state = 2
            # start_idx for entity id
            start_idx = index + 1
        elif ch == '|' and state == 2:
            ent_id = text[start_idx:index]
            # start_idx for entity name
            start_idx = index + 1
            state = 3
        elif ch == ']' and state == 3:
            ent_name = text[start_idx:index]
            # entity has id and name
            entity_list.append([ent_id, ent_name])
            raw_text += ent_name
            state = 4
        elif ch == ']' and state == 4:
            state = 0

    return raw_text, entity_list


def get_coref_result(input_json, function="spanBert"):
    if function == "spanBert":
        # Use spanBert API on our server
        data_str = json.dumps(input_json)
        print("input_json is ", data_str)
        r = requests.post("http://103.238.162.32:4414/", data=data_str)
        print("return", r.text)
        quit(0)
        return r.text
    else:
        return input_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_dir', type=str, default='/data/tsq/xlink/bd')
    parser.add_argument('--max_len', type=int, default=256)
    parser.add_argument('--batch_size', type=int, default=8)
    parser.add_argument('--src_text', type=str, default='abstract', help="the input text from wiki")
    parser.add_argument('--function', type=str, default='spanBert', help="the co-reference function")
    args = parser.parse_args()
    src_file_path = os.path.join(args.data_dir, f"standard_{args.src_text}.txt")
    tgt_file_path = os.path.join(args.data_dir, f"coref_{args.src_text}.json")
    fout = check_fout(tgt_file_path)
    with open(src_file_path, 'r') as fin:
        lines = fin.readlines()
        total_num = len(lines)
        batch = []
        entity_lists = []
        for line in tqdm(lines, total=total_num):
            id_and_txt = line.split('\t\t')
            _id = id_and_txt[0]
            # spanBert has a length limit
            _text = restrict_length(id_and_txt[1], args.max_len)
            raw_text, entity_list = parse_xlink_text(_text)
            coref_input_json = {"ID": _id, "Text": raw_text}
            batch.append(coref_input_json)
            entity_lists.append(entity_list)
            # output
            if len(batch) == args.batch_size:
                coref_result_json_str = get_coref_result(batch, args.function)
                coref_result_json = json.loads(coref_result_json_str)[0]
                for i, _coref_result_json in enumerate(coref_result_json):
                    _coref_result_json["entity_list"] = entity_lists[i]
                    _coref_result_json["speakers"] = []
                    # write to json
                    fout.write(json.dumps(_coref_result_json))
                    fout.write("\n")
                # init
                batch = []
                entity_lists = []


if __name__ == '__main__':
    main()
