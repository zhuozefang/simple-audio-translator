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
import shutil


# 默认值
DEFAULT_API_KEY = "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"
DEFAULT_CHUNK_LENGTH = 5

# 全局变量
api_key = DEFAULT_API_KEY
chunk_length = DEFAULT_CHUNK_LENGTH

def get_config(filename):
    global api_key, chunk_length
    try:
        with open(filename, 'r') as file:
            config = json.load(file)
        
        # 从配置文件中获取参数值
        api_key = config.get('api_key', DEFAULT_API_KEY)
        chunk_length = config.get('chunk_length', DEFAULT_CHUNK_LENGTH)

    except FileNotFoundError:
        print("配置文件不存在。创建新文件并保存默认值。")
        config = {
            'api_key': DEFAULT_API_KEY,
            'chunk_length': DEFAULT_CHUNK_LENGTH
        }
        with open(filename, 'w') as file:
            json.dump(config, file)

    except json.JSONDecodeError:
        print("配置文件解析错误。使用默认值。")


app = Flask(__name__)

# 设置openai api_key
@app.route('/openai/api_key_set', methods=['POST'])
def api_key_set():
    req = request.get_json()
    api_key = req.get('api_key')
    chunk_length = req.get('chunk_length')
    try:
        with open('./config.json', 'r') as file:
            config = json.load(file)
        
        config['api_key'] = api_key if api_key else config['api_key']
        config['chunk_length'] = int(chunk_length) if chunk_length else config['chunk_length']
        
        with open('./config.json', 'w') as file:
            json.dump(config, file)

        return jsonify({'message': 'Config updated successfully'}), 200

    except FileNotFoundError:
        return jsonify({'message': 'Config file not found'}), 500

    except json.JSONDecodeError:
        return jsonify({'message': 'Error decoding config file'}), 500


# 上传文件
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return 'No file part in the request'

        file = request.files['file']

        if file.filename == '':
            return 'No selected file'
        
        # 获取当前日期
        current_date = date.today().strftime("%Y-%m-%d")

        # 创建上传目录
        common_upload_dir = os.path.join(os.getcwd(), f"common_upload/")
        os.makedirs(common_upload_dir, exist_ok=True)
        os.chmod(common_upload_dir, 0o777)

        
        # 创建以当前日期命名的文件夹
        trans_key = generate_random_string(8)
        folder_path = os.path.join(os.getcwd(), f"audio_{current_date}/{trans_key}/upload/")
        os.makedirs(folder_path, exist_ok=True)
        os.chmod(folder_path, 0o777)
        
        # 保存文件到文件夹中
        file_extension = os.path.splitext(file.filename)[1]
        save_path = os.path.join(folder_path, f"{trans_key}_original{file_extension}")
        common_save_path = os.path.join(common_upload_dir, f"{trans_key}_{file.filename}")
        file.save(save_path)
        file.save(common_save_path)
        
        global global_map
        global_data = load_from_json("./global_map_json")
        if global_data:
            global_map.update(global_data)
        
        global_map[trans_key] = {'Progress': '0.00%', 'file_path': f"{save_path}"}
        save_to_json("./global_map_json", global_map)
        result = {'data': {"trans_key": trans_key}}
        return jsonify(result), 200
    except Exception as e:
    # 捕获并处理函数运行时的错误
        error_message = str(e)
        return jsonify({'error': error_message}), 500   


# 开始音频转换
@app.route('/transcribe/start', methods=['POST'])
def transcribe_start():
    try:
        global global_map, api_key
        openai.api_key = api_key

        req = request.get_json()
        trans_key = req.get('trans_key')
        global_map = load_from_json("./global_map_json")
        if not global_map:
            return "not found"
        if trans_key not in global_map:
            return "not found"
        
        input_file = global_map[trans_key]['file_path']
        progress = {"Progress": "0.00%"}
        global_map[trans_key] = progress
        # input_file = "./Mei-Ling.wav"

        # Create the output directory if it doesn't exist
        current_date = date.today().strftime("%Y-%m-%d")
        output_root_dir = f"./audio_{current_date}"
        os.makedirs(output_root_dir, exist_ok=True)
        os.chmod(output_root_dir, 0o777)

        # partition dir
        partition_dir = f"{output_root_dir}/{trans_key}/partition/"
        os.makedirs(partition_dir, exist_ok=True)
        os.chmod(partition_dir, 0o777)

        # whisper dir
        whisper_dir = f"{output_root_dir}/{trans_key}/whisper/"
        os.makedirs(whisper_dir, exist_ok=True)
        os.chmod(whisper_dir, 0o777)

        # trans dir
        trans_dir = f"{output_root_dir}/{trans_key}/output/"
        os.makedirs(trans_dir, exist_ok=True)
        os.chmod(trans_dir, 0o777)

        file_list = split_audio(input_file, partition_dir)

        progress = {"Progress": "3.00%"}
        global_map[trans_key] = progress

        # transcriber = WhisperTranscriber("base")
        lang = "en"
        out_put_array = []
        for path in file_list:
            #  text = transcriber.whisper_transcribe(path, "Chinese")
            #  print(text)
            # 调用 whisper 命令
            command = ["whisper", path, "--model", "base", "--language", lang, "--output_format", "srt", "--output_dir", whisper_dir]
            subprocess.run(command, capture_output=True, text=False)
            print("Success")
            srt_name = os.path.splitext(os.path.basename(path))[0]
            srt_path = f"{whisper_dir}{srt_name}.srt"
            out_put_array.append(srt_path)

        progress = {"Progress": "5.00%"}
        global_map[trans_key] = progress
        total_len = len(out_put_array)
        for input_path in out_put_array:
            srt_name = os.path.splitext(os.path.basename(input_path))[0]
            output_path = f"{trans_dir}/{srt_name}[translated].srt"
            translate_srt(trans_key, input_path, output_path, total_len)

        return "Job Done", 200
    except Exception as e:
        # 捕获并处理函数运行时的错误
        error_message = str(e)
        return jsonify({'error': error_message}), 500



global_map = {}
# 获取转换进度
@app.route('/transcribe/progress', methods=['GET'])
def transcribe_progress():
    try:
        # trans_key = request.args.get('trans_key')
        # 在这里进行处理和逻辑操作
        global global_map
        # global_map = load_from_json("./global_map_json")
        if not global_map:
            return {'data': {}}
        
        process_list = {}
        for key, value in global_map.items():
            process_list[key] = {"Progress": value['Progress']}

        result = {'data': process_list}
        return jsonify(result)
    except Exception as e:
        # 捕获并处理函数运行时的错误
        error_message = str(e)
        return jsonify({'error': error_message}), 500


# 获取对应转换内容
@app.route('/transcribe/result_content', methods=['POST'])
def transcribe_result():
    try:
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
        srt_path = srt_path.replace('/upload/', '/output/')

        srt_content = ""
        with open(srt_path, 'r', encoding='utf-8') as file:
            srt_content = file.read()

        srt_data = {
            'content': srt_content
        }
        return jsonify(srt_data)
    except Exception as e:
        # 捕获并处理函数运行时的错误
        error_message = str(e)
        return jsonify({'error': error_message}), 500


# 获取上传文件列表
@app.route('/upload_file_list', methods=['GET'])
def upload_file_list():
    try:
        common_upload_dir = os.path.join(os.getcwd(), 'common_upload/')
        os.makedirs(common_upload_dir, exist_ok=True)
        os.chmod(common_upload_dir, 0o777)

        # 获取目录中的所有文件和子目录
        file_list = {}
        sorted_files = get_files_sorted_by_time(common_upload_dir)
        for entry in sorted_files:
            file_name = os.path.basename(entry[0])
            # upload_time = entry[1]
            trans_key = file_name[:8]
            file_name = file_name[9:]
            file_list[trans_key] = file_name

        return jsonify(file_list)
    except Exception as e:
        # 捕获并处理函数运行时的错误
        error_message = str(e)
        return jsonify({'error': error_message}), 500






def get_files_sorted_by_time(directory):
    file_list = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            # 获取文件添加时间： sec
            file_time = os.path.getctime(file_path)
            file_list.append((file_path, file_time))

    sorted_files = sorted(file_list, key=lambda x: x[1])  # 按文件添加时间排序
    return sorted_files


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


#切分成分钟长的音频片段，您可以根据自己音频文件的具体情况进行切分
def split_audio(input_file, output_dir, chunk_length_ms= 5 * 60 * 1000):
    string_array = []
    # Load the audio file
    audio = AudioSegment.from_file(input_file)
    chunk_length_sec = chunk_length_ms / 1000
    file_extension = os.path.splitext(input_file)[1][1:]

    if audio.duration_seconds <= chunk_length_sec :
        partName = os.path.join(output_dir, f"000_{os.path.basename(input_file).split('.')[0]}.{file_extension}")
        string_array.append(partName)
        shutil.copy(input_file, partName)
        return string_array

    chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

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

def translate_srt(trans_key, file_path, output_path, total):
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
        total_progress = ps / total
        progress = {"Progress": f"{total_progress:.2f}%"}
        global_map[trans_key] = progress
        print(f"Progress: {total_progress:.2f}%")

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
    get_config('./config.json')
    app.run()