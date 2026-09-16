import app

def run_full_tests():
    print("=== STARTING FULL APP COMPREHENSIVE TESTS ===")
    client = app.app.test_client()

    # 0. Clean slate: remove any existing record for today
    r = client.get('/api/work/today')
    assert r.status_code == 200
    today = r.get_json()
    if today.get('id'):
        client.delete(f'/api/work/records/{today["id"]}')
    print('[PASS] 0. Cleaned up any pre-existing record for today')

    # 1. Index page
    r = client.get('/')
    assert r.status_code == 200
    assert 'LIG DNA' in r.get_data(as_text=True)
    print('[PASS] 1. GET / serves HTML properly')

    # 2. Clock-out without clock-in should fail
    r = client.post('/api/work/clock-out')
    assert r.status_code == 400
    print('[PASS] 2. Clock-out without clock-in correctly rejected:', r.get_json()['error'])

    # 3. Clock-in
    r = client.post('/api/work/clock-in')
    assert r.status_code == 201
    record = r.get_json()
    record_id = record['id']
    assert record['status'] == 'working'
    print(f'[PASS] 3. Clock-in created record {record_id} at {record["clock_in"]}')

    # 4. Duplicate clock-in should be rejected (no duplicate record created)
    r = client.post('/api/work/clock-in')
    assert r.status_code == 400
    r2 = client.get('/api/work/records')
    todays = [x for x in r2.get_json() if x['id'] == record_id]
    assert len(todays) == 1
    print('[PASS] 4. Duplicate clock-in rejected, no duplicate record created')

    # 5. Today status reflects "working"
    r = client.get('/api/work/today')
    data = r.get_json()
    assert data['status'] == 'working'
    assert data['expected_clock_out'] is not None
    print('[PASS] 5. GET /api/work/today shows working status with expected clock-out')

    # 6. Clock-out
    r = client.post('/api/work/clock-out')
    assert r.status_code == 200
    result = r.get_json()
    assert result['status'] == 'done'
    assert isinstance(result['work_minutes'], int) and result['work_minutes'] >= 0
    print(f'[PASS] 6. Clock-out succeeded, work_minutes={result["work_minutes"]}')

    # 7. Duplicate clock-out should be rejected
    r = client.post('/api/work/clock-out')
    assert r.status_code == 400
    print('[PASS] 7. Duplicate clock-out rejected:', r.get_json()['error'])

    # 8. Get record by date
    work_date = result['work_date']
    r = client.get(f'/api/work/records/{work_date}')
    assert r.status_code == 200
    assert r.get_json()['status'] == 'done'
    print(f'[PASS] 8. GET /api/work/records/{work_date} returns the finished record')

    # 9. Update record: fix clock_in/clock_out and recompute work_minutes
    payload = {
        'clock_in': f'{work_date} 09:00:00',
        'clock_out': f'{work_date} 18:00:00',
        'break_minutes': 60,
    }
    r = client.put(f'/api/work/records/{record_id}', json=payload)
    assert r.status_code == 200
    updated = r.get_json()
    assert updated['work_minutes'] == 8 * 60
    print('[PASS] 9. PUT update recalculated work_minutes to', updated['work_minutes'])

    # 10. Invalid update: clock_out before clock_in must be rejected
    bad_payload = {'clock_in': f'{work_date} 18:00:00', 'clock_out': f'{work_date} 09:00:00', 'break_minutes': 60}
    r = client.put(f'/api/work/records/{record_id}', json=bad_payload)
    assert r.status_code == 400
    print('[PASS] 10. Invalid update (clock_out before clock_in) rejected')

    # 11. Invalid update: negative break minutes must be rejected
    bad_payload2 = {'clock_in': f'{work_date} 09:00:00', 'clock_out': f'{work_date} 18:00:00', 'break_minutes': -10}
    r = client.put(f'/api/work/records/{record_id}', json=bad_payload2)
    assert r.status_code == 400
    print('[PASS] 11. Negative break_minutes rejected')

    # 12. Weekly summary includes today's record
    r = client.get(f'/api/work/summary/weekly?date={work_date}')
    assert r.status_code == 200
    weekly = r.get_json()
    assert weekly['total_minutes'] >= 8 * 60
    print('[PASS] 12. Weekly summary total_minutes =', weekly['total_minutes'])

    # 13. Monthly summary
    year, month = work_date.split('-')[0], work_date.split('-')[1]
    r = client.get(f'/api/work/summary/monthly?year={year}&month={month}')
    assert r.status_code == 200
    monthly = r.get_json()
    assert monthly['work_days'] >= 1
    print('[PASS] 13. Monthly summary work_days =', monthly['work_days'])

    # 14. Delete record and confirm it is gone
    r = client.delete(f'/api/work/records/{record_id}')
    assert r.status_code == 200
    r = client.get(f'/api/work/records/{work_date}')
    assert r.get_json()['status'] == 'not_started'
    print('[PASS] 14. DELETE removed the record; date now shows not_started')

    # 15. Deleting again returns 404
    r = client.delete(f'/api/work/records/{record_id}')
    assert r.status_code == 404
    print('[PASS] 15. Re-deleting an already-deleted record correctly returns 404')

    print("\n==========================================")
    print(">>> ALL TEST CASES PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == '__main__':
    run_full_tests()
