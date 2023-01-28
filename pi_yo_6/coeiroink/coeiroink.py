import json

from glob import glob
from typing import List
from pathlib import Path

def get_metas_dict() -> List[dict]:
    paths: List[str] = sorted(glob(str(Path(__file__).parent) + '/speaker_info/**/'))

    speaker_infos = []
    for path in paths:
        with open(path + 'metas.json', encoding='utf-8') as f:
            meta = json.load(f)
        styles = [{'name': s['styleName'], 'id': s['styleId']} for s in meta['styles']]
        version = meta['version'] if 'version' in meta.keys() else '0.0.1'
        speaker_info = {
            'name': meta['speakerName'],
            'speaker_uuid': meta['speakerUuid'],
            'styles': styles,
            'version': version
        }
        speaker_infos.append(speaker_info)

    speaker_infos = sorted(speaker_infos, key=lambda x: x['styles'][0]['id'])
    return speaker_infos