import app

def run_tests():
    client = app.app.test_client()

    # Test index
    r = client.get('/')
    assert r.status_code == 200, f'Index failed: {r.status_code}'
    print('[OK] GET / returned 200 OK')

    # Clean up any existing record for today so the test is repeatable
    r = client.get('/api/work/today')
    assert r.status_code == 200, f'Today failed: {r.status_code}'
    today = r.get_json()
    if today.get('id'):
        client.delete(f'/api/work/records/{today["id"]}')

    # Test clock-in
    r = client.post('/api/work/clock-in')
    assert r.status_code == 201, f'Clock-in failed: {r.status_code}'
    record = r.get_json()
    record_id = record['id']
    assert record['status'] == 'working'
    print(f'[OK] POST /api/work/clock-in created record {record_id}: {record["clock_in"]}')

    # Duplicate clock-in should be rejected
    r = client.post('/api/work/clock-in')
    assert r.status_code == 400, 'Duplicate clock-in should fail'
    print('[OK] Duplicate clock-in correctly rejected')

    # Test clock-out
    r = client.post('/api/work/clock-out')
    assert r.status_code == 200, f'Clock-out failed: {r.status_code}'
    result = r.get_json()
    assert result['status'] == 'done'
    print(f'[OK] POST /api/work/clock-out: worked {result["work_minutes"]} minutes')

    # Test records list
    r = client.get('/api/work/records')
    assert r.status_code == 200
    records = r.get_json()
    print(f'[OK] GET /api/work/records returned {len(records)} items')

    # Cleanup
    r = client.delete(f'/api/work/records/{record_id}')
    assert r.status_code == 200, f'Delete failed: {r.status_code}'
    print('[OK] DELETE succeeded')

    print('\n[SUCCESS] All backend API verification tests passed with flying colors!')

if __name__ == '__main__':
    run_tests()
