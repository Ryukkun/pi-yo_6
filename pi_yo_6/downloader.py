import tarfile
import zipfile
import requests
import tempfile
import re
import os

from pathlib import Path
from tqdm import tqdm

def download(url, out_dir, out_file:str = ''):
    file_name = re.search(r'/[^/]+?$', url).group().replace('/','')
    if not out_file:
        out_file = Path(out_dir) / file_name
    r = requests.get(url, stream=True)
    total_size = int(r.headers.get('content-length', 0))
    chunk_size = 8 * 1024

    pbar = tqdm(total=total_size, unit='B', unit_scale=True)
    with open(out_file, 'wb') as f:
        for data in r.iter_content(chunk_size):
            f.write(data)
            pbar.update(chunk_size)
    pbar.close()
    return out_file
        


def download_tar(url, out_dir, out_file:str =''):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        out_dir = Path(out_dir)
        tar_file = download(url, temp_dir)
        # 展開
        with tarfile.open(tar_file, 'r:gz')as tar:
            tar.extractall(path=temp_dir)
            extracted_name = tar.getnames()[0]
            befor_name = temp_dir / extracted_name
            after_name = out_dir / extracted_name
            if out_file:
                after_name = out_dir / out_file
            os.rename(befor_name, after_name)



def download_zip(url, out_dir, out_file:str =''):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        out_dir = Path(out_dir)
        zip_file = download(url, temp_dir)
        # 展開
        with zipfile.ZipFile(zip_file)as zf:
            zf.extractall(path=temp_dir)
            extracted_name = zf.namelist()[0]
            befor_name = temp_dir / extracted_name
            after_name = out_dir / extracted_name
            if out_file:
                after_name = out_dir / out_file
            os.rename(befor_name, after_name)



if __name__ == '__main__':
    url = 'https://jaist.dl.sourceforge.net/project/open-jtalk/Dictionary/open_jtalk_dic-1.11/open_jtalk_dic_utf_8-1.11.tar.gz'
    dir = Path(__file__).parent
    print(dir)
    download_tar(url, dir)