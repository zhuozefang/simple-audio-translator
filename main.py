import whisper
import openai
from datetime import date
import subprocess
from flask import Flask, request, jsonify, json
import pysrt
import random
import string

from pydub import AudioSegment
import os
openai.api_key = "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"

app = Flask(__name__)
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part in the request'

    file = request.files['file']

    if file.filename == '':
        return 'No selected file'
    
    # 获取当前日期
    current_date = date.today().strftime("%Y-%m-%d")
    
    # 创建以当前日期命名的文件夹
    trans_key = generate_random_string(8)
    folder_path = os.path.join(os.getcwd(), f"upload_{current_date}/{trans_key}")
    os.makedirs(folder_path, exist_ok=True)
    
    # 保存文件到文件夹中
    file_extension = os.path.splitext(file.filename)[1]
    save_path = os.path.join(folder_path, f"{trans_key}_original{file_extension}")
    file.save(save_path)
    
    global global_map
    global_data = load_from_json("./global_map_json")
    if global_data:
        global_map.update(global_data)
    
    global_map[trans_key] = {'Progress': '0.00%', 'file_path': f"{save_path}"}
    save_to_json("./global_map_json", global_map)
    result = {'data': {"trans_key": trans_key}}
    return jsonify(result)
    #return 'File uploaded successfully'

@app.route('/transcribe/start', methods=['POST'])
def transcribe_start():
    req = request.get_json()
    trans_key = req.get('trans_key')
    global_map = load_from_json("./global_map_json")
    if not global_map:
        return "not found"
    if trans_key not in global_map:
        return "not found"

    global_map[trans_key]['Progress'] = f"Progress: 0.00%"
    input_file = global_map[trans_key]['file_path']

    # Create the output directory if it doesn't exist
    current_date = date.today().strftime("%Y-%m-%d")
    output_root_dir = f"./media_{current_date}"
    os.makedirs(output_root_dir, exist_ok=True)
    os.chmod(output_root_dir, 0o777)

    # partition dir
    partition_dir = f"{output_root_dir}/partition/"
    os.makedirs(partition_dir, exist_ok=True)
    os.chmod(partition_dir, 0o777)

    # output dir
    output_dir = f"{output_root_dir}/output/"
    os.makedirs(output_dir, exist_ok=True)
    os.chmod(output_dir, 0o777)

    file_list = split_audio(input_file, partition_dir)

    progress = {"Progress": f"Progress: 3.00%"}
    global_map[trans_key] = progress

    lang = "en"
    out_put_array = []
    for path in file_list:
        # 调用 whisper 命令
        command = ["whisper", path, "--model", "base", "--language", lang, "--output_format", "srt", "--output_dir", output_dir]
        subprocess.run(command, capture_output=True, text=False)
        print("Success")
        srt_name = os.path.splitext(os.path.basename(path))[0]
        srt_path = f"{output_dir}{srt_name}.srt"
        out_put_array.append(srt_path)

    progress = {"Progress": f"Progress: 5.00%"}
    global_map[trans_key] = progress
    for input_path in out_put_array:
        srt_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f"./{srt_name}[translated].srt"
        translate_srt(trans_key, input_path, output_path)

    return "Job Done"


global_map = {}
@app.route('/transcribe/progress', methods=['GET'])
def transcribe_progress():
    trans_key = request.args.get('trans_key')
    # 在这里进行处理和逻辑操作
    # print(global_map)
    result = {'data': global_map}
    return jsonify(result)

    # return jsonify(global_map)
    if trans_key in global_map:
        trans_progress = global_map[trans_key]
        inner_data = {'message': trans_progress} if trans_progress else {'message': '0%'}
        result = {'data': inner_data}
        return jsonify(result)
    
    inner_data = {'message': 'not found'}
    result = {'data': inner_data}
    return jsonify(result)


@app.route('/transcribe/result_content', methods=['POST'])
def transcribe_result():
    req = request.get_json()
    trans_key = req.get('trans_key')
    global_map = load_from_json("./global_map_json")
    if not global_map:
        return "not found"
    if trans_key not in global_map:
        return "not found"
    
    input_file = global_map[trans_key]['file_path']
    old_name = os.path.basename(input_file)
    srt_path = input_file.replace(old_name, f"000_{trans_key}_original[translated].srt")

    srt_content = ""
    with open(srt_path, 'r', encoding='utf-8') as file:
        srt_content = file.read()

    srt_data = {
        'content': srt_content
    }
    return jsonify(srt_data)


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


#切分成2分钟长的音频片段，您可以根据自己音频文件的具体情况进行切分
def split_audio(input_file, output_dir, chunk_length_ms= 2 * 60 * 1000):
    # Load the audio file
    audio = AudioSegment.from_file(input_file)
    chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_extension = os.path.splitext(input_file)[1][1:]
    string_array = []
    for i, chunk in enumerate(chunks):
        partName = os.path.join(output_dir, f"{i:03d}_{os.path.basename(input_file).split('.')[0]}.{file_extension}")
        chunk.export(partName, format=f"{file_extension}")
        string_array.append(partName)
    
    return string_array



def read_srt(file_path):
    subs = pysrt.open(file_path)
    return subs

def translate_text(text):
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=f"Translate the following English text to Chinese(simplified): '{text}'",
        max_tokens=60,
        n=1,
        stop=None,
        temperature=0.5,
    )

    translated_text = response.choices[0].text.strip()
    return translated_text

def write_srt(subs, translated_subs, output_path):
    for i in range(len(subs)):
        subs[i].text = f"{subs[i].text}\n{translated_subs[i].text}"
    subs.save(output_path, encoding="utf-8")

def translate_srt(trans_key, file_path, output_path):
    global global_map
    subs = read_srt(file_path)
    translated_subs = []

    total_subs = len(subs)
    for i, sub in enumerate(subs):
        translated_text = translate_text(sub.text)
        translated_sub = pysrt.SubRipItem(index=sub.index, start=sub.start, end=sub.end, text=translated_text)
        translated_subs.append(translated_sub)

        # Set progress
        ps = (i + 1) / total_subs * 100
        progress = {"Progress": f"Progress: {ps:.2f}%"}
        global_map[trans_key] = progress
        print(f"Progress: {ps:.2f}%")

    write_srt(subs, translated_subs, output_path)

# 将global_map保存到JSON文件
def save_to_json(file_path, data):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file)

# 从JSON文件读取数据
def load_from_json(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            if not data:
                data = ""
    except FileNotFoundError:
        data = ""
    return data




if __name__ == '__main__':
    app.run()