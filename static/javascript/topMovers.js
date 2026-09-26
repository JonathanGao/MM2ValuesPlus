// Actual top movers: the sidebar list, and the calendar used to pick a day.
// The calendar is moved onto document.body and opened as a popover so the
// sidebar, navbar, and weapon panel cannot cover it or cut it off.
const section = document.getElementById('actual-movers-section');
const calendarButton = document.getElementById('actual-calendar-button');
const calendarEl = document.getElementById('actual-calendar');
const listEl = document.getElementById('actual-movers-list');
const noteEl = document.getElementById('actual-movers-note');
const emptyEl = document.getElementById('actual-movers-empty');
const datesJson = document.getElementById('actual-scrape-dates');

if (section && calendarButton && calendarEl && listEl && datesJson) {
    const predictor = section.dataset.predictor || '';
    const scrapeDates = new Set(JSON.parse(datesJson.textContent || '[]'));
    const weekdayLabels = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
    const monthLabels = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    const latestDate = scrapeDates.size
        ? [...scrapeDates].sort().at(-1)
        : null;
    let viewYear = latestDate ? Number(latestDate.slice(0, 4)) : new Date().getFullYear();
    let viewMonth = latestDate ? Number(latestDate.slice(5, 7)) - 1 : new Date().getMonth();
    let selectedDate = null;

    // Build YYYY-MM-DD from the calendar's year, month (0-11), and day number.
    function isoDate(year, month, day) {
        const monthText = String(month + 1).padStart(2, '0');
        const dayText = String(day).padStart(2, '0');
        return `${year}-${monthText}-${dayText}`;
    }

    function changeClass(changePct) {
        if (changePct > 0) return 'change-up';
        if (changePct < 0) return 'change-down';
        return 'change-flat';
    }

    function formatChangePct(changePct) {
        const value = Number(changePct) || 0;
        const sign = value > 0 ? '+' : '';
        return `${sign}${value.toFixed(2)}%`;
    }

    // Replace the Actual list with one day's results.
    // A flat day still lists the highest values at 0%. A day we cannot
    // compare shows a short explanation instead of a blank box.
    function renderMovers(payload) {
        listEl.replaceChildren();
        const movers = payload.movers || [];
        noteEl.hidden = !payload.flat;
        emptyEl.hidden = movers.length > 0;

        if (payload.status === 'no-scrape') {
            emptyEl.textContent = 'No scrape on this day.';
        } else if (payload.status === 'no-previous') {
            emptyEl.textContent = 'No earlier scrape to compare with this day.';
        } else if (!movers.length) {
            emptyEl.textContent = 'No day-over-day scrapes to compare.';
        }

        for (const mover of movers) {
            const item = document.createElement('li');
            item.className = 'mover-item';

            const link = document.createElement('a');
            link.className = 'mover-link';
            const query = predictor ? `?predictor=${encodeURIComponent(predictor)}` : '';
            link.href = `/${encodeURIComponent(mover.rarity)}${query}`;

            const name = document.createElement('span');
            name.className = 'mover-name';
            name.textContent = mover.name;

            const meta = document.createElement('span');
            meta.className = 'mover-meta';
            meta.append(`${mover.rarity} · `);
            const fromTime = document.createElement('time');
            fromTime.dateTime = mover.fromDate;
            fromTime.textContent = mover.fromDateLabel;
            meta.append(fromTime, ` ${mover.previousValue} → `);
            const toTime = document.createElement('time');
            toTime.dateTime = mover.toDate;
            toTime.textContent = mover.toDateLabel;
            meta.append(toTime, ` ${mover.currentValue}`);

            link.append(name, meta);

            const change = document.createElement('span');
            change.className = `mover-change ${changeClass(mover.changePct)}`;
            change.textContent = formatChangePct(mover.changePct);

            item.append(link, change);
            listEl.append(item);
        }
    }

    // Draw one month. Days with a daily scrape can be selected. Other days
    // stay visible but cannot be clicked, because there is nothing to compare.
    function renderCalendar() {
        calendarEl.replaceChildren();

        const nav = document.createElement('div');
        nav.className = 'actual-calendar-nav';
        const prev = document.createElement('button');
        prev.type = 'button';
        prev.textContent = '‹';
        prev.setAttribute('aria-label', 'Previous month');
        const month = document.createElement('span');
        month.className = 'actual-calendar-month';
        month.textContent = `${monthLabels[viewMonth]} ${viewYear}`;
        const next = document.createElement('button');
        next.type = 'button';
        next.textContent = '›';
        next.setAttribute('aria-label', 'Next month');
        prev.addEventListener('click', () => shiftMonth(-1));
        next.addEventListener('click', () => shiftMonth(1));
        nav.append(prev, month, next);

        const weekdays = document.createElement('div');
        weekdays.className = 'actual-calendar-weekdays';
        for (const label of weekdayLabels) {
            const cell = document.createElement('span');
            cell.textContent = label;
            weekdays.append(cell);
        }

        const grid = document.createElement('div');
        grid.className = 'actual-calendar-grid';
        const firstWeekday = new Date(viewYear, viewMonth, 1).getDay();
        const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
        for (let i = 0; i < firstWeekday; i += 1) {
            grid.append(document.createElement('span'));
        }
        for (let day = 1; day <= daysInMonth; day += 1) {
            const date = isoDate(viewYear, viewMonth, day);
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'actual-calendar-day';
            button.textContent = String(day);
            if (scrapeDates.has(date)) {
                button.classList.add('has-scrape');
                button.addEventListener('click', () => selectDate(date));
            } else {
                button.disabled = true;
            }
            if (date === selectedDate || (!selectedDate && date === latestDate)) {
                button.classList.add('selected');
            }
            grid.append(button);
        }

        const latest = document.createElement('button');
        latest.type = 'button';
        latest.className = 'actual-calendar-latest';
        latest.textContent = 'Latest day';
        latest.addEventListener('click', () => selectDate(null));

        calendarEl.append(nav, weekdays, grid, latest);
    }

    // Move the visible month forward or back, wrapping the year at the ends.
    function shiftMonth(delta) {
        viewMonth += delta;
        if (viewMonth < 0) {
            viewMonth = 11;
            viewYear -= 1;
        } else if (viewMonth > 11) {
            viewMonth = 0;
            viewYear += 1;
        }
        renderCalendar();
    }

    // Put the calendar in the browser's top layer, then place it beside the
    // Calendar button. The top layer is above every other element on the page.
    function showCalendarOnTop() {
        calendarEl.classList.remove('hidden');
        calendarEl.hidden = false;
        if (calendarEl.parentElement !== document.body) {
            document.body.appendChild(calendarEl);
        }
        calendarEl.setAttribute('popover', 'manual');
        if (typeof calendarEl.showPopover === 'function' && !calendarEl.matches(':popover-open')) {
            calendarEl.showPopover();
        }

        const rect = calendarButton.getBoundingClientRect();
        const width = calendarEl.offsetWidth || 256;
        const height = calendarEl.offsetHeight || 280;
        let left = rect.right + 8;
        if (left + width > window.innerWidth - 8) {
            left = Math.max(8, window.innerWidth - width - 8);
        }
        let top = rect.bottom + 6;
        if (top + height > window.innerHeight - 8) {
            top = Math.max(8, rect.top - height - 6);
        }
        calendarEl.style.top = `${top}px`;
        calendarEl.style.left = `${left}px`;
    }

    function setCalendarOpen(open) {
        calendarButton.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) {
            renderCalendar();
            showCalendarOnTop();
        } else if (typeof calendarEl.hidePopover === 'function' && calendarEl.matches(':popover-open')) {
            calendarEl.hidePopover();
        } else {
            calendarEl.hidden = true;
        }
    }

    // Load Actual movers for one scrape day. Passing null returns the latest day.
    async function selectDate(date) {
        selectedDate = date;
        const query = date ? `?date=${encodeURIComponent(date)}` : '';
        const response = await fetch(`/api/top-movers/actual${query}`);
        if (!response.ok) return;
        const payload = await response.json();
        renderMovers(payload);
        setCalendarOpen(false);
    }

    // Toggle the calendar. A click anywhere else, or Escape, closes it.
    calendarButton.addEventListener('click', () => {
        const open = calendarButton.getAttribute('aria-expanded') !== 'true';
        setCalendarOpen(open);
    });

    document.addEventListener('click', (event) => {
        // aria-expanded is the open/closed flag. The popover does not use the
        // hidden attribute, so that cannot be used to tell if it is showing.
        if (calendarButton.getAttribute('aria-expanded') !== 'true') return;
        if (calendarEl.contains(event.target) || calendarButton.contains(event.target)) return;
        setCalendarOpen(false);
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') setCalendarOpen(false);
    });
}
