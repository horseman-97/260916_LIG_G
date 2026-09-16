import app

def run_tests():
    client = app.app.test_client()

    # Test index
    r = client.get('/')
    assert r.status_code == 200, f'Index failed: {r.status_code}'
    print('[OK] GET / returned 200 OK')

    # Test stats
    r = client.get('/api/stats')
    assert r.status_code == 200, f'Stats failed: {r.status_code}'
    stats = r.get_json()
    print('[OK] GET /api/stats:', stats)

    # Test todos
    r = client.get('/api/todos')
    assert r.status_code == 200, f'Todos failed: {r.status_code}'
    todos = r.get_json()
    print(f'[OK] GET /api/todos returned {len(todos)} items')

    # Test create
    r = client.post('/api/todos', json={
        'title': '자동 검증 투두 테스트',
        'description': '테스트 설명 내용',
        'category': 'DNA 과제',
        'priority': '높음',
        'due_date': '2026-09-30'
    })
    assert r.status_code == 201, f'Create failed: {r.status_code}'
    new_todo = r.get_json()
    new_id = new_todo['id']
    print(f'[OK] POST /api/todos created ID {new_id}: {new_todo["title"]}')

    # Test toggle
    r = client.patch(f'/api/todos/{new_id}/toggle')
    assert r.status_code == 200, f'Toggle failed: {r.status_code}'
    assert r.get_json()['completed'] == 1, 'Completed status should be 1'
    print('[OK] PATCH toggle completed = 1')

    # Test update
    r = client.put(f'/api/todos/{new_id}', json={
        'title': '수정된 투두 제목',
        'description': '수정된 내용',
        'category': '업무/프로젝트',
        'priority': '보통',
        'due_date': '2026-10-01'
    })
    assert r.status_code == 200, f'Update failed: {r.status_code}'
    assert r.get_json()['title'] == '수정된 투두 제목', 'Title should be updated'
    print('[OK] PUT update succeeded')

    # Test delete
    r = client.delete(f'/api/todos/{new_id}')
    assert r.status_code == 200, f'Delete failed: {r.status_code}'
    print('[OK] DELETE succeeded')

    print('\n[SUCCESS] All backend API verification tests passed with flying colors!')

if __name__ == '__main__':
    run_tests()
