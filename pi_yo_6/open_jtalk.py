import os
from glob import glob

from config import Config

def get_metas() -> list:
    hts_list = [os.path.split(_)[1].replace('.htsvoice','') for _ in glob(f'{Config.OJ.Voice}*.htsvoice')]
    hts_dic = {}
    for hts in hts_list:
        _hts = hts.split('_')
        hts_name = _hts[0]
        if not hts_dic.get(hts_name): hts_dic[hts_name] = []
        hts_dic[hts_name].append(hts)
    return [
        {
            'name':k,
            'styles':[
                {'name': _, 'id': _} for _ in v
            ]
        } for k, v, in hts_dic.items()
    ]