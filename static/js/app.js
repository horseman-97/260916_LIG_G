/**
 * LIG DNA Smart Todo App - Interactive Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // Current Filter & Sort State
    const state = {
        status: 'all',
        category: 'all',
        search: '',
        sortBy: 'created_desc',
        todos: []
    };

    // DOM Elements
    const todoList = document.getElementById('todoList');
    const emptyState = document.getElementById('emptyState');
    const visibleCount = document.getElementById('visibleCount');
    const searchInput = document.getElementById('searchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const statusTabs = document.getElementById('statusTabs');
    const categoryPills = document.getElementById('categoryPills');
    const sortBySelect = document.getElementById('sortBySelect');
    const clearCompletedBtn = document.getElementById('clearCompletedBtn');

    // Stats Elements
    const statTotal = document.getElementById('statTotal');
    const statActive = document.getElementById('statActive');
    const statCompleted = document.getElementById('statCompleted');
    const statDueToday = document.getElementById('statDueToday');
    const statRate = document.getElementById('statRate');
    const progressBarFill = document.getElementById('progressBarFill');
    const progressMessage = document.getElementById('progressMessage');
    const currentDateText = document.getElementById('currentDateText');

    // Modals
    const addModalOverlay = document.getElementById('addModalOverlay');
    const openAddModalBtn = document.getElementById('openAddModalBtn');
    const closeAddModalBtn = document.getElementById('closeAddModalBtn');
    const cancelAddBtn = document.getElementById('cancelAddBtn');
    const detailedAddForm = document.getElementById('detailedAddForm');
    const emptyAddBtn = document.getElementById('emptyAddBtn');

    const editModalOverlay = document.getElementById('editModalOverlay');
    const closeEditModalBtn = document.getElementById('closeEditModalBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const editForm = document.getElementById('editForm');

    // Quick Add Form
    const quickAddForm = document.getElementById('quickAddForm');
    const quickTitleInput = document.getElementById('quickTitleInput');
    const quickCategorySelect = document.getElementById('quickCategorySelect');
    const quickPrioritySelect = document.getElementById('quickPrioritySelect');
    const quickDueDateInput = document.getElementById('quickDueDateInput');

    // 1. Initialize Date & Current Time
    function initDateDisplay() {
        const now = new Date();
        const days = ['일', '월', '화', '수', '목', '금', '토'];
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const date = String(now.getDate()).padStart(2, '0');
        const dayName = days[now.getDay()];
        currentDateText.textContent = `${year}년 ${month}월 ${date}일 (${dayName})`;

        // Set default date picker values to today
        const todayIso = now.toISOString().split('T')[0];
        quickDueDateInput.value = todayIso;
    }

    // 2. Fetch Stats from Backend
    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) throw new Error('Failed to fetch stats');
            const data = await res.json();

            statTotal.textContent = data.total;
            statActive.textContent = data.active;
            statCompleted.textContent = data.completed;
            statDueToday.textContent = data.due_today;
            statRate.textContent = `${data.rate}%`;
            progressBarFill.style.width = `${data.rate}%`;

            if (data.rate === 100 && data.total > 0) {
                progressMessage.textContent = '🎉 모든 할 일을 완수했습니다! 멋진 하루입니다!';
            } else if (data.rate >= 50) {
                progressMessage.textContent = '🔥 절반 이상 달성! 조금만 더 힘내세요!';
            } else {
                progressMessage.textContent = '오늘의 과제를 차근차근 해결해보세요.';
            }
        } catch (err) {
            console.error('Error fetching stats:', err);
        }
    }

    // 3. Fetch Todos from Backend
    async function fetchTodos() {
        try {
            const params = new URLSearchParams({
                status: state.status,
                category: state.category,
                search: state.search,
                sort_by: state.sortBy
            });

            const res = await fetch(`/api/todos?${params.toString()}`);
            if (!res.ok) throw new Error('Failed to fetch todos');
            const todos = await res.json();
            state.todos = todos;

            renderTodos(todos);
            fetchStats();
        } catch (err) {
            console.error('Error fetching todos:', err);
            showToast('할 일 목록을 불러오지 못했습니다.', 'error');
        }
    }

    // 4. Render Todos
    function renderTodos(todos) {
        todoList.innerHTML = '';
        visibleCount.textContent = todos.length;

        if (todos.length === 0) {
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';

        todos.forEach(todo => {
            const card = document.createElement('div');
            const priorityClass = todo.priority === '높음' ? 'priority-high' :
                                  todo.priority === '보통' ? 'priority-medium' : 'priority-low';
            
            card.className = `todo-card ${priorityClass} ${todo.completed ? 'completed' : ''}`;
            card.dataset.id = todo.id;

            // Category tag style
            let catClass = 'other';
            if (todo.category.includes('DNA')) catClass = 'dna';
            else if (todo.category.includes('업무')) catClass = 'work';
            else if (todo.category.includes('자기계발')) catClass = 'personal';
            else if (todo.category.includes('회의')) catClass = 'meeting';

            // Due Date Badge calculation
            let dueBadgeHtml = '';
            if (todo.due_date) {
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                const due = new Date(todo.due_date);
                due.setHours(0, 0, 0, 0);

                const diffDays = Math.round((due - today) / (1000 * 60 * 60 * 24));
                let dueClass = 'upcoming';
                let dueLabel = todo.due_date;

                if (!todo.completed) {
                    if (diffDays < 0) {
                        dueClass = 'overdue';
                        dueLabel = `기한초과 (${Math.abs(diffDays)}일 지남)`;
                    } else if (diffDays === 0) {
                        dueClass = 'today';
                        dueLabel = '오늘 마감';
                    } else if (diffDays === 1) {
                        dueClass = 'today';
                        dueLabel = '내일 마감 (D-1)';
                    } else {
                        dueLabel = `D-${diffDays} (${todo.due_date})`;
                    }
                }

                dueBadgeHtml = `<span class="due-badge ${dueClass}">📅 ${dueLabel}</span>`;
            }

            // Priority badge
            const priorityBadgeClass = todo.priority === '높음' ? 'high' :
                                       todo.priority === '보통' ? 'medium' : 'low';

            card.innerHTML = `
                <div class="todo-checkbox-container">
                    <input 
                        type="checkbox" 
                        class="todo-checkbox" 
                        ${todo.completed ? 'checked' : ''} 
                        aria-label="완료 여부 변경"
                    >
                </div>
                <div class="todo-main-content">
                    <div class="todo-meta">
                        <span class="category-tag ${catClass}">${escapeHtml(todo.category)}</span>
                        <span class="priority-badge ${priorityBadgeClass}">우선순위: ${escapeHtml(todo.priority)}</span>
                        ${dueBadgeHtml}
                    </div>
                    <h3 class="todo-title">${escapeHtml(todo.title)}</h3>
                    ${todo.description ? `<p class="todo-desc">${escapeHtml(todo.description)}</p>` : ''}
                </div>
                <div class="todo-actions">
                    <button class="action-btn btn-edit" title="수정" aria-label="수정">✏️</button>
                    <button class="action-btn btn-delete" title="삭제" aria-label="삭제">🗑️</button>
                </div>
            `;

            // Event Listeners for Card Items
            const checkbox = card.querySelector('.todo-checkbox');
            checkbox.addEventListener('change', () => toggleTodo(todo.id, checkbox));

            const editBtn = card.querySelector('.btn-edit');
            editBtn.addEventListener('click', () => openEditModal(todo));

            const deleteBtn = card.querySelector('.btn-delete');
            deleteBtn.addEventListener('click', () => deleteTodo(todo.id, card));

            todoList.appendChild(card);
        });
    }

    // 5. Toggle Todo Status
    async function toggleTodo(id, checkbox) {
        try {
            const res = await fetch(`/api/todos/${id}/toggle`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!res.ok) throw new Error('Toggle failed');
            const updated = await res.json();

            // Find card & apply completion styling
            const card = document.querySelector(`.todo-card[data-id="${id}"]`);
            if (card) {
                if (updated.completed) {
                    card.classList.add('completed');
                    triggerConfetti();
                    showToast('🎉 할 일을 완료했습니다!', 'success');
                } else {
                    card.classList.remove('completed');
                    showToast('할 일을 진행 중으로 변경했습니다.', 'info');
                }
            }

            fetchStats();
        } catch (err) {
            console.error('Toggle error:', err);
            checkbox.checked = !checkbox.checked;
            showToast('상태 변경에 실패했습니다.', 'error');
        }
    }

    // 6. Delete Todo
    async function deleteTodo(id, cardElement) {
        if (!confirm('이 할 일을 삭제하시겠습니까?')) return;

        try {
            const res = await fetch(`/api/todos/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Delete failed');

            cardElement.style.transition = 'all 0.25s ease';
            cardElement.style.opacity = '0';
            cardElement.style.transform = 'scale(0.9)';

            setTimeout(() => {
                fetchTodos();
            }, 250);

            showToast('할 일이 삭제되었습니다.', 'info');
        } catch (err) {
            console.error('Delete error:', err);
            showToast('삭제 중 오류가 발생했습니다.', 'error');
        }
    }

    // 7. Clear All Completed
    clearCompletedBtn.addEventListener('click', async () => {
        if (!confirm('완료된 모든 할 일을 정리(삭제)하시겠습니까?')) return;

        try {
            const res = await fetch('/api/todos/clear-completed', { method: 'POST' });
            if (!res.ok) throw new Error('Clear completed failed');
            const result = await res.json();

            showToast(`${result.deleted_count}개의 완료된 항목을 정리했습니다.`, 'success');
            fetchTodos();
        } catch (err) {
            console.error('Clear error:', err);
            showToast('완료 항목 정리에 실패했습니다.', 'error');
        }
    });

    // 8. Quick Add Handler
    quickAddForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = quickTitleInput.value.trim();
        if (!title) return;

        const payload = {
            title: title,
            description: '',
            category: quickCategorySelect.value,
            priority: quickPrioritySelect.value,
            due_date: quickDueDateInput.value
        };

        try {
            const res = await fetch('/api/todos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error('Create failed');
            quickTitleInput.value = '';
            showToast('새 할 일이 추가되었습니다!', 'success');
            fetchTodos();
        } catch (err) {
            console.error('Quick add error:', err);
            showToast('할 일 추가에 실패했습니다.', 'error');
        }
    });

    // 9. Detailed Add Modal
    function openAddModal() {
        detailedAddForm.reset();
        const todayIso = new Date().toISOString().split('T')[0];
        document.getElementById('modalAddDueDate').value = todayIso;
        addModalOverlay.classList.add('active');
        document.getElementById('modalAddTitle').focus();
    }

    function closeAddModal() {
        addModalOverlay.classList.remove('active');
    }

    openAddModalBtn.addEventListener('click', openAddModal);
    closeAddModalBtn.addEventListener('click', closeAddModal);
    cancelAddBtn.addEventListener('click', closeAddModal);
    emptyAddBtn.addEventListener('click', openAddModal);

    detailedAddForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = document.getElementById('modalAddTitle').value.trim();
        if (!title) return;

        const payload = {
            title: title,
            description: document.getElementById('modalAddDesc').value.trim(),
            category: document.getElementById('modalAddCategory').value,
            priority: document.getElementById('modalAddPriority').value,
            due_date: document.getElementById('modalAddDueDate').value
        };

        try {
            const res = await fetch('/api/todos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error('Create failed');
            closeAddModal();
            showToast('새 할 일이 등록되었습니다.', 'success');
            fetchTodos();
        } catch (err) {
            console.error('Add modal error:', err);
            showToast('등록 중 오류가 발생했습니다.', 'error');
        }
    });

    // 10. Edit Modal
    function openEditModal(todo) {
        document.getElementById('editTodoId').value = todo.id;
        document.getElementById('editTitle').value = todo.title;
        document.getElementById('editDesc').value = todo.description || '';
        document.getElementById('editCategory').value = todo.category;
        document.getElementById('editPriority').value = todo.priority;
        document.getElementById('editDueDate').value = todo.due_date || '';

        editModalOverlay.classList.add('active');
        document.getElementById('editTitle').focus();
    }

    function closeEditModal() {
        editModalOverlay.classList.remove('active');
    }

    closeEditModalBtn.addEventListener('click', closeEditModal);
    cancelEditBtn.addEventListener('click', closeEditModal);

    editForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('editTodoId').value;
        const title = document.getElementById('editTitle').value.trim();
        if (!title) return;

        const payload = {
            title: title,
            description: document.getElementById('editDesc').value.trim(),
            category: document.getElementById('editCategory').value,
            priority: document.getElementById('editPriority').value,
            due_date: document.getElementById('editDueDate').value
        };

        try {
            const res = await fetch(`/api/todos/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error('Update failed');
            closeEditModal();
            showToast('할 일이 수정되었습니다.', 'success');
            fetchTodos();
        } catch (err) {
            console.error('Update error:', err);
            showToast('수정 중 오류가 발생했습니다.', 'error');
        }
    });

    // Close Modals on Backdrop Click or ESC Key
    [addModalOverlay, editModalOverlay].forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            addModalOverlay.classList.remove('active');
            editModalOverlay.classList.remove('active');
        }
    });

    // 11. Search & Filters Event Listeners
    let searchDebounce = null;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchDebounce);
        const val = e.target.value;
        clearSearchBtn.style.display = val ? 'block' : 'none';

        searchDebounce = setTimeout(() => {
            state.search = val;
            fetchTodos();
        }, 200);
    });

    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        state.search = '';
        clearSearchBtn.style.display = 'none';
        fetchTodos();
    });

    // Status Tabs
    statusTabs.addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-btn');
        if (!btn) return;

        statusTabs.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        state.status = btn.dataset.status;
        fetchTodos();
    });

    // Category Pills
    categoryPills.addEventListener('click', (e) => {
        const pill = e.target.closest('.pill-btn');
        if (!pill) return;

        categoryPills.querySelectorAll('.pill-btn').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');

        state.category = pill.dataset.category;
        fetchTodos();
    });

    // Sort By
    sortBySelect.addEventListener('change', (e) => {
        state.sortBy = e.target.value;
        fetchTodos();
    });

    // Click Stat Card to Filter Status
    document.querySelectorAll('.stat-card[data-filter-status]').forEach(card => {
        card.addEventListener('click', () => {
            const filterStatus = card.dataset.filterStatus;
            const targetTab = statusTabs.querySelector(`.tab-btn[data-status="${filterStatus}"]`);
            if (targetTab) {
                targetTab.click();
            }
        });
    });

    // 12. Lightweight Toast System
    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icon = type === 'success' ? '✨' : type === 'error' ? '⚠️' : 'ℹ️';
        toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 2800);
    }

    // 13. Confetti Animation Effect (Pure Canvas)
    function triggerConfetti() {
        const canvas = document.getElementById('confettiCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const particles = [];
        const colors = ['#2563eb', '#38bdf8', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#ffffff'];

        for (let i = 0; i < 70; i++) {
            particles.push({
                x: canvas.width / 2 + (Math.random() * 200 - 100),
                y: canvas.height / 2 + (Math.random() * 100 - 50),
                r: Math.random() * 6 + 3,
                color: colors[Math.floor(Math.random() * colors.length)],
                vx: (Math.random() - 0.5) * 12,
                vy: (Math.random() - 1.2) * 10,
                gravity: 0.25,
                alpha: 1,
                rot: Math.random() * 360,
                rotSpeed: (Math.random() - 0.5) * 10
            });
        }

        let animationFrame;
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let activeCount = 0;

            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += p.gravity;
                p.alpha -= 0.015;
                p.rot += p.rotSpeed;

                if (p.alpha > 0) {
                    activeCount++;
                    ctx.save();
                    ctx.translate(p.x, p.y);
                    ctx.rotate((p.rot * Math.PI) / 180);
                    ctx.globalAlpha = p.alpha;
                    ctx.fillStyle = p.color;
                    ctx.fillRect(-p.r / 2, -p.r / 2, p.r, p.r * 1.5);
                    ctx.restore();
                }
            });

            if (activeCount > 0) {
                animationFrame = requestAnimationFrame(animate);
            } else {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                cancelAnimationFrame(animationFrame);
            }
        }

        animate();
    }

    // Utility: HTML Escaper
    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Initial Load
    initDateDisplay();
    fetchTodos();
});
