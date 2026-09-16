import app
import json

def run_full_tests():
    print("=== STARTING FULL APP COMPREHENSIVE TESTS ===")
    client = app.app.test_client()

    # 1. Test Index Page
    r = client.get('/')
    assert r.status_code == 200
    assert 'LIG DNA 스마트 투두' in r.get_data(as_text=True)
    print('[PASS] 1. GET / serves HTML properly')

    # 2. Test Stats API
    r = client.get('/api/stats')
    assert r.status_code == 200
    stats = r.get_json()
    assert 'total' in stats and 'completed' in stats and 'active' in stats and 'rate' in stats
    print('[PASS] 2. GET /api/stats returns valid schema:', stats)

    # 3. Test Todos List with Filters
    r = client.get('/api/todos')
    assert r.status_code == 200
    all_todos = r.get_json()
    print(f'[PASS] 3-1. GET /api/todos returns {len(all_todos)} items')

    r = client.get('/api/todos?status=active')
    assert r.status_code == 200
    active_todos = r.get_json()
    assert all(t['completed'] == 0 for t in active_todos)
    print(f'[PASS] 3-2. GET /api/todos?status=active returns {len(active_todos)} items')

    r = client.get('/api/todos?status=completed')
    assert r.status_code == 200
    completed_todos = r.get_json()
    assert all(t['completed'] == 1 for t in completed_todos)
    print(f'[PASS] 3-3. GET /api/todos?status=completed returns {len(completed_todos)} items')

    r = client.get('/api/todos?category=DNA 과제')
    assert r.status_code == 200
    dna_todos = r.get_json()
    assert all(t['category'] == 'DNA 과제' for t in dna_todos)
    print(f'[PASS] 3-4. GET /api/todos?category=DNA 과제 returns {len(dna_todos)} items')

    r = client.get('/api/todos?priority=높음')
    assert r.status_code == 200
    high_todos = r.get_json()
    assert all(t['priority'] == '높음' for t in high_todos)
    print(f'[PASS] 3-5. GET /api/todos?priority=높음 returns {len(high_todos)} items')

    r = client.get('/api/todos?sort_by=due_date')
    assert r.status_code == 200
    print('[PASS] 3-6. GET /api/todos?sort_by=due_date works')

    r = client.get('/api/todos?sort_by=priority')
    assert r.status_code == 200
    print('[PASS] 3-7. GET /api/todos?sort_by=priority works')

    # 4. Test CRUD Lifecycle
    # 4-1. Create
    new_payload = {
        'title': '통합 테스트 투두 항목',
        'description': '상세 내용 검증용',
        'category': 'DNA 과제',
        'priority': '높음',
        'due_date': '2026-12-31'
    }
    r = client.post('/api/todos', json=new_payload)
    assert r.status_code == 201
    created_item = r.get_json()
    item_id = created_item['id']
    assert created_item['title'] == new_payload['title']
    assert created_item['completed'] == 0
    print(f'[PASS] 4-1. POST /api/todos created ID {item_id}')

    # 4-2. Create with empty title (Validation check)
    r = client.post('/api/todos', json={'title': '   '})
    assert r.status_code == 400
    print('[PASS] 4-2. POST /api/todos validates empty title (400 Bad Request)')

    # 4-3. Single Get
    r = client.get(f'/api/todos/{item_id}')
    assert r.status_code == 200
    assert r.get_json()['id'] == item_id
    print(f'[PASS] 4-3. GET /api/todos/{item_id} retrieves item')

    # 4-4. Toggle Complete
    r = client.patch(f'/api/todos/{item_id}/toggle')
    assert r.status_code == 200
    assert r.get_json()['completed'] == 1
    assert r.get_json()['completed_at'] is not None
    print(f'[PASS] 4-4. PATCH /api/todos/{item_id}/toggle marked completed')

    # 4-5. Toggle back to Incomplete
    r = client.patch(f'/api/todos/{item_id}/toggle')
    assert r.status_code == 200
    assert r.get_json()['completed'] == 0
    assert r.get_json()['completed_at'] is None
    print(f'[PASS] 4-5. PATCH /api/todos/{item_id}/toggle marked uncompleted')

    # 4-6. Update
    updated_payload = {
        'title': '수정 완료된 투두 제목',
        'description': '새로운 설명',
        'category': '회의/미팅',
        'priority': '낮음',
        'due_date': '2026-11-20'
    }
    r = client.put(f'/api/todos/{item_id}', json=updated_payload)
    assert r.status_code == 200
    updated_item = r.get_json()
    assert updated_item['title'] == '수정 완료된 투두 제목'
    assert updated_item['category'] == '회의/미팅'
    print(f'[PASS] 4-6. PUT /api/todos/{item_id} updated item')

    # 4-7. Update identical data test
    r = client.put(f'/api/todos/{item_id}', json=updated_payload)
    assert r.status_code == 200
    print(f'[PASS] 4-7. PUT with identical data handled properly: {r.status_code}')

    # 4-8. Delete item
    r = client.delete(f'/api/todos/{item_id}')
    assert r.status_code == 200
    print(f'[PASS] 4-8. DELETE /api/todos/{item_id} deleted item')

    # 4-9. Check 404 on deleted item
    r = client.get(f'/api/todos/{item_id}')
    assert r.status_code == 404
    print(f'[PASS] 4-9. GET deleted item correctly returns 404')

    # 5. Test Clear Completed
    # Create a temp item and complete it
    r = client.post('/api/todos', json={'title': '삭제 대상 완료 항목'})
    temp_id = r.get_json()['id']
    client.patch(f'/api/todos/{temp_id}/toggle')
    r = client.post('/api/todos/clear-completed')
    assert r.status_code == 200
    clear_res = r.get_json()
    assert clear_res['success'] is True
    print(f'[PASS] 5. POST /api/todos/clear-completed cleaned {clear_res["deleted_count"]} items')

    print("\n==========================================")
    print(">>> ALL 17 TEST CASES PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == '__main__':
    run_full_tests()
