/**
 * LIG DNA Work Time App - Interactive Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const DAY_NAMES = ['일', '월', '화', '수', '목', '금', '토'];

    // DOM Elements
    const currentDateText = document.getElementById('currentDateText');
    const statusBadge = document.getElementById('statusBadge');
    const clockInText = document.getElementById('clockInText');
    const clockOutText = document.getElementById('clockOutText');
    const bigTimer = document.getElementById('bigTimer');
    const bigTimerCaption = document.getElementById('bigTimerCaption');
    const clockInBtn = document.getElementById('clockInBtn');
    const clockOutBtn = document.getElementById('clockOutBtn');

    const statTodayMinutes = document.getElementById('statTodayMinutes');
    const statExpectedOut = document.getElementById('statExpectedOut');
    const statDiffLabel = document.getElementById('statDiffLabel');
    const statDiffValue = document.getElementById('statDiffValue');

    const weeklyTotal = document.getElementById('weeklyTotal');
    const weekBarChart = document.getElementById('weekBarChart');
    const monthlyTitle = document.getElementById('monthlyTitle');
    const monthlyWorkDays = document.getElementById('monthlyWorkDays');
    const monthlyTotal = document.getElementById('monthlyTotal');
    const monthlyAvg = document.getElementById('monthlyAvg');

    const prevDateBtn = document.getElementById('prevDateBtn');
    const nextDateBtn = document.getElementById('nextDateBtn');
    const lookupTodayBtn = document.getElementById('lookupTodayBtn');
    const lookupDateInput = document.getElementById('lookupDateInput');
    const lookupResult = document.getElementById('lookupResult');

    const recordsList = document.getElementById('recordsList');
    const emptyState = document.getElementById('emptyState');

    const editModalOverlay = document.getElementById('editModalOverlay');
    const closeEditModalBtn = document.getElementById('closeEditModalBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const editForm = document.getElementById('editForm');

    let liveTimerHandle = null;
    let todayState = null;

    // ---- KST-aware time helpers ---------------------------------------
    // The server stores/returns wall-clock KST strings ("YYYY-MM-DD HH:MM:SS").
    // This trick reads the browser clock through the Asia/Seoul timezone so
    // client-side calculations line up with what the server recorded,
    // regardless of the visitor's actual local timezone.
    function nowKST() {
        return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
    }

    function todayKSTStr() {
        const d = nowKST();
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    function parseWallClock(str) {
        // "YYYY-MM-DD HH:MM:SS" -> Date, parsed consistently with nowKST()
        return new Date(str.replace(' ', 'T'));
    }

    function timeOnly(str) {
        if (!str) return '--:--';
        return str.slice(11, 16);
    }

    function formatMinutes(minutes) {
        if (minutes === null || minutes === undefined) return '-';
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return `${h}시간 ${m}분`;
    }

    function formatElapsed(ms) {
        const totalSec = Math.max(Math.floor(ms / 1000), 0);
        const h = String(Math.floor(totalSec / 3600)).padStart(2, '0');
        const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
        const s = String(totalSec % 60).padStart(2, '0');
        return `${h}:${m}:${s}`;
    }

    // ---- Header date --------------------------------------------------
    function initDateDisplay() {
        const now = nowKST();
        const y = now.getFullYear();
        const m = String(now.getMonth() + 1).padStart(2, '0');
        const d = String(now.getDate()).padStart(2, '0');
        const dayName = DAY_NAMES[now.getDay()];
        currentDateText.textContent = `${y}년 ${m}월 ${d}일 (${dayName})`;
    }

    // ---- Today status card ---------------------------------------------
    async function fetchToday() {
        try {
            const res = await fetch('/api/work/today');
            if (!res.ok) throw new Error('Failed to fetch today status');
            todayState = await res.json();
            renderStatus(todayState);
        } catch (err) {
            console.error('fetchToday error:', err);
            showToast('오늘의 근무 상태를 불러오지 못했습니다.', 'error');
        }
    }

    function renderStatus(data) {
        clockInText.textContent = timeOnly(data.clock_in);
        clockOutText.textContent = timeOnly(data.clock_out);

        stopLiveTimer();

        if (data.status === 'not_started') {
            statusBadge.textContent = '출근 전';
            statusBadge.className = 'status-badge not-started';
            bigTimerCaption.textContent = '오늘 아직 출근하지 않았습니다.';
            bigTimer.textContent = '00:00:00';
            clockInBtn.style.display = 'inline-flex';
            clockOutBtn.style.display = 'none';
        } else if (data.status === 'working') {
            statusBadge.textContent = '근무 중';
            statusBadge.className = 'status-badge working';
            bigTimerCaption.textContent = '현재 근무 경과시간';
            startLiveTimer(data.clock_in);
            clockInBtn.style.display = 'none';
            clockOutBtn.style.display = 'inline-flex';
        } else {
            statusBadge.textContent = '근무 종료';
            statusBadge.className = 'status-badge done';
            bigTimerCaption.textContent = '오늘 근무시간';
            bigTimer.textContent = formatMinutesAsClock(data.work_minutes);
            clockInBtn.style.display = 'none';
            clockOutBtn.style.display = 'none';
        }

        statTodayMinutes.textContent = formatMinutes(data.work_minutes);
        statExpectedOut.textContent = data.expected_clock_out ? timeOnly(data.expected_clock_out) : '-';

        renderDiff(data);
    }

    function formatMinutesAsClock(minutes) {
        if (minutes === null || minutes === undefined) return '00:00:00';
        const h = String(Math.floor(minutes / 60)).padStart(2, '0');
        const m = String(minutes % 60).padStart(2, '0');
        return `${h}시간 ${m}분`;
    }

    function renderDiff(data) {
        if (data.work_minutes === null || data.work_minutes === undefined) {
            statDiffLabel.textContent = '목표 근무시간';
            statDiffValue.textContent = formatMinutes(data.target_minutes);
            return;
        }
        const diff = data.work_minutes - data.target_minutes;
        if (diff >= 0) {
            statDiffLabel.textContent = '초과근무';
            statDiffValue.textContent = diff === 0 ? '정확히 달성' : formatMinutes(diff);
        } else {
            statDiffLabel.textContent = '부족시간';
            statDiffValue.textContent = formatMinutes(-diff);
        }
    }

    function startLiveTimer(clockInStr) {
        const start = parseWallClock(clockInStr);
        function tick() {
            const elapsed = nowKST().getTime() - start.getTime();
            bigTimer.textContent = formatElapsed(elapsed);
        }
        tick();
        liveTimerHandle = setInterval(tick, 1000);
    }

    function stopLiveTimer() {
        if (liveTimerHandle) {
            clearInterval(liveTimerHandle);
            liveTimerHandle = null;
        }
    }

    // ---- Clock in / out -------------------------------------------------
    async function handleApiAction(url) {
        try {
            const res = await fetch(url, { method: 'POST' });
            const body = await res.json();
            if (!res.ok) {
                showToast(body.error || '요청을 처리하지 못했습니다.', 'error');
                return;
            }
            await refreshAll();
            return body;
        } catch (err) {
            console.error('API action error:', err);
            showToast('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'error');
        }
    }

    clockInBtn.addEventListener('click', async () => {
        const result = await handleApiAction('/api/work/clock-in');
        if (result) showToast(`출근 처리되었습니다 (${timeOnly(result.clock_in)})`, 'success');
    });

    clockOutBtn.addEventListener('click', async () => {
        const result = await handleApiAction('/api/work/clock-out');
        if (result) showToast(`퇴근 처리되었습니다 (${timeOnly(result.clock_out)})`, 'success');
    });

    // ---- Weekly summary ---------------------------------------------------
    async function fetchWeekly() {
        try {
            const res = await fetch(`/api/work/summary/weekly?date=${todayKSTStr()}`);
            if (!res.ok) throw new Error('weekly fetch failed');
            const data = await res.json();
            renderWeekly(data);
        } catch (err) {
            console.error('fetchWeekly error:', err);
        }
    }

    function renderWeekly(data) {
        weeklyTotal.textContent = formatMinutes(data.total_minutes);
        weekBarChart.innerHTML = '';
        const scaleMax = Math.max(480, ...data.days.map(d => d.work_minutes));

        data.days.forEach(day => {
            const dow = new Date(day.date + 'T00:00:00').getDay();
            const heightPct = scaleMax > 0 ? Math.min((day.work_minutes / scaleMax) * 100, 100) : 0;

            const col = document.createElement('div');
            col.className = 'week-bar-col';
            const isToday = day.date === todayKSTStr();
            col.innerHTML = `
                <span class="week-bar-minutes">${day.work_minutes > 0 ? formatMinutes(day.work_minutes) : ''}</span>
                <div class="week-bar-track">
                    <div class="week-bar-fill" style="height:${heightPct}%"></div>
                </div>
                <span class="week-bar-label ${isToday ? 'today' : ''}">${DAY_NAMES[dow]}</span>
            `;
            weekBarChart.appendChild(col);
        });
    }

    // ---- Monthly summary ---------------------------------------------------
    async function fetchMonthly() {
        try {
            const now = nowKST();
            const res = await fetch(`/api/work/summary/monthly?year=${now.getFullYear()}&month=${now.getMonth() + 1}`);
            if (!res.ok) throw new Error('monthly fetch failed');
            const data = await res.json();
            monthlyTitle.textContent = `${data.year}년 ${data.month}월`;
            monthlyWorkDays.textContent = `${data.work_days}일`;
            monthlyTotal.textContent = formatMinutes(data.total_minutes);
            monthlyAvg.textContent = formatMinutes(data.avg_minutes);
        } catch (err) {
            console.error('fetchMonthly error:', err);
        }
    }

    // ---- Date lookup ---------------------------------------------------
    async function fetchLookup(dateStr) {
        if (!dateStr) return;
        try {
            const res = await fetch(`/api/work/records/${dateStr}`);
            const data = await res.json();
            if (!res.ok) {
                lookupResult.textContent = data.error || '조회에 실패했습니다.';
                return;
            }
            if (data.status === 'not_started') {
                lookupResult.textContent = `${dateStr} : 근무 기록이 없습니다.`;
            } else {
                lookupResult.textContent =
                    `${dateStr} · 출근 ${timeOnly(data.clock_in)} ~ 퇴근 ${timeOnly(data.clock_out)} · ` +
                    `휴게 ${data.break_minutes}분 · 근무시간 ${formatMinutes(data.work_minutes)}`;
            }
        } catch (err) {
            console.error('fetchLookup error:', err);
            lookupResult.textContent = '조회 중 오류가 발생했습니다.';
        }
    }

    lookupDateInput.value = todayKSTStr();
    lookupDateInput.addEventListener('change', () => fetchLookup(lookupDateInput.value));

    prevDateBtn.addEventListener('click', () => {
        const d = new Date(lookupDateInput.value + 'T00:00:00');
        d.setDate(d.getDate() - 1);
        lookupDateInput.value = toDateInputValue(d);
        fetchLookup(lookupDateInput.value);
    });

    nextDateBtn.addEventListener('click', () => {
        const d = new Date(lookupDateInput.value + 'T00:00:00');
        d.setDate(d.getDate() + 1);
        lookupDateInput.value = toDateInputValue(d);
        fetchLookup(lookupDateInput.value);
    });

    lookupTodayBtn.addEventListener('click', () => {
        lookupDateInput.value = todayKSTStr();
        fetchLookup(lookupDateInput.value);
    });

    function toDateInputValue(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    // ---- Records list ---------------------------------------------------
    async function fetchRecords() {
        try {
            const res = await fetch('/api/work/records?limit=30');
            if (!res.ok) throw new Error('records fetch failed');
            const records = await res.json();
            renderRecords(records);
        } catch (err) {
            console.error('fetchRecords error:', err);
            showToast('근무 기록을 불러오지 못했습니다.', 'error');
        }
    }

    function renderRecords(records) {
        recordsList.innerHTML = '';

        if (records.length === 0) {
            emptyState.style.display = 'block';
            return;
        }
        emptyState.style.display = 'none';

        records.forEach(record => {
            const row = document.createElement('div');
            row.className = 'records-row';
            row.dataset.id = record.id;
            row.innerHTML = `
                <span data-label="날짜">${record.work_date}</span>
                <span data-label="출근">${timeOnly(record.clock_in)}</span>
                <span data-label="퇴근">${timeOnly(record.clock_out)}</span>
                <span data-label="휴게">${record.break_minutes}분</span>
                <span data-label="근무시간">${formatMinutes(record.work_minutes)}</span>
                <span class="records-actions">
                    <button class="action-btn btn-edit" title="수정" aria-label="수정">✏️</button>
                    <button class="action-btn btn-delete" title="삭제" aria-label="삭제">🗑️</button>
                </span>
            `;

            row.querySelector('.btn-edit').addEventListener('click', () => openEditModal(record));
            row.querySelector('.btn-delete').addEventListener('click', () => deleteRecord(record.id));

            recordsList.appendChild(row);
        });
    }

    async function deleteRecord(id) {
        if (!confirm('이 근무 기록을 삭제하시겠습니까?')) return;
        try {
            const res = await fetch(`/api/work/records/${id}`, { method: 'DELETE' });
            const body = await res.json();
            if (!res.ok) {
                showToast(body.error || '삭제에 실패했습니다.', 'error');
                return;
            }
            showToast('근무 기록이 삭제되었습니다.', 'info');
            await refreshAll();
        } catch (err) {
            console.error('deleteRecord error:', err);
            showToast('삭제 중 오류가 발생했습니다.', 'error');
        }
    }

    // ---- Edit modal ---------------------------------------------------
    function openEditModal(record) {
        document.getElementById('editRecordId').value = record.id;
        document.getElementById('editWorkDate').value = record.work_date;
        document.getElementById('editClockIn').value = record.clock_in ? record.clock_in.slice(11, 16) : '';
        document.getElementById('editClockOut').value = record.clock_out ? record.clock_out.slice(11, 16) : '';
        document.getElementById('editBreakMinutes').value = record.break_minutes;

        editModalOverlay.classList.add('active');
    }

    function closeEditModal() {
        editModalOverlay.classList.remove('active');
    }

    closeEditModalBtn.addEventListener('click', closeEditModal);
    cancelEditBtn.addEventListener('click', closeEditModal);
    editModalOverlay.addEventListener('click', (e) => {
        if (e.target === editModalOverlay) closeEditModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeEditModal();
    });

    editForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('editRecordId').value;
        const workDate = document.getElementById('editWorkDate').value;
        const clockInTime = document.getElementById('editClockIn').value;
        const clockOutTime = document.getElementById('editClockOut').value;
        const breakMinutes = parseInt(document.getElementById('editBreakMinutes').value, 10) || 0;

        const payload = {
            clock_in: clockInTime ? `${workDate} ${clockInTime}:00` : null,
            clock_out: clockOutTime ? `${workDate} ${clockOutTime}:00` : null,
            break_minutes: breakMinutes,
        };

        try {
            const res = await fetch(`/api/work/records/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const body = await res.json();
            if (!res.ok) {
                showToast(body.error || '수정에 실패했습니다.', 'error');
                return;
            }
            closeEditModal();
            showToast('근무 기록이 수정되었습니다.', 'success');
            await refreshAll();
        } catch (err) {
            console.error('edit submit error:', err);
            showToast('수정 중 오류가 발생했습니다.', 'error');
        }
    });

    // ---- Toast system ---------------------------------------------------
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
        }, 3200);
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ---- Bootstrap ---------------------------------------------------
    async function refreshAll() {
        await Promise.all([
            fetchToday(),
            fetchWeekly(),
            fetchMonthly(),
            fetchRecords(),
            fetchLookup(lookupDateInput.value),
        ]);
    }

    initDateDisplay();
    refreshAll();
});
