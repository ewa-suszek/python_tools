import os.path
import sys
import gzip
import json
import pickle

def convert_cache():
    app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    cache_path = os.path.join(app_path, '_cache')
    cache_files_list = os.listdir(cache_path)
    cache_files_list_size = len(cache_files_list)
    for i in range(0,cache_files_list_size):
        cache_file_name = cache_files_list[i]
        if cache_file_name.find('_full_info.cache') > 0 and cache_file_name.find('gtax_') > -1 :
            print(f'progress:{round(i/cache_files_list_size*100,2)}%   converting {cache_file_name}                  ', end='\r', flush=True)
            convert_pickle(cache_path, cache_file_name)

def convert_pickle(cache_path, cache_file_name):
    cache_file = os.path.join(cache_path, cache_file_name)
    cache_move_path = os.path.join(cache_path, 'uncompressed')
    cache_file_move = os.path.join(cache_move_path, cache_file_name)
    gzip_file = os.path.join(cache_path, cache_file_name[:-5] + 'gzip')
    if os.path.isfile(cache_file):
        with open(cache_file, 'rb') as cache:
            cache_data = pickle.load(cache)
    with gzip.open(gzip_file, 'w') as f:
        f.write(json.dumps(cache_data).encode('utf-8')) 
    if not os.path.exists(cache_move_path):
        os.makedirs(cache_move_path)
    os.rename(cache_file, cache_file_move)

def cache_json_save(data, gzip_file_name):
    with gzip.open(gzip_file_name, 'w') as f:
        f.write(json.dumps(data).encode('utf-8')) 
    return 0

def cache_json_load(gzip_file_name):
    with gzip.open(gzip_file_name, 'r') as f:
        data = json.loads(f.read().decode('utf-8'))
    return data

if __name__ == '__main__':
    convert_cache()
