import requests
import time
import json

API = 'http://127.0.0.1:8000/api'

def run():
    print('Starting E2E Test...')
    # 1. Ingest
    with open('test_data.csv', 'w') as f:
        f.write('smiles,endpoint_val,endpoint_cat\nCCO,1.2,Active\nCCN,0.8,Inactive\n')
    
    with open('test_data.csv', 'rb') as f:
        res = requests.post(f'{API}/ingest', files={'file': ('test_data.csv', f)})
        
    assert res.status_code == 200, res.text
    data = res.json()
    print('Ingest OK:', data['parquet_path'])
    filepath = data['parquet_path']
    
    # 2. Mapping & Segregation
    mappings = {'smiles': 'smiles', 'endpoint': 'endpoint_cat', 'value': 'endpoint_val'}
    res = requests.post(f'{API}/mapping', json={'filepath': filepath, 'mappings': mappings})
    assert res.status_code == 200, res.text
    
    res = requests.post(f'{API}/segregate', json={'filepath': filepath, 'mappings': mappings})
    assert res.status_code == 200, res.text
    print('Segregation OK:', res.json()['statistics'])
    
    # 3. Enrichment
    payload = {
        'filepath': filepath,
        'mappings': mappings,
        'selected_descriptors': [],
        'include_mordred': False,
        'mode': 'fast'
    }
    res = requests.post(f'{API}/jobs/enrich', json=payload)
    assert res.status_code == 200, res.text
    job_id = res.json()['job_id']
    print('Enrichment Dispatch OK:', job_id)
    
    # 4. Poll
    while True:
        status = requests.get(f'{API}/jobs/{job_id}/status').json()
        print('Status:', status['status'], f"({status.get('progress_pct', 0)}%)")
        if status['status'] == 'COMPLETED':
            break
        if status['status'] in ('FAILED', 'CANCELLED'):
            print('Job Failed!', status)
            return
        time.sleep(1)
        
    # 5. Result
    res = requests.get(f'{API}/jobs/{job_id}/result').json()
    print('Enrichment Result OK, rows:', res['total_rows'], 'cols:', len(res['columns']))
    result_path = res['parquet_path']
    
    # 6. Readiness
    res = requests.post(f'{API}/readiness', json={'filepath': result_path, 'mappings': mappings})
    assert res.status_code == 200, res.text
    audit = res.json()
    print('Readiness OK, Tier:', audit['tier'], 'Score:', audit['score'])

if __name__ == '__main__':
    run()
