// app.js - CityPulse Dashboard UI Logic

document.addEventListener('DOMContentLoaded', () => {
    // Set Current Date and Time
    const datetimeElement = document.getElementById('current-datetime');
    
    function updateDateTime() {
        const now = new Date();
        const options = { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        datetimeElement.textContent = now.toLocaleDateString('en-US', options);
    }
    
    // Initial call and set interval
    updateDateTime();
    setInterval(updateDateTime, 60000);

    const refreshBtn = document.getElementById('refresh-btn');

    // Map Controls Toggle
    const mapBtns = document.querySelectorAll('.map-btn');
    mapBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            mapBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Animate circular progress on load
    // The CSS already handles the stroke-dasharray animation, 
    // but we can add subtle entry animations for cards here if needed.
    
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.5s ease-out';
        
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 + (index * 150));
    });
    
    const hero = document.querySelector('.hero-section');
    hero.style.opacity = '0';
    hero.style.transition = 'opacity 0.8s ease-out';
    setTimeout(() => {
        hero.style.opacity = '1';
    }, 50);

    // Notification Dropdown Logic
    const notifBtn = document.getElementById('notification-btn');
    const notifPanel = document.getElementById('notification-panel');
    const badge = document.getElementById('notification-badge');
    let notificationRecords = null;
    const readNotificationIds = new Set();
    const dismissedNotificationIds = new Set();
    
    // Toggle Panel
    notifBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        notifPanel.classList.toggle('hidden');
    });

    // Close when clicking outside
    document.addEventListener('click', (e) => {
        if (!notifPanel.contains(e.target) && !notifBtn.contains(e.target)) {
            notifPanel.classList.add('hidden');
        }
    });

    // Prevent closing when clicking inside panel
    notifPanel.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    // Update Badge Count
    function updateBadgeCount() {
        if (!Array.isArray(notificationRecords)) {
            badge.style.display = 'none';
            if (markAllReadBtn) markAllReadBtn.disabled = true;
            return;
        }
        const unreadCount = notificationRecords.filter(record =>
            !dismissedNotificationIds.has(String(record.id)) && !readNotificationIds.has(String(record.id))
        ).length;
        badge.textContent = String(unreadCount);
        if (markAllReadBtn) markAllReadBtn.disabled = unreadCount === 0;
        if (unreadCount > 0) {
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    }

    // Mark All as Read
    const markAllReadBtn = document.getElementById('mark-all-read');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', () => {
            if (!Array.isArray(notificationRecords)) return;
            notificationRecords.forEach(record => readNotificationIds.add(String(record.id)));
            renderDashboardAlerts();
            if (modalTitle.textContent === 'All Notifications') renderAllNotificationsPanel();
            updateBadgeCount();
        });
    }

    // Update count on load
    updateBadgeCount();

    // Nav Navigation and Smooth Scroll
    const navLinks = document.querySelectorAll('.nav-link');
    function syncNavigation() {
        const hash = window.location.hash || '#dashboard';
        navLinks.forEach(link => {
            const active = link.getAttribute('href') === hash;
            link.classList.toggle('active', active);
            if (active) link.setAttribute('aria-current', 'page');
            else link.removeAttribute('aria-current');
        });
    }
    syncNavigation();
    window.addEventListener('hashchange', syncNavigation);
    window.addEventListener('popstate', syncNavigation);
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            if (targetId && targetId !== '#') {
                const targetElement = document.getElementById(targetId);
                if (targetElement) {
                    if (window.location.hash !== '#' + targetId) history.pushState(null, '', '#' + targetId);
                    syncNavigation();
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    if (targetId === 'map' && civicEvents === null) loadCivicEvents();
                }
            }
        });
    });

    // Dashboard detail modal logic
    const modal = document.getElementById('mock-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const modalActionBtn = modal.querySelector('.modal-footer .btn-primary');
    const modalFooterCloseBtn = modal.querySelector('.modal-footer .btn-outline.close-modal');
    const closeModalBtns = document.querySelectorAll('.close-modal');
    let reportMode = false;
    let reportForm = null;
    let reportSubmitted = false;

    function openModal(title, content) {
        modalTitle.textContent = title;
        modal.querySelector('.modal-content')?.classList.remove('report-mode', 'dashboard-data-mode');
        if (modalFooterCloseBtn) modalFooterCloseBtn.style.display = '';
        modalActionBtn.style.display = 'none';
        modalActionBtn.textContent = '';
        const paragraph = document.createElement('p');
        paragraph.textContent = content;
        modalBody.replaceChildren(paragraph);
        modal.classList.remove('hidden');
    }

    function closeModal() {
        modal.classList.add('hidden');
        modal.querySelector('.modal-content')?.classList.remove('report-mode', 'dashboard-data-mode');
        if (modalFooterCloseBtn) modalFooterCloseBtn.style.display = '';
        modalActionBtn.style.display = 'none';
        reportMode = false;
        reportForm = null;
        reportSubmitted = false;
        modalActionBtn.textContent = '';
    }

    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', closeModal);
    });

    modalActionBtn.addEventListener('click', () => {
        if (reportMode) {
            if (reportSubmitted) closeModal();
            else reportForm?.requestSubmit();
            return;
        }
        closeModal();
    });

    const reportIssueBtn = [...document.querySelectorAll('.top-header .header-actions .btn')]
        .find(button => button.textContent.includes('Report Issue'));
    reportIssueBtn?.addEventListener('click', openReportForm);

    // Close modal on click outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    function focusIncidentList() {
        document.querySelector('.nav-link[href="#incidents"]')?.click();
        if (!incidentList) return;
        incidentList.tabIndex = -1;
        incidentList.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        incidentList.focus({ preventScroll: true });
    }

    document.addEventListener('click', event => {
        const viewAll = event.target.closest('.civic-card .view-all');
        if (!viewAll) return;
        event.preventDefault();
        focusIncidentList();
    });

    notifPanel.addEventListener('click', event => {
        const viewAll = event.target.closest('.dropdown-footer a');
        if (!viewAll) return;
        event.preventDefault();
        notifPanel.classList.add('hidden');
        openDashboardDataPanel('All Notifications');
        loadAllNotificationsPanel();
    });

    notifPanel.addEventListener('click', handleNotificationAction);
    modalBody.addEventListener('click', handleNotificationAction);

    // Hamburger Menu (mobile nav)
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const hamburgerIcon = document.getElementById('hamburger-icon');
    const navLinksMenu = document.querySelector('.nav-links');

    if (hamburgerBtn && navLinksMenu) {
        hamburgerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = navLinksMenu.classList.toggle('open');
            hamburgerBtn.setAttribute('aria-expanded', isOpen);
            hamburgerIcon.className = isOpen ? 'ph ph-x' : 'ph ph-list';
        });

        // Close when a nav link is clicked
        navLinksMenu.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navLinksMenu.classList.remove('open');
                hamburgerIcon.className = 'ph ph-list';
                hamburgerBtn.setAttribute('aria-expanded', 'false');
            });
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!navLinksMenu.contains(e.target) && !hamburgerBtn.contains(e.target)) {
                if (navLinksMenu.classList.contains('open')) {
                    navLinksMenu.classList.remove('open');
                    hamburgerIcon.className = 'ph ph-list';
                    hamburgerBtn.setAttribute('aria-expanded', 'false');
                }
            }
        });
    }

    // Live data from the existing FastAPI read endpoints.
    const apiBaseUrl = window.CITYPULSE_API_BASE_URL || 'http://127.0.0.1:8000/api';
    let dashboardSnapshot = null;
    let dataSourceLabel = null;
    let predictionSnapshot = null;
    let predictionZone = null;
    let predictionTimestamp = null;
    let reportPredictions = [];
    let weatherRecords = null;
    let trafficRecords = null;
    let incidentRecords = null;
    let civicEvents = null;

    const weatherBody = document.querySelector('.weather-card .card-body');
    const trafficBody = document.querySelector('.traffic-card .card-body');
    const crowdPredictionBody = document.querySelector('.ml-insights-card .card-body');
    const incidentList = document.querySelector('.civic-card .incident-list');
    const incidentSummaryHost = document.querySelector('.civic-card .incident-summary');
    const recommendationsHost = document.querySelector('.recommendations-list');
    const incidentSearch = document.getElementById('incident-search');
    const incidentStatusFilter = document.getElementById('incident-status-filter');
    const incidentSeverityFilter = document.getElementById('incident-severity-filter');
    const incidentCategoryFilter = document.getElementById('incident-category-filter');
    const reportsContent = document.querySelector('#reports .reports-content');
    const reportsRefreshBtn = document.getElementById('reports-refresh-btn');
    const notificationBody = document.querySelector('#notification-panel .dropdown-body');
    const heroSection = document.querySelector('#dashboard.hero-section');
    const heroStatItems = heroSection?.querySelectorAll('.hero-stats .stat-item') || [];
    const mapArea = document.querySelector('.map-interactive-area');
    const cityMapHost = document.getElementById('citypulse-map');
    const mapLegend = mapArea?.querySelector('.map-legend');
    const mapZoomControls = mapArea?.querySelectorAll('.map-zoom-controls .zoom-btn') || [];
    let cityMap = null;
    let mapMarkers = [];

    function makeElement(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = String(text);
        return node;
    }

    function setApiState(host, state, message, retry) {
        if (!host) return;
        host.classList.add('api-state-host');
        host.dataset.apiState = state;
        host.setAttribute('aria-busy', state === 'loading' ? 'true' : 'false');
        host.querySelector(':scope > .api-state-panel')?.remove();
        const panel = makeElement('div', 'api-state-panel is-' + state);
        panel.setAttribute('role', state === 'error' ? 'alert' : 'status');
        panel.setAttribute('aria-live', state === 'error' ? 'assertive' : 'polite');
        panel.append(makeElement('span', 'api-state-indicator', state === 'loading' ? ' ' : ''));
        panel.append(makeElement('p', 'api-state-message', message));
        if (retry && state === 'error') {
            const button = makeElement('button', 'btn btn-outline api-retry', 'Try again');
            button.type = 'button';
            button.addEventListener('click', retry);
            panel.append(button);
        }
        host.append(panel);
    }

    function clearApiState(host) {
        if (!host) return;
        host.querySelector(':scope > .api-state-panel')?.remove();
        host.classList.remove('api-state-host');
        delete host.dataset.apiState;
        host.removeAttribute('aria-busy');
    }

    function setMapState(state, message, retry) {
        mapArea?.querySelector('.api-map-state')?.remove();
        if (!mapArea) return;
        const panel = makeElement('div', 'api-state-panel api-map-state is-' + state);
        panel.setAttribute('role', state === 'error' ? 'alert' : 'status');
        panel.setAttribute('aria-live', state === 'error' ? 'assertive' : 'polite');
        panel.append(makeElement('span', 'api-state-indicator', state === 'loading' ? ' ' : ''));
        panel.append(makeElement('p', 'api-state-message', message));
        if (retry && state === 'error') {
            const button = makeElement('button', 'btn btn-outline api-retry', 'Try again');
            button.type = 'button';
            button.addEventListener('click', retry);
            panel.append(button);
        }
        mapArea.append(panel);
    }

    function initializeCityMap() {
        if (cityMap) return cityMap;
        if (!cityMapHost || !window.L) throw new Error('The interactive map could not load. Check your connection and try again.');
        const defaultMapZoom = mapArea?.clientWidth <= 420 ? 10 : 12;
        cityMap = window.L.map(cityMapHost, { zoomControl: false, scrollWheelZoom: true }).setView([26.9124, 75.7873], defaultMapZoom);
        window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
        }).addTo(cityMap);
        cityMap.on('zoomend', () => { if (mapArea) mapArea.dataset.zoom = String(cityMap.getZoom()); });
        if (mapArea) mapArea.dataset.zoom = String(cityMap.getZoom());
        window.setTimeout(() => cityMap?.invalidateSize(), 0);
        return cityMap;
    }

    async function fetchApi(path, options = {}) {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 12000);
        try {
            const response = await fetch(apiBaseUrl + path, {
                method: 'GET',
                ...options,
                headers: { Accept: 'application/json', ...(options?.headers || {}) },
                signal: controller.signal
            });
            const body = await response.json().catch(() => null);
            if (!response.ok) {
                throw new Error((typeof body?.detail === 'string' && body.detail) || body?.message || ('CityPulse API returned ' + response.status + '.'));
            }
            return body;
        } catch (error) {
            if (error.name === 'AbortError') throw new Error('The CityPulse API request timed out.');
            if (error instanceof TypeError) {
                throw new Error('Could not reach the API. Check that FastAPI is running and this frontend origin is allowed by CORS.');
            }
            throw error;
        } finally {
            window.clearTimeout(timeout);
        }
    }

    function setReportMessage(message, state) {
        let status = modalBody.querySelector('.report-form-state');
        if (!status) {
            status = makeElement('p', 'report-form-state');
            status.setAttribute('aria-live', 'polite');
            modalBody.append(status);
        }
        status.className = 'report-form-state is-' + state;
        status.setAttribute('role', state === 'error' ? 'alert' : 'status');
        status.setAttribute('aria-live', state === 'error' ? 'assertive' : 'polite');
        status.textContent = message;
    }

    function openReportForm() {
        reportMode = true;
        reportSubmitted = false;
        modalTitle.textContent = 'Report a Civic Issue';
        modal.querySelector('.modal-content')?.classList.add('report-mode');
        if (modalFooterCloseBtn) modalFooterCloseBtn.style.display = 'none';
        modalActionBtn.style.display = '';
        modalActionBtn.textContent = 'Submit Report';
        modalBody.replaceChildren();

        reportForm = makeElement('form', 'report-form');
        reportForm.noValidate = false;

        const field = (labelText, name, control, className) => {
            const wrapper = makeElement('label', 'report-field' + (className ? ' ' + className : ''));
            wrapper.append(makeElement('span', '', labelText));
            control.name = name;
            control.required = true;
            wrapper.append(control);
            return wrapper;
        };

        const category = makeElement('select');
        [
            ['waterlogging', 'Waterlogging'],
            ['road_accident', 'Road accident'],
            ['road_damage', 'Road damage'],
            ['fallen_tree', 'Fallen tree'],
            ['streetlight_outage', 'Streetlight outage'],
            ['traffic_signal_failure', 'Traffic signal failure'],
            ['other', 'Other']
        ].forEach(([value, label]) => {
            const option = makeElement('option', '', label);
            option.value = value;
            category.append(option);
        });

        const title = makeElement('input');
        title.type = 'text';
        title.minLength = 3;
        title.maxLength = 120;
        title.placeholder = 'Short issue title';

        const description = makeElement('textarea');
        description.rows = 3;
        description.minLength = 3;
        description.maxLength = 1000;
        description.placeholder = 'Describe the issue';

        const severity = makeElement('select');
        [['low', 'Low'], ['medium', 'Medium'], ['high', 'High'], ['critical', 'Critical']].forEach(([value, label]) => {
            const option = makeElement('option', '', label);
            option.value = value;
            severity.append(option);
        });

        const zone = makeElement('input');
        zone.type = 'text';
        zone.value = 'Jaipur';
        zone.maxLength = 100;

        const latitude = makeElement('input');
        latitude.type = 'number';
        latitude.step = 'any';
        latitude.min = '-90';
        latitude.max = '90';
        latitude.value = '26.9124';

        const longitude = makeElement('input');
        longitude.type = 'number';
        longitude.step = 'any';
        longitude.min = '-180';
        longitude.max = '180';
        longitude.value = '75.7873';

        const coordinateRow = makeElement('div', 'report-coordinate-row');
        coordinateRow.append(field('Latitude', 'latitude', latitude), field('Longitude', 'longitude', longitude));
        reportForm.append(
            field('Issue type', 'incident_category', category),
            field('Title', 'title', title),
            field('Description', 'description', description),
            field('Severity', 'severity', severity),
            field('Zone', 'zone', zone),
            coordinateRow
        );
        reportForm.addEventListener('submit', submitIncidentReport);
        modalBody.append(reportForm);
        modal.classList.remove('hidden');
        description.focus();
    }

    async function submitIncidentReport(event) {
        event.preventDefault();
        if (!reportForm || reportSubmitted) return;
        const descriptionField = reportForm.elements.namedItem('description');
        const titleField = reportForm.elements.namedItem('title');
        const zoneField = reportForm.elements.namedItem('zone');
        const descriptionText = String(descriptionField.value || '').trim();
        const titleText = String(titleField.value || '').trim();
        const zoneText = String(zoneField.value || '').trim();
        descriptionField.setCustomValidity(descriptionText.length < 3 ? 'Enter a description with at least 3 non-space characters.' : '');
        titleField.setCustomValidity(titleText.length < 3 ? 'Enter a title with at least 3 non-space characters.' : '');
        zoneField.setCustomValidity(zoneText ? '' : 'Enter a zone.');
        if (!reportForm.reportValidity()) {
            setReportMessage('Check the required report fields and try again.', 'error');
            return;
        }

        const fields = new FormData(reportForm);
        const payload = {
            incident_category: fields.get('incident_category'),
            description: titleText + ' — ' + descriptionText,
            severity: fields.get('severity'),
            status: 'reported',
            timestamp: new Date().toISOString(),
            location: {
                zone: zoneText,
                latitude: Number(fields.get('latitude')),
                longitude: Number(fields.get('longitude'))
            }
        };

        modalActionBtn.disabled = true;
        modalActionBtn.textContent = 'Submitting…';
        setReportMessage('Submitting your report…', 'loading');
        try {
            await fetchApi('/incidents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            reportSubmitted = true;
            reportForm.remove();
            setReportMessage('Your civic issue was reported successfully.', 'success');
            modalActionBtn.textContent = 'Close';
            await Promise.allSettled([loadDashboard(), loadWeather(), loadTraffic(), loadIncidents(), loadCivicEvents(), loadDataSource()]);
            await loadCrowdPrediction();
            await loadReports();
        } catch (error) {
            setReportMessage(error.message || 'Could not submit your report. Please try again.', 'error');
            modalActionBtn.textContent = 'Try Again';
        } finally {
            modalActionBtn.disabled = false;
        }
    }

    function requireArray(payload, label) {
        if (!Array.isArray(payload)) throw new Error('The ' + label + ' endpoint returned an unexpected response.');
        return payload;
    }

    function mean(records, pick) {
        const values = records.map(pick).map(Number).filter(Number.isFinite);
        return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
    }

    function formatValue(value, digits, suffix) {
        const number = Number(value);
        return Number.isFinite(number) ? String(Number(number.toFixed(digits || 0))) + (suffix || '') : '—';
    }

    function humanize(value) {
        return String(value || 'Unknown').replace(/[_-]+/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase());
    }

    function relativeTime(value) {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return 'Time unavailable';
        const minutes = Math.max(0, Math.floor((Date.now() - date.getTime()) / 60000));
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return minutes + 'm ago';
        if (minutes < 1440) return Math.floor(minutes / 60) + 'h ago';
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    }

    function updateLastUpdated(card, timestamp) {
        const target = card?.querySelector('.last-updated');
        if (target) target.textContent = timestamp ? relativeTime(timestamp) : 'Updated just now';
    }

    function renderWeather() {
        if (!weatherBody || !Array.isArray(weatherRecords) || !weatherRecords.length) return;
        clearApiState(weatherBody);
        const current = weatherRecords[0];
        const temp = current.temperature;
        const humidity = current.humidity;
        const rainfall = current.rainfall;
        const wind = current.wind_speed_kmh;
        const aqi = current.air_quality_index;
        const condition = current.weather_condition || 'Unknown';
        const sourceNote = weatherBody.querySelector('.weather-source-note');
        if (sourceNote) {
            sourceNote.textContent = 'Live weather • Open-Meteo' + (current.is_stale
                ? ' · Cached data. ' + (current.warning || 'Provider refresh is unavailable.')
                : '');
        }

        weatherBody.querySelector('.temperature').textContent = formatValue(temp, 1, '°C');
        weatherBody.querySelector('.feels-like').textContent = current.data_source ? 'Live weather • Open-Meteo' : 'Source unavailable';
        weatherBody.querySelector('.condition-badge').textContent = condition;
        const icon = weatherBody.querySelector('.weather-main > i');
        if (icon) {
            const text = condition.toLowerCase();
            icon.className = 'ph-fill ' + (/rain|storm|shower/.test(text) ? 'ph-cloud-rain' : /cloud|haze|overcast/.test(text) ? 'ph-cloud' : 'ph-sun');
        }

        const labels = weatherBody.querySelectorAll('.visual-indicator .indicator-label span');
        labels[0].textContent = 'Current precipitation';
        labels[1].textContent = displayMeasuredValue(rainfall, 1, ' mm');
        weatherBody.querySelector('.visual-indicator .progress-fill').style.width = Math.min(100, Math.max(0, Number(rainfall) / 5)) + '%';
        const metrics = weatherBody.querySelectorAll('.grid-metrics .metric-box');
        if (metrics[0]) metrics[0].querySelector('.m-val').textContent = displayMeasuredValue(humidity, 0, '%');
        if (metrics[1]) metrics[1].querySelector('.m-val').textContent = displayMeasuredValue(wind, 1, ' km/h');
        if (metrics[2]) {
            metrics[2].querySelector('.m-val').textContent = aqi == null ? '—' : formatValue(aqi);
            metrics[2].querySelector('.m-lbl').textContent = 'Air Quality Index';
        }
        updateLastUpdated(weatherBody.closest('.card'), current.fetched_at || current.timestamp);
    }

    function renderTraffic() {
        if (!trafficBody || !Array.isArray(trafficRecords) || !trafficRecords.length) return;
        clearApiState(trafficBody);
        const sourceNote = trafficBody.querySelector('.traffic-source-note');
        if (sourceNote) sourceNote.textContent = 'Non-live · Stored development observations; no live traffic feed configured';
        const summary = dashboardSnapshot?.traffic || {};
        const congestion = Number.isFinite(Number(summary.average_congestion)) ? Number(summary.average_congestion) : mean(trafficRecords, row => row.congestion_percentage);
        const speed = mean(trafficRecords.filter(row => row.average_speed_kmh != null), row => row.average_speed_kmh);
        const status = trafficBody.querySelector('.traffic-status');
        let label = 'Light Congestion';
        let statusClass = 'traffic-low';
        if (congestion >= 75) { label = 'Severe Congestion'; statusClass = 'traffic-high'; }
        else if (congestion >= 35) { label = congestion >= 55 ? 'Heavy Congestion' : 'Moderate Congestion'; statusClass = 'status-moderate'; }
        status.className = 'traffic-status ' + statusClass;
        status.replaceChildren(makeElement('span', 'pulse-dot'), document.createTextNode(label));
        trafficBody.querySelector('.speed-val').textContent = formatValue(speed, 1);
        const labels = trafficBody.querySelectorAll('.visual-indicator .indicator-label span');
        labels[0].textContent = 'Citywide Congestion';
        labels[1].textContent = formatValue(congestion) + '%';
        trafficBody.querySelector('.visual-indicator .progress-fill').style.width = Math.min(100, Math.max(0, Number(congestion) || 0)) + '%';

        const list = trafficBody.querySelector('.alert-list');
        list.replaceChildren();
        [...trafficRecords].sort((a, b) => Number(b.congestion_percentage) - Number(a.congestion_percentage)).slice(0, 2).forEach(row => {
            const severity = String(row.severity || '').toLowerCase();
            const warning = severity === 'high' || severity === 'critical';
            const item = makeElement('li');
            const icon = makeElement('span', 'alert-icon ' + (warning ? 'warning' : 'info'));
            icon.append(makeElement('i', 'ph ' + (warning ? 'ph-warning' : 'ph-info')));
            const text = makeElement('div', 'alert-text');
            text.append(makeElement('strong', '', row.location?.road_name || row.location?.landmark || row.location?.zone || 'Unnamed corridor'));
            text.append(makeElement('span', '', formatValue(row.congestion_percentage) + '% congestion · ' + formatValue(row.delay, 1) + ' min delay'));
            item.append(icon, text);
            list.append(item);
        });
        const heading = trafficBody.querySelector('.affected-areas h5');
        const avgDelay = summary.average_delay_minutes != null ? summary.average_delay_minutes : mean(trafficRecords, row => row.delay);
        heading.textContent = 'Avg delay ' + formatValue(avgDelay, 1) + ' min' + (summary.most_congested_corridor ? ' · Peak: ' + summary.most_congested_corridor : '');
        updateLastUpdated(trafficBody.closest('.card'), trafficRecords[0]?.timestamp);
    }

    function displayMeasuredValue(value, digits, suffix) {
        return value == null || value === '' || !Number.isFinite(Number(value))
            ? 'Not reported'
            : formatValue(value, digits, suffix);
    }

    function latestWeatherByZone(records) {
        const latest = new Map();
        records.forEach(record => {
            const key = String(record.location?.zone || '').trim().toLowerCase();
            if (!key) return;
            const previous = latest.get(key);
            if (!previous || new Date(record.timestamp) > new Date(previous.timestamp)) latest.set(key, record);
        });
        return [...latest.values()].sort((a, b) => String(a.location?.zone).localeCompare(String(b.location?.zone)));
    }

    function renderWeatherForecastPanel(records) {
        if (!records.length) {
            setApiState(modalBody, 'empty', 'No weather observations are currently available.');
            return;
        }
        clearApiState(modalBody);
        modalBody.replaceChildren();
        const cachedWarning = records[0].warning ? ' · ' + records[0].warning : '';
        modalBody.append(makeElement('p', 'dashboard-data-note', 'Live source: Open-Meteo · Jaipur. Forecast values are provider model output, not local station measurements.' + cachedWarning));
        const list = makeElement('div', 'dashboard-data-list');
        latestWeatherByZone(records).forEach(record => {
            const article = makeElement('article', 'dashboard-data-record');
            article.append(makeElement('h4', '', record.location?.zone || 'Weather observation'));
            addDashboardDataField(article, 'Current condition:', record.weather_condition || 'Not reported');
            addDashboardDataField(article, 'Temperature:', displayMeasuredValue(record.temperature, 1, '°C'));
            addDashboardDataField(article, 'Humidity:', displayMeasuredValue(record.humidity, 0, '%'));
            addDashboardDataField(article, 'Wind:', displayMeasuredValue(record.wind_speed_kmh, 1, ' km/h'));
            addDashboardDataField(article, 'Rainfall:', displayMeasuredValue(record.rainfall, 1, ' mm'));
            if (record.air_quality_index != null) addDashboardDataField(article, 'Air quality index:', displayMeasuredValue(record.air_quality_index));
            addDashboardDataField(article, 'Source:', record.data_source || 'Unavailable');
            addDashboardDataField(article, 'Updated:', formatIncidentTimestamp(record.fetched_at || record.timestamp));
            const forecast = Array.isArray(record.forecast) ? record.forecast.slice(0, 12) : [];
            forecast.forEach(hour => {
                addDashboardDataField(article, new Date(hour.timestamp).toLocaleTimeString([], { hour: 'numeric' }) + ':',
                    `${displayMeasuredValue(hour.temperature, 0, '°C')} · ${hour.weather_condition} · rain ${displayMeasuredValue(hour.precipitation, 1, ' mm')} (${displayMeasuredValue(hour.precipitation_probability, 0, '%')} chance)`);
            });
            list.append(article);
        });
        modalBody.append(list);
    }

    async function loadWeatherForecastPanel() {
        setApiState(modalBody, 'loading', 'Loading current weather observations…');
        try {
            weatherRecords = requireArray(await fetchApi('/weather?limit=100'), 'weather');
            renderWeather();
            renderWeatherForecastPanel(weatherRecords);
        } catch (error) {
            setApiState(modalBody, 'error', error.message || 'Could not load weather observations.', loadWeatherForecastPanel);
        }
    }

    function renderTrafficDetailsPanel(records) {
        if (!records.length) {
            setApiState(modalBody, 'empty', 'No traffic observations are currently available.');
            return;
        }
        clearApiState(modalBody);
        modalBody.replaceChildren();
        modalBody.append(makeElement('p', 'dashboard-data-note', 'Non-live development observations from stored backend data. No live traffic provider is configured; do not use these values as current traffic conditions.'));
        const summary = dashboardSnapshot?.traffic;
        if (summary) {
            const summaryCard = makeElement('article', 'dashboard-data-record');
            summaryCard.append(makeElement('h4', '', 'Backend traffic summary'));
            addDashboardDataField(summaryCard, 'Average congestion:', displayMeasuredValue(summary.average_congestion, 1, '%'));
            addDashboardDataField(summaryCard, 'Average delay:', displayMeasuredValue(summary.average_delay_minutes, 1, ' min'));
            if (summary.most_congested_corridor) addDashboardDataField(summaryCard, 'Most congested corridor:', summary.most_congested_corridor);
            if (summary.most_congested_zone) addDashboardDataField(summaryCard, 'Most congested zone:', summary.most_congested_zone);
            modalBody.append(summaryCard);
        }
        const list = makeElement('div', 'dashboard-data-list');
        [...records].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).forEach(record => {
            const location = record.location || {};
            const title = location.road_name || location.landmark || location.zone || 'Traffic observation';
            const article = makeElement('article', 'dashboard-data-record');
            article.append(makeElement('h4', '', title));
            addDashboardDataField(article, 'Location:', [location.zone, location.address, location.landmark]
                .filter((value, index, values) => value && values.indexOf(value) === index).join(' · ') || 'Not reported');
            addDashboardDataField(article, 'Congestion:', displayMeasuredValue(record.congestion_percentage, 1, '%'));
            addDashboardDataField(article, 'Estimated delay:', displayMeasuredValue(record.delay, 1, ' min'));
            addDashboardDataField(article, 'Average speed:', displayMeasuredValue(record.average_speed_kmh, 1, ' km/h'));
            addDashboardDataField(article, 'Severity:', humanize(record.severity || 'Not reported'));
            addDashboardDataField(article, 'Observed:', formatIncidentTimestamp(record.timestamp));
            list.append(article);
        });
        modalBody.append(list);
    }

    async function loadTrafficDetailsPanel() {
        setApiState(modalBody, 'loading', 'Loading traffic observations…');
        try {
            trafficRecords = requireArray(await fetchApi('/traffic?limit=100'), 'traffic');
            renderTraffic();
            renderTrafficDetailsPanel(trafficRecords);
        } catch (error) {
            setApiState(modalBody, 'error', error.message || 'Could not load traffic observations.', loadTrafficDetailsPanel);
        }
    }

    function updateIncidentSummary(summary) {
        if (!summary) return;
        const card = document.querySelector('.civic-card');
        if (!card) return;
        clearApiState(card.querySelector('.incident-summary'));
        const provenance = card.querySelector('.incident-source-note');
        if (provenance) provenance.textContent = dataSourceLabel === 'MongoDB'
            ? 'User-reported incident records · MongoDB · not independently verified'
            : 'User-reported incidents unavailable · MongoDB is disconnected';
        card.querySelector('.incident-count .count').textContent = formatValue(summary.total_incidents);
        card.querySelector('.incident-count .label').textContent = 'Total Incidents';
        const breakdown = summary.breakdown_by_severity || {};
        const entries = [
            [card.querySelector('.breakdown-item.critical'), (Number(breakdown.critical) || 0) + (Number(breakdown.high) || 0), 'High / Critical'],
            [card.querySelector('.breakdown-item.warning'), Number(breakdown.medium) || 0, 'Medium'],
            [card.querySelector('.breakdown-item.info'), Number(breakdown.low) || 0, 'Low']
        ];
        entries.forEach(([item, count, label]) => {
            const text = item && [...item.childNodes].find(node => node.nodeType === Node.TEXT_NODE);
            if (text) text.nodeValue = ' ' + count + ' ' + label;
        });
    }

    function renderIncidentSummaryFromRecords() {
        if (!Array.isArray(incidentRecords)) return;
        if (dashboardSnapshot?.incidents) {
            updateIncidentSummary(dashboardSnapshot.incidents);
            return;
        }
        const counts = { low: 0, medium: 0, high: 0, critical: 0 };
        incidentRecords.forEach(row => {
            const severity = String(row.severity || '').toLowerCase();
            if (Object.prototype.hasOwnProperty.call(counts, severity)) counts[severity] += 1;
        });
        updateIncidentSummary({ total_incidents: incidentRecords.length, breakdown_by_severity: counts });
    }

    function updateIncidentCategoryOptions() {
        if (!incidentCategoryFilter || !Array.isArray(incidentRecords)) return;
        const selected = incidentCategoryFilter.value || 'all';
        const categories = [...new Set(incidentRecords.map(row => String(row.incident_category || '').toLowerCase()).filter(Boolean))].sort();
        incidentCategoryFilter.replaceChildren(new Option('All', 'all'));
        categories.forEach(category => incidentCategoryFilter.add(new Option(humanize(category), category)));
        incidentCategoryFilter.value = categories.includes(selected) ? selected : 'all';
    }

    function incidentMatchesFilters(row) {
        const status = String(row.status || 'reported').toLowerCase();
        const selectedStatus = incidentStatusFilter?.value || 'all';
        if (selectedStatus === 'open' && status === 'resolved') return false;
        if (selectedStatus === 'in_progress' && status !== 'in_progress') return false;
        if (selectedStatus === 'resolved' && status !== 'resolved') return false;
        const severity = String(row.severity || '').toLowerCase();
        if (incidentSeverityFilter?.value !== 'all' && severity !== incidentSeverityFilter.value) return false;
        const category = String(row.incident_category || '').toLowerCase();
        if (incidentCategoryFilter?.value !== 'all' && category !== incidentCategoryFilter.value) return false;
        const query = String(incidentSearch?.value || '').trim().toLowerCase();
        if (query && ![category, row.description, row.location?.zone, row.location?.address, row.location?.landmark]
            .some(value => String(value || '').toLowerCase().includes(query))) return false;
        return true;
    }

    function renderIncidents() {
        if (!incidentList || !Array.isArray(incidentRecords)) return;
        if (!incidentRecords.length) {
            setApiState(incidentList, 'empty', 'No civic incidents are currently reported.');
            return;
        }
        clearApiState(incidentList);
        incidentList.replaceChildren();
        updateIncidentCategoryOptions();
        const filteredRecords = incidentRecords.filter(incidentMatchesFilters);
        if (!filteredRecords.length) {
            setApiState(incidentList, 'empty', incidentRecords.length ? 'No incidents match the selected filters.' : 'No civic incidents are currently reported.');
            return;
        }
        filteredRecords.forEach(row => {
            const severity = String(row.severity || 'low').toLowerCase();
            const status = String(row.status || 'reported').toLowerCase();
            const item = makeElement('article', 'incident-item ' + (status === 'resolved' ? 'resolved' : 'active') + ' ' + severity + '-severity');
            item.dataset.category = String(row.incident_category || '');
            item.dataset.severity = severity;
            item.dataset.description = row.description || '';
            item.dataset.status = humanize(status);
            item.dataset.location = row.location?.address || row.location?.zone || 'Location unavailable';

            const header = makeElement('div', 'incident-item-header');
            const badgeClass = severity === 'critical' || severity === 'high' ? 'high' : severity === 'medium' ? 'medium' : 'low';
            const badge = makeElement('span', 'incident-badge ' + badgeClass);
            badge.append(makeElement('i', 'ph-fill ' + (severity === 'low' ? 'ph-info' : 'ph-warning-circle')), document.createTextNode(humanize(severity)));
            const date = new Date(row.timestamp);
            const timeText = Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
            const timestamp = makeElement('time', 'incident-time', timeText);
            if (!Number.isNaN(date.getTime())) timestamp.dateTime = date.toISOString();
            header.append(badge, timestamp);

            const content = makeElement('div', 'incident-content');
            content.append(makeElement('strong', '', humanize(row.incident_category)));
            content.append(makeElement('span', 'incident-location', row.location?.zone || 'Location unavailable'));
            content.append(makeElement('span', 'incident-description', row.description || 'No description provided.'));

            const footer = makeElement('div', 'incident-footer');
            footer.append(makeElement('span', 'incident-status ' + (status === 'resolved' ? 'resolved' : 'active'), humanize(status)));
            const details = makeElement('button', 'btn-text view-incident', 'View Details ');
            details.type = 'button';
            details.append(makeElement('i', 'ph ph-caret-right'));
            footer.append(details);
            item.append(header, content, footer);
            incidentList.append(item);
        });
    }

    function notificationSummary(event) {
        const metadata = event.metadata || {};
        if (metadata.description) return String(metadata.description);
        if (event.source === 'traffic') {
            const value = event.value == null ? '' : String(event.value) + (event.unit ? ' ' + event.unit : '');
            const delay = metadata.delay_minutes == null ? '' : String(metadata.delay_minutes) + ' min delay';
            return [value && value + ' congestion', delay].filter(Boolean).join(' · ') || 'Traffic observation';
        }
        if (event.source === 'weather') {
            const condition = metadata.condition ? String(metadata.condition) : '';
            const value = event.value == null ? '' : String(event.value) + (event.unit ? ' ' + event.unit : '');
            return [condition, value && humanize(event.type) + ': ' + value].filter(Boolean).join(' · ') || 'Weather observation';
        }
        const metric = event.value == null ? '' : String(event.value) + (event.unit ? ' ' + event.unit : '');
        return [humanize(event.type) + ' incident', metric].filter(Boolean).join(' · ');
    }

    function createNotificationItem(event) {
        const id = String(event.id);
        const severity = String(event.severity || 'low').toLowerCase();
        const severityStyle = severity === 'critical' ? 'critical' : ['high', 'medium'].includes(severity) ? 'warning' : 'info';
        const item = makeElement('div', 'notification-item ' + (readNotificationIds.has(id) ? 'read' : 'unread') + ' ' + severityStyle);
        item.dataset.notificationId = id;
        const icon = severity === 'critical' ? 'ph-warning-octagon' : event.source === 'traffic' ? 'ph-traffic-cone' : 'ph-warning-circle';
        const notificationIcon = makeElement('div', 'notification-icon');
        notificationIcon.append(makeElement('i', 'ph-fill ' + icon));
        const content = makeElement('div', 'notification-content');
        const title = makeElement('div', 'notification-title');
        title.append(
            makeElement('strong', '', humanize(event.type) || humanize(event.source) + ' update'),
            makeElement('span', 'notification-time', relativeTime(event.timestamp))
        );
        content.append(title, makeElement('p', '', notificationSummary(event)));
        content.append(makeElement('span', 'notification-read-state notification-location', readNotificationIds.has(id) ? 'Read' : 'Unread'));
        content.append(makeElement('span', 'notification-location', event.zone || 'Location unavailable'));
        const provenance = event.metadata?.data_source || (event.source === 'traffic'
            ? 'Stored development traffic · not live'
            : event.source === 'incident' ? 'MongoDB user report · not independently verified' : 'Open-Meteo live weather');
        content.append(makeElement('span', 'notification-location', provenance));
        const actions = makeElement('div', 'notification-actions');
        const view = makeElement('button', 'action-btn view', '');
        view.type = 'button';
        view.title = 'View Details';
        view.setAttribute('aria-label', 'View notification details');
        view.append(makeElement('i', 'ph ph-eye'));
        const dismiss = makeElement('button', 'action-btn dismiss', '');
        dismiss.type = 'button';
        dismiss.title = 'Dismiss';
        dismiss.setAttribute('aria-label', 'Dismiss notification');
        dismiss.append(makeElement('i', 'ph ph-x'));
        actions.append(view, dismiss);
        item.append(notificationIcon, content, actions);
        return item;
    }

    function renderNotificationItems(host, events, emptyMessage) {
        clearApiState(host);
        host.replaceChildren();
        if (!events.length) {
            host.append(makeElement('div', 'api-notification-empty', emptyMessage));
            return;
        }
        events.forEach(event => host.append(createNotificationItem(event)));
    }

    function renderDashboardAlerts() {
        if (!Array.isArray(notificationRecords)) return;
        const visible = notificationRecords
            .filter(event => !dismissedNotificationIds.has(String(event.id)))
            .slice(0, 8);
        renderNotificationItems(notificationBody, visible, 'No notifications are currently available.');
        updateBadgeCount();
    }

    function renderAllNotificationsPanel() {
        if (!Array.isArray(notificationRecords)) return;
        const visible = notificationRecords.filter(event => !dismissedNotificationIds.has(String(event.id)));
        clearApiState(modalBody);
        modalBody.replaceChildren();
        if (!visible.length) {
            setApiState(modalBody, 'empty', 'No notifications are currently available.');
            return;
        }
        const list = makeElement('div', 'dashboard-data-list dashboard-notification-list');
        visible.forEach(event => list.append(createNotificationItem(event)));
        modalBody.append(list);
    }

    function openNotificationDetails(event) {
        const metadata = event.metadata || {};
        const rawId = metadata.raw_id == null ? '' : String(metadata.raw_id);
        const incident = Array.isArray(incidentRecords) ? incidentRecords.find(record => String(record.id) === rawId) : null;
        const traffic = Array.isArray(trafficRecords) ? trafficRecords.find(record => String(record.id) === rawId) : null;
        const title = humanize(event.type) || humanize(event.source) + ' update';
        openDashboardDataPanel(title);
        const details = makeElement('article', 'dashboard-data-record');
        addDashboardDataField(details, 'Type / source:', humanize(event.type) + ' · ' + humanize(event.source));
        addDashboardDataField(details, 'Data provenance:', metadata.data_source || (event.source === 'traffic'
            ? 'Stored development traffic · not live'
            : event.source === 'incident' ? 'MongoDB user report · not independently verified' : 'Open-Meteo live weather'));
        const description = metadata.description || incident?.description || notificationSummary(event);
        addDashboardDataField(details, 'Description:', description || 'Not provided by the source.');
        addDashboardDataField(details, 'Location:', [event.zone, metadata.road_name, metadata.landmark].filter(Boolean).join(' · ') || 'Not provided by the source.');
        addDashboardDataField(details, 'Time:', formatIncidentTimestamp(event.timestamp));
        addDashboardDataField(details, 'Severity:', humanize(event.severity || 'Not reported'));
        if (metadata.status || incident?.status) addDashboardDataField(details, 'Status:', humanize(metadata.status || incident.status));
        if (event.value != null) addDashboardDataField(details, 'Reported value:', String(event.value) + (event.unit ? ' ' + event.unit : ''));
        if (metadata.condition) addDashboardDataField(details, 'Weather condition:', metadata.condition);
        if (metadata.humidity != null) addDashboardDataField(details, 'Humidity:', String(metadata.humidity) + '%');
        if (metadata.wind_speed_kmh != null) addDashboardDataField(details, 'Wind:', String(metadata.wind_speed_kmh) + ' km/h');
        if (metadata.rainfall_mm != null) addDashboardDataField(details, 'Rainfall:', String(metadata.rainfall_mm) + ' mm');
        if (traffic || metadata.delay_minutes != null) {
            const delay = traffic?.delay ?? metadata.delay_minutes;
            if (delay != null) addDashboardDataField(details, 'Traffic delay:', String(delay) + ' min');
            const speed = traffic?.average_speed_kmh ?? metadata.average_speed_kmh;
            if (speed != null) addDashboardDataField(details, 'Average speed:', String(speed) + ' km/h');
        }
        if (incident || traffic) addDashboardDataField(details, 'Related record:', rawId || 'Available in source data');
        modalBody.append(details);
    }

    function handleNotificationAction(event) {
        const button = event.target.closest('.notification-item .view, .notification-item .dismiss');
        if (!button) return;
        const item = button.closest('.notification-item');
        const id = item?.dataset.notificationId;
        const record = notificationRecords?.find(eventRecord => String(eventRecord.id) === id);
        if (!record) return;
        if (button.classList.contains('view')) {
            readNotificationIds.add(id);
            renderDashboardAlerts();
            if (modalTitle.textContent === 'All Notifications') renderAllNotificationsPanel();
            updateBadgeCount();
            openNotificationDetails(record);
            return;
        }
        dismissedNotificationIds.add(id);
        item.style.opacity = '0';
        item.style.transform = 'translateX(20px)';
        item.style.transition = 'all 0.2s ease';
        renderDashboardAlerts();
        if (modalTitle.textContent === 'All Notifications') renderAllNotificationsPanel();
        updateBadgeCount();
    }

    function updateDashboard(data) {
        dashboardSnapshot = data;
        const score = Math.max(0, Math.min(100, Number(data.healthScore) || 0));
        const city = data.city || 'Jaipur';
        const cityName = document.getElementById('city-name');
        if (cityName) cityName.textContent = city === 'Jaipur' ? 'Jaipur, RJ' : city;
        const scoreText = heroSection?.querySelector('.percentage');
        if (scoreText) scoreText.textContent = String(score);
        const circle = heroSection?.querySelector('.circle');
        if (circle) circle.setAttribute('stroke-dasharray', score + ', 100');

        const badge = heroSection?.querySelector('.status-badge');
        if (badge) {
            const label = score >= 70 ? 'Healthy' : score >= 45 ? 'Watch' : 'Needs Attention';
            badge.className = 'status-badge ' + (score >= 70 ? 'status-good' : score >= 45 ? 'status-moderate' : 'status-alert');
            badge.textContent = label;
        }
        const briefing = heroSection?.querySelector('.health-details p');
        if (briefing) briefing.textContent = data.summary || 'City status uses available live weather and user-reported MongoDB incidents. Stored traffic observations are development data.';
        updateDataSourceNote();

        const values = heroSection?.querySelectorAll('.hero-stats .stat-value');
        const labels = heroSection?.querySelectorAll('.hero-stats .stat-label');
        if (values?.[0]) values[0].textContent = formatValue(data.incidents?.active_incidents);
        if (labels?.[0]) labels[0].textContent = 'Active Incidents';
        if (values?.[1]) values[1].textContent = '—';
        if (labels?.[1]) labels[1].textContent = 'Reporting Zones';
        if (Array.isArray(incidentRecords)) updateReportingZonesStat(incidentRecords);
        if (data.timestamp && datetimeElement) {
            const date = new Date(data.timestamp);
            if (!Number.isNaN(date.getTime())) datetimeElement.textContent = date.toLocaleString(undefined, { dateStyle: 'full', timeStyle: 'short' });
        }
        updateIncidentSummary(data.incidents);
        renderRecommendations(data.recommendations || []);
        if (Array.isArray(weatherRecords) && weatherRecords.length) renderWeather();
        if (Array.isArray(trafficRecords) && trafficRecords.length) renderTraffic();
        if (Array.isArray(incidentRecords)) renderIncidentSummaryFromRecords();
    }

    function renderRecommendations(items) {
        if (!recommendationsHost) return;
        clearApiState(recommendationsHost);
        recommendationsHost.replaceChildren();
        if (!Array.isArray(items) || !items.length) {
            recommendationsHost.append(makeElement('p', 'api-notification-empty', 'No current recommendations are indicated by the available data.'));
            return;
        }
        items.forEach(item => {
            const article = makeElement('article', 'recommendation-item');
            article.append(makeElement('strong', '', item.title || 'Data-backed recommendation'));
            article.append(makeElement('p', '', item.message || 'Details unavailable.'));
            article.append(makeElement('small', 'provenance-note', 'Source: ' + (item.source || 'Backend data')));
            recommendationsHost.append(article);
        });
    }

    function updateReportingZonesStat(records) {
        const value = heroStatItems[1]?.querySelector('.stat-value');
        if (!value) return;
        if (!Array.isArray(records)) {
            value.textContent = '—';
            return;
        }
        const zones = new Set(records
            .map(record => String(record.location?.zone || '').trim().toLowerCase())
            .filter(Boolean));
        value.textContent = String(zones.size);
    }

    function openDashboardDataPanel(title) {
        reportMode = false;
        reportForm = null;
        reportSubmitted = false;
        modalTitle.textContent = title;
        modal.querySelector('.modal-content')?.classList.remove('report-mode');
        modal.querySelector('.modal-content')?.classList.add('dashboard-data-mode');
        if (modalFooterCloseBtn) modalFooterCloseBtn.style.display = '';
        modalActionBtn.style.display = 'none';
        modalBody.replaceChildren();
        modal.classList.remove('hidden');
    }

    async function fetchIncidentPages() {
        const allRecords = [];
        const pageSize = 100;
        for (let skip = 0; ; skip += pageSize) {
            const page = requireArray(
                await fetchApi('/incidents?limit=' + pageSize + '&skip=' + skip),
                'incidents'
            );
            allRecords.push(...page);
            if (page.length < pageSize) break;
        }
        return allRecords;
    }

    function addDashboardDataField(container, label, value) {
        const row = makeElement('p', 'dashboard-data-field');
        row.append(makeElement('strong', '', label), document.createTextNode(' ' + value));
        container.append(row);
    }

    function formatIncidentTimestamp(value) {
        const date = new Date(value);
        return Number.isNaN(date.getTime())
            ? 'Time unavailable'
            : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
    }

    function renderActiveIncidentsPanel(records) {
        const active = records.filter(record => String(record.status || '').toLowerCase() !== 'resolved');
        if (!active.length) {
            setApiState(modalBody, 'empty', 'There are no active incidents.');
            return;
        }
        clearApiState(modalBody);
        modalBody.replaceChildren();
        const list = makeElement('div', 'dashboard-data-list');
        active.forEach(record => {
            const category = humanize(record.incident_category || 'Incident');
            const description = String(record.description || 'No description provided.').trim();
            const separator = description.indexOf(' — ');
            const title = String(record.title || (separator >= 0 ? description.slice(0, separator) : description));
            const details = separator >= 0 ? description.slice(separator + 3) : description;
            const location = record.location || {};
            const locationText = [location.zone, location.address, location.landmark, location.road_name]
                .map(value => String(value || '').trim())
                .filter((value, index, values) => value && values.indexOf(value) === index)
                .join(' · ') || 'Location unavailable';
            const article = makeElement('article', 'dashboard-data-record');
            article.append(makeElement('h4', '', title));
            addDashboardDataField(article, 'Category:', category);
            addDashboardDataField(article, 'Description:', details);
            addDashboardDataField(article, 'Location:', locationText);
            addDashboardDataField(article, 'Severity:', humanize(record.severity || 'unknown'));
            addDashboardDataField(article, 'Status:', humanize(record.status || 'unknown'));
            addDashboardDataField(article, 'Date/Time:', formatIncidentTimestamp(record.timestamp));
            list.append(article);
        });
        modalBody.append(list);
    }

    async function loadActiveIncidentsPanel() {
        setApiState(modalBody, 'loading', 'Loading active incidents…');
        try {
            renderActiveIncidentsPanel(await fetchIncidentPages());
        } catch (error) {
            setApiState(modalBody, 'error', error.message || 'Could not load active incidents.', loadActiveIncidentsPanel);
        }
    }

    function renderReportingZonesPanel(records) {
        const zones = new Map();
        records.forEach(record => {
            const name = String(record.location?.zone || '').trim();
            if (!name) return;
            const key = name.toLowerCase();
            if (!zones.has(key)) zones.set(key, { name, records: [] });
            zones.get(key).records.push(record);
        });
        if (!zones.size) {
            setApiState(modalBody, 'empty', 'No reporting zones can be derived from the incident locations.');
            return;
        }
        clearApiState(modalBody);
        modalBody.replaceChildren();
        const list = makeElement('div', 'dashboard-data-list');
        [...zones.values()].sort((a, b) => a.name.localeCompare(b.name)).forEach(zone => {
            const severities = {};
            const statuses = {};
            zone.records.forEach(record => {
                const severity = humanize(record.severity || 'unknown');
                const status = humanize(record.status || 'unknown');
                severities[severity] = (severities[severity] || 0) + 1;
                statuses[status] = (statuses[status] || 0) + 1;
            });
            const article = makeElement('article', 'dashboard-data-record dashboard-zone-record');
            article.append(makeElement('h4', '', zone.name));
            addDashboardDataField(article, 'Incidents:', String(zone.records.length));
            addDashboardDataField(article, 'Severity:', Object.entries(severities).map(([label, count]) => label + ' ' + count).join(' · '));
            addDashboardDataField(article, 'Status:', Object.entries(statuses).map(([label, count]) => label + ' ' + count).join(' · '));
            list.append(article);
        });
        modalBody.append(list);
    }

    async function loadReportingZonesPanel() {
        setApiState(modalBody, 'loading', 'Loading reporting zones…');
        try {
            renderReportingZonesPanel(await fetchIncidentPages());
        } catch (error) {
            setApiState(modalBody, 'error', error.message || 'Could not load reporting zones.', loadReportingZonesPanel);
        }
    }

    function updateDataSourceNote() {
        const note = document.getElementById('data-source-note');
        if (!note) return '';
        const sources = dashboardSnapshot?.data_sources;
        if (sources && typeof sources === 'object') {
            note.textContent = [
                'Weather: ' + (sources.weather || 'unavailable'),
                'Traffic: ' + (sources.traffic || 'unavailable'),
                'Incidents: ' + (sources.incidents || 'unavailable'),
                'Crowd: ' + (sources.crowd_prediction || 'unavailable')
            ].join(' · ');
            return note.textContent;
        }
        if (!dataSourceLabel) return note.textContent = 'Data source could not be verified.';
        const source = dataSourceLabel.toLowerCase();
        note.textContent = source.includes('synthetic') || source.includes('local')
            ? 'Development data · ' + dataSourceLabel
            : 'Backend data source · ' + dataSourceLabel;
        return note.textContent;
    }

    async function loadDataSource() {
        try {
            const health = await fetchApi('/health');
            dataSourceLabel = health?.database?.activeDataSource || 'Backend API';
        } catch (error) {
            dataSourceLabel = null;
        }
        updateDataSourceNote();
    }

    function clearMapMarkers() {
        mapMarkers.forEach(({ marker }) => marker.remove());
        mapMarkers = [];
        mapArea?.querySelector('.api-map-state')?.remove();
    }

    mapZoomControls.forEach(button => {
        const icon = button.querySelector('i');
        if (icon?.classList.contains('ph-plus')) {
            button.setAttribute('aria-label', 'Zoom in');
            button.addEventListener('click', () => cityMap?.zoomIn());
        } else if (icon?.classList.contains('ph-minus')) {
            button.setAttribute('aria-label', 'Zoom out');
            button.addEventListener('click', () => cityMap?.zoomOut());
        } else if (icon?.classList.contains('ph-crosshair')) {
            button.setAttribute('aria-label', 'Reset map view');
            button.addEventListener('click', () => cityMap?.setView([26.9124, 75.7873], mapArea?.clientWidth <= 420 ? 10 : 12));
        } else if (icon?.classList.contains('ph-layers')) {
            button.setAttribute('aria-label', 'Toggle map legend');
            button.setAttribute('aria-pressed', 'false');
            button.addEventListener('click', () => {
                const hidden = mapLegend?.classList.toggle('hidden') || false;
                button.setAttribute('aria-pressed', String(hidden));
            });
        }
    });

    function renderCivicEvents() {
        if (!mapArea || !Array.isArray(civicEvents)) return;
        clearMapMarkers();
        const events = civicEvents.filter(event => {
            const lat = event?.latitude, lon = event?.longitude;
            return lat !== null && lat !== undefined && lat !== '' && lon !== null && lon !== undefined && lon !== '' &&
                Number.isFinite(Number(lat)) && Number.isFinite(Number(lon)) && Number(lat) >= -90 && Number(lat) <= 90 && Number(lon) >= -180 && Number(lon) <= 180;
        });
        const unmapped = civicEvents.filter(event => !events.includes(event));
        const unmappedPanel = mapArea.querySelector('.map-unmapped');
        const unmappedList = unmappedPanel?.querySelector('.map-unmapped-list');
        if (unmappedPanel && unmappedList) {
            unmappedList.replaceChildren();
            unmappedPanel.hidden = unmapped.length === 0;
            unmapped.forEach(event => {
                const item = makeElement('p', 'map-unmapped-item');
                item.textContent = [event.title || humanize(event.type || event.source || 'Event'), event.zone || event.location || 'Location unavailable', 'Coordinates unavailable or invalid'].join(' · ');
                unmappedList.append(item);
            });
        }
        let map;
        try { map = initializeCityMap(); }
        catch (error) { setMapState('error', error.message || 'The interactive map could not load.', loadCivicEvents); return; }
        if (!events.length) {
            setMapState('empty', civicEvents.length ? 'No civic events have valid coordinates to place on the map.' : 'No civic events are currently available.');
            return;
        }
        mapArea.querySelector('.api-map-state')?.remove();
        const coordinateGroups = new Map();
        events.forEach(event => {
            const source = String(event.source || 'incident').toLowerCase();
            const key = source + ':' + Number(event.latitude) + ',' + Number(event.longitude);
            if (!coordinateGroups.has(key)) coordinateGroups.set(key, []);
            coordinateGroups.get(key).push(event);
        });

        coordinateGroups.forEach(groupEvents => {
            const event = groupEvents[0];
            const source = String(event.source || 'incident').toLowerCase();
            const severity = String(event.severity || 'low').toLowerCase();
            const metadata = event.metadata || {};
            const iconName = source === 'traffic' ? 'ph-traffic-cone' : source === 'weather' ? 'ph-cloud-sun' : 'ph-warning-circle';
            const icon = window.L.divIcon({
                className: 'citypulse-marker-icon citypulse-' + source + ' severity-' + severity,
                html: '<span class="citypulse-marker-pin"><i class="ph-fill ' + iconName + '"></i></span>' + (groupEvents.length > 1 ? '<span class="citypulse-marker-count">' + groupEvents.length + '</span>' : ''),
                iconSize: [34, 42],
                iconAnchor: [17, 38],
                popupAnchor: [0, -36]
            });
            const marker = window.L.marker([Number(event.latitude), Number(event.longitude)], { icon, title: humanize(event.type) + ' · ' + (event.zone || 'Citywide') }).addTo(map);
            const applyMarkerAttributes = () => {
                const el = marker.getElement();
                if (!el) return;
                el.dataset.source = source;
                el.dataset.eventId = String(event.id || '');
                el.dataset.eventCount = String(groupEvents.length);
                el.dataset.latitude = String(Number(event.latitude));
                el.dataset.longitude = String(Number(event.longitude));
                el.setAttribute('aria-label', humanize(event.type) + ' in ' + (event.zone || 'Citywide'));
            };
            marker.on('add', applyMarkerAttributes);
            applyMarkerAttributes();
            const popup = makeElement('div', 'citypulse-map-popup');
            if (mapArea.clientWidth <= 420) popup.style.width = '190px';
            if (groupEvents.length > 1) popup.append(makeElement('strong', 'citypulse-popup-title', groupEvents.length + ' events at this location'));
            groupEvents.forEach((groupEvent, index) => {
                const groupMetadata = groupEvent.metadata || {};
                const details = makeElement('section', 'citypulse-popup-event');
                details.append(makeElement('strong', 'citypulse-popup-title', groupEvent.title || humanize(groupEvent.type)));
                const locationName = groupMetadata.road_name || groupMetadata.landmark || groupEvent.zone || 'Location not provided';
                const dataSource = groupMetadata.data_source || (source === 'incident' ? 'MongoDB user-reported · not independently verified' : source === 'traffic' ? 'Stored development observation · not live traffic' : 'Open-Meteo weather');
                const fields = [
                    ['Category / type', humanize(groupEvent.type || source)],
                    ['Severity', humanize(groupEvent.severity || severity)],
                    ['Status', groupMetadata.status ? humanize(groupMetadata.status) : source === 'incident' ? 'Reported' : 'Observed'],
                    ['Location', locationName],
                    ['Data source', dataSource],
                    ['Date / time', groupEvent.timestamp ? new Date(groupEvent.timestamp).toLocaleString() : 'Unavailable']
                ];
                if (groupEvent.value !== null && groupEvent.value !== undefined) fields.push(['Reading', String(groupEvent.value) + (groupEvent.unit ? ' ' + groupEvent.unit : '')]);
                if (groupMetadata.description) fields.push(['Description', String(groupMetadata.description)]);
                if (groupMetadata.delay_minutes !== null && groupMetadata.delay_minutes !== undefined) fields.push(['Delay', formatValue(groupMetadata.delay_minutes, 1) + ' min']);
                fields.forEach(([label, value]) => {
                    const row = makeElement('p', 'citypulse-popup-row');
                    row.append(makeElement('span', 'citypulse-popup-label', label));
                    row.append(makeElement('span', 'citypulse-popup-value', value));
                    details.append(row);
                });
                popup.append(details);
                if (index < groupEvents.length - 1) popup.append(makeElement('hr', 'citypulse-popup-divider'));
            });
            marker.bindPopup(popup, { maxWidth: 290, maxHeight: 320 });
            mapMarkers.push({ marker, source });
        });
        applyCivicEventFilter();
    }

    function applyCivicEventFilter() {
        if (!Array.isArray(civicEvents) || !mapArea) return;
        const active = [...mapBtns].find(button => button.classList.contains('active'));
        const label = active?.textContent.trim().toLowerCase() || 'all';
        const source = label.includes('traffic') ? 'traffic' : label.includes('incident') ? 'incident' : label.includes('weather') ? 'weather' : 'all';
        let visible = 0;
        mapMarkers.forEach(({ marker, source: markerSource }) => {
            const shouldShow = source === 'all' || markerSource === source;
            if (shouldShow && !cityMap.hasLayer(marker)) marker.addTo(cityMap);
            if (!shouldShow && cityMap.hasLayer(marker)) cityMap.removeLayer(marker);
            if (shouldShow) visible += 1;
        });
        if (!visible) setMapState('empty', 'No backend civic events match this map layer.');
        else mapArea.querySelector('.api-map-state')?.remove();
    }

    function renderReportBars(host, values) {
        if (!host) return;
        host.replaceChildren();
        const entries = Object.entries(values || {})
            .map(([label, value]) => [label, Number(value)])
            .filter(([, value]) => Number.isFinite(value) && value >= 0)
            .sort((a, b) => b[1] - a[1]);
        if (!entries.length || entries.every(([, value]) => value === 0)) {
            host.append(makeElement('p', 'report-chart-empty', 'No data available.'));
            return;
        }
        const max = Math.max(...entries.map(([, value]) => value));
        entries.forEach(([label, value]) => {
            const row = makeElement('div', 'report-bar-row');
            const heading = makeElement('div', 'report-bar-heading');
            heading.append(makeElement('span', '', humanize(label)), makeElement('strong', '', formatValue(value)));
            const track = makeElement('div', 'report-bar-track');
            const fill = makeElement('span', 'report-bar-fill');
            fill.style.width = Math.max(value > 0 ? 2 : 0, value / max * 100) + '%';
            track.append(fill);
            row.append(heading, track);
            host.append(row);
        });
    }

    function availablePredictionZones() {
        const zones = new Set();
        [weatherRecords, trafficRecords].forEach(records => {
            if (Array.isArray(records)) records.forEach(record => {
                const zone = record.location?.zone;
                if (zone) zones.add(zone);
            });
        });
        if (!zones.size && Array.isArray(incidentRecords)) incidentRecords.forEach(record => {
            const zone = record.location?.zone;
            if (zone) zones.add(zone);
        });
        return [...zones].sort((a, b) => a.localeCompare(b));
    }

    async function predictCrowdForZone(zone) {
        const payload = predictionInputFromCurrentData(zone);
        return fetchApi('/predictions/crowd', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    async function loadReports() {
        if (!reportsContent) return;
        setApiState(reportsContent, 'loading', 'Loading city reports…', loadReports);
        try {
            const incidentSummary = dashboardSnapshot?.incidents;
            if (!incidentSummary && !Array.isArray(incidentRecords)) {
                throw new Error('Incident report data is unavailable. Retry after the backend is reachable.');
            }

            const incidents = Array.isArray(incidentRecords) ? incidentRecords : null;
            const total = incidentSummary?.total_incidents ?? incidents?.length;
            const open = incidents
                ? incidents.filter(row => String(row.status).toLowerCase() !== 'resolved').length
                : incidentSummary?.active_incidents;
            const resolved = incidents
                ? incidents.filter(row => String(row.status).toLowerCase() === 'resolved').length
                : incidentSummary?.resolved_incidents;
            const categoryCounts = incidentSummary?.breakdown_by_category || (incidents || []).reduce((counts, row) => {
                const category = String(row.incident_category || 'unknown').toLowerCase();
                counts[category] = (counts[category] || 0) + 1;
                return counts;
            }, {});
            const severityCounts = incidentSummary?.breakdown_by_severity || (incidents || []).reduce((counts, row) => {
                const severity = String(row.severity || 'unknown').toLowerCase();
                counts[severity] = (counts[severity] || 0) + 1;
                return counts;
            }, {});
            const trafficSummary = dashboardSnapshot?.traffic || {};
            const congestion = trafficSummary.average_congestion ?? mean(trafficRecords || [], row => row.congestion_percentage);
            const delay = trafficSummary.average_delay_minutes ?? mean(trafficRecords || [], row => row.delay);

            document.getElementById('report-total-incidents').textContent = formatValue(total);
            document.getElementById('report-open-incidents').textContent = formatValue(open);
            document.getElementById('report-resolved-incidents').textContent = formatValue(resolved);
            document.getElementById('report-average-congestion').textContent = congestion == null ? '—' : formatValue(congestion, 1, '%');
            document.getElementById('report-average-delay').textContent = delay == null ? '—' : formatValue(delay, 1, ' min');
            renderReportBars(document.getElementById('report-category-chart'), categoryCounts);
            renderReportBars(document.getElementById('report-severity-chart'), severityCounts);

            const zones = availablePredictionZones();
            const results = await Promise.allSettled(zones.map(async zone => {
                if (predictionSnapshot && predictionZone === zone) return { zone, prediction: predictionSnapshot };
                return { zone, prediction: await predictCrowdForZone(zone) };
            }));
            reportPredictions = results.filter(result => result.status === 'fulfilled').map(result => result.value);
            const crowdCounts = reportPredictions.reduce((counts, result) => {
                const level = String(result.prediction?.crowd_level || '').toLowerCase();
                if (['low', 'moderate', 'high'].includes(level)) counts[level] = (counts[level] || 0) + 1;
                return counts;
            }, {});
            renderReportBars(document.getElementById('report-crowd-chart'), crowdCounts);
            const failedPredictions = results.length - reportPredictions.length;
            if (failedPredictions) {
                const note = document.getElementById('reports-data-note');
                note.textContent = 'Crowd predictions loaded for ' + reportPredictions.length + ' of ' + zones.length + ' zones. Retry to refresh missing predictions.';
                note.classList.add('is-warning');
            }

            clearApiState(reportsContent);
            const dataNote = document.getElementById('reports-data-note');
            if (!failedPredictions) dataNote.textContent = updateDataSourceNote() + ' · Reports use current backend observations. Crowd distribution is a model prediction; training data is synthetic and not real-world validated.';
            if (!failedPredictions) dataNote.classList.remove('is-warning');
        } catch (error) {
            setApiState(reportsContent, 'error', error.message || 'Could not load city reports.', loadReports);
        }
    }

    async function loadDashboard() {
        dashboardSnapshot = null;
        setApiState(heroSection, 'loading', 'Loading citywide dashboard…', loadDashboard);
        setApiState(incidentSummaryHost, 'loading', 'Loading incident summary…', loadDashboard);
        if (recommendationsHost) recommendationsHost.replaceChildren();
        if (recommendationsHost) setApiState(recommendationsHost, 'loading', 'Generating recommendations from available live data…', loadDashboard);
        try {
            const data = await fetchApi('/dashboard');
            if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('The dashboard endpoint returned an unexpected response.');
            clearApiState(heroSection);
            updateDashboard(data);
        } catch (error) {
            const message = error.message || 'Could not load dashboard data.';
            setApiState(heroSection, 'error', message, loadDashboard);
            if (recommendationsHost) recommendationsHost.replaceChildren();
            setApiState(recommendationsHost, 'error', message, loadDashboard);
            if (!Array.isArray(incidentRecords)) setApiState(incidentSummaryHost, 'error', message, loadDashboard);
        }
    }

    async function loadWeather(forceRefresh = false) {
        const sourceNote = weatherBody?.querySelector('.weather-source-note');
        if (sourceNote) sourceNote.textContent = 'Checking live weather · Open-Meteo';
        setApiState(weatherBody, 'loading', 'Loading weather observations…', loadWeather);
        try {
            weatherRecords = requireArray(await fetchApi('/weather?limit=100' + (forceRefresh ? '&refresh=true' : '')), 'weather');
            if (!weatherRecords.length) return setApiState(weatherBody, 'empty', 'No weather observations are currently available.');
            clearApiState(weatherBody);
            renderWeather();
        } catch (error) {
            weatherRecords = null;
            if (sourceNote) sourceNote.textContent = 'Weather unavailable · Open-Meteo';
            setApiState(weatherBody, 'error', error.message || 'Could not load weather observations.', loadWeather);
        }
    }

    async function loadTraffic() {
        setApiState(trafficBody, 'loading', 'Loading traffic observations…', loadTraffic);
        try {
            trafficRecords = requireArray(await fetchApi('/traffic?limit=100'), 'traffic');
            if (!trafficRecords.length) return setApiState(trafficBody, 'empty', 'No traffic observations are currently available.');
            clearApiState(trafficBody);
            renderTraffic();
        } catch (error) {
            trafficRecords = null;
            setApiState(trafficBody, 'error', error.message || 'Could not load traffic observations.', loadTraffic);
        }
    }

    async function loadIncidents() {
        setApiState(incidentList, 'loading', 'Loading civic incidents…', loadIncidents);
        try {
            incidentRecords = requireArray(await fetchApi('/incidents?limit=100'), 'incidents');
            updateReportingZonesStat(incidentRecords);
            clearApiState(incidentList);
            renderIncidentSummaryFromRecords();
            renderIncidents();
        } catch (error) {
            incidentRecords = null;
            updateReportingZonesStat(null);
            setApiState(incidentList, 'error', error.message || 'Could not load civic incidents.', loadIncidents);
        }
    }

    async function fetchAllCivicEvents() {
        const records = [];
        const pageSize = 100;
        for (let skip = 0; ; skip += pageSize) {
            const page = requireArray(
                await fetchApi('/civic-events?limit=' + pageSize + '&skip=' + skip),
                'civic events'
            );
            records.push(...page);
            if (page.length < pageSize) return records;
        }
    }

    async function loadAllNotificationsPanel() {
        setApiState(modalBody, 'loading', 'Loading all notifications…', loadAllNotificationsPanel);
        try {
            notificationRecords = await fetchAllCivicEvents();
            renderDashboardAlerts();
            renderAllNotificationsPanel();
        } catch (error) {
            setApiState(modalBody, 'error', error.message || 'Could not load notifications.', loadAllNotificationsPanel);
        }
    }

    async function loadCivicEvents() {
        civicEvents = null;
        notificationRecords = null;
        updateBadgeCount();
        clearMapMarkers();
        try { initializeCityMap(); }
        catch (error) {
            setMapState('error', error.message || 'The interactive map could not load.', loadCivicEvents);
        }
        setMapState('loading', 'Loading civic events…', loadCivicEvents);
        setApiState(notificationBody, 'loading', 'Loading notifications…', loadCivicEvents);
        try {
            civicEvents = await fetchAllCivicEvents();
            notificationRecords = civicEvents;
            renderCivicEvents();
            renderDashboardAlerts();
        } catch (error) {
            civicEvents = null;
            notificationRecords = null;
            clearMapMarkers();
            setMapState('error', error.message || 'Could not load civic events.', loadCivicEvents);
            setApiState(notificationBody, 'error', error.message || 'Could not load notifications.', loadCivicEvents);
            updateBadgeCount();
        }
    }

    function latestRecordForZone(records, zone) {
        if (!Array.isArray(records)) return null;
        return records
            .filter(record => record.location?.zone === zone)
            .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0] || null;
    }

    function predictionInputFromCurrentData(preferredZone = null) {
        const weatherByZone = new Map();
        (Array.isArray(weatherRecords) ? weatherRecords : []).forEach(record => {
            const zone = record.location?.zone;
            if (zone && (!weatherByZone.has(zone) || new Date(record.timestamp) > new Date(weatherByZone.get(zone).timestamp))) {
                weatherByZone.set(zone, record);
            }
        });
        let zone = preferredZone && weatherByZone.has(preferredZone) ? preferredZone : null;
        if (!zone) zone = [...weatherByZone.entries()]
            .sort((a, b) => new Date(b[1].timestamp).getTime() - new Date(a[1].timestamp).getTime())[0]?.[0];
        if (!zone && Array.isArray(incidentRecords)) {
            zone = [...incidentRecords]
                .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())[0]
                ?.location?.zone;
        }
        if (!zone) throw new Error('No city observations are available to build a crowd prediction.');

        const weather = latestRecordForZone(weatherRecords, zone);
        const zoneIncidents = Array.isArray(incidentRecords)
            ? incidentRecords.filter(record => record.location?.zone === zone)
            : null;
        const activeIncidents = zoneIncidents?.filter(record => record.status !== 'resolved') || null;
        const urgentIncidents = zoneIncidents?.filter(record => ['high', 'critical'].includes(String(record.severity).toLowerCase())) || null;

        return {
            timestamp: new Date().toISOString(),
            zone,
            temperature_c: weather?.temperature ?? null,
            rainfall_mm: weather?.rainfall ?? null,
            humidity_pct: weather?.humidity ?? null,
            wind_speed_kmh: weather?.wind_speed_kmh ?? null,
            air_quality_index: weather?.air_quality_index ?? null,
            weather_condition: weather?.weather_condition ?? null,
            incident_count: zoneIncidents === null ? null : zoneIncidents.length,
            active_incident_count: activeIncidents === null ? null : activeIncidents.length,
            high_critical_incident_count: urgentIncidents === null ? null : urgentIncidents.length
        };
    }

    function renderCrowdPrediction(prediction, zone, timestamp) {
        const level = String(prediction?.crowd_level || '').toLowerCase();
        if (!['low', 'moderate', 'high'].includes(level)) {
            throw new Error('The crowd prediction endpoint returned an unsupported crowd level.');
        }

        const probabilities = prediction.probabilities && typeof prediction.probabilities === 'object' && !Array.isArray(prediction.probabilities)
            ? Object.entries(prediction.probabilities)
                .map(([name, value]) => [name.toLowerCase(), Number(value)])
                .filter(([name, value]) => ['low', 'moderate', 'high'].includes(name) && Number.isFinite(value) && value >= 0 && value <= 1)
            : [];
        const highestProbability = probabilities.length
            ? Math.max(...probabilities.map(([, value]) => value))
            : Number(prediction.confidence);
        if (!Number.isFinite(highestProbability) || highestProbability < 0 || highestProbability > 1) {
            throw new Error('The crowd prediction endpoint returned invalid confidence data.');
        }

        const levelValue = crowdPredictionBody.querySelector('.level-val');
        if (levelValue) levelValue.textContent = humanize(level);
        const levelLabel = crowdPredictionBody.querySelector('.level-lbl');
        const predictedTime = new Date(timestamp).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
        if (levelLabel) levelLabel.textContent = 'For ' + zone + ' · ' + predictedTime;
        const confidenceValue = crowdPredictionBody.querySelector('.conf-val');
        if (confidenceValue) confidenceValue.textContent = Math.round(highestProbability * 100) + '%';

        const chart = crowdPredictionBody.querySelector('.simple-chart');
        if (chart) {
            chart.replaceChildren();
            ['low', 'moderate', 'high'].forEach(name => {
                const value = probabilities.find(([label]) => label === name)?.[1];
                if (value === undefined) return;
                const bar = makeElement('div', 'chart-bar' + (name === level ? ' highlight' : ''));
                bar.style.height = Math.max(value > 0 ? 4 : 0, value * 100) + '%';
                bar.title = humanize(name) + ' probability: ' + (value * 100).toFixed(1) + '%';
                bar.setAttribute('aria-label', bar.title);
                bar.append(makeElement('span', 'bar-lbl', humanize(name)));
                chart.append(bar);
            });
        }

        const insight = crowdPredictionBody.querySelector('.insight-text');
        if (insight) {
            const icon = insight.querySelector('i') || makeElement('i', 'ph ph-info');
            insight.replaceChildren(icon, document.createTextNode(' Prediction updated for ' + zone + ' at ' + predictedTime + '.'));
        }
        clearApiState(crowdPredictionBody);
        crowdPredictionBody.dataset.predictionState = 'success';
        crowdPredictionBody.setAttribute('aria-busy', 'false');
    }

    async function loadCrowdPrediction() {
        setApiState(crowdPredictionBody, 'loading', 'Loading crowd prediction…');
        crowdPredictionBody.dataset.predictionState = 'loading';
        try {
            const payload = predictionInputFromCurrentData();
            const result = await fetchApi('/predictions/crowd', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            predictionSnapshot = result;
            predictionZone = payload.zone;
            predictionTimestamp = payload.timestamp;
            renderCrowdPrediction(result, payload.zone, payload.timestamp);
            return true;
        } catch (error) {
            crowdPredictionBody.dataset.predictionState = 'error';
            setApiState(crowdPredictionBody, 'error', error.message || 'Could not load the crowd prediction.', retryCrowdPrediction);
            return false;
        }
    }

    function renderCrowdPredictionPanel() {
        if (!predictionSnapshot) {
            setApiState(modalBody, 'empty', 'No crowd prediction is currently available.');
            return;
        }
        clearApiState(modalBody);
        modalBody.replaceChildren();
        const details = makeElement('article', 'dashboard-data-record');
        details.append(makeElement('h4', '', 'Prediction for ' + (predictionZone || 'current zone')));
        addDashboardDataField(details, 'Predicted crowd level:', humanize(predictionSnapshot.crowd_level));
        const probabilities = predictionSnapshot.probabilities;
        if (probabilities && typeof probabilities === 'object' && !Array.isArray(probabilities)) {
            ['low', 'moderate', 'high'].forEach(level => {
                const probability = probabilities[level];
                if (probability != null && Number.isFinite(Number(probability))) {
                    addDashboardDataField(details, humanize(level) + ' probability:', (Number(probability) * 100).toFixed(1) + '%');
                }
            });
        } else {
            addDashboardDataField(details, 'Probabilities:', 'Not provided by the prediction API.');
        }
        addDashboardDataField(details, 'Last updated:', formatIncidentTimestamp(predictionTimestamp));
        modalBody.append(details);
        const modelNote = crowdPredictionBody.querySelector('.ml-model-note')?.textContent.trim();
        if (modelNote) modalBody.append(makeElement('p', 'dashboard-data-note', modelNote));
    }

    async function loadCrowdPredictionPanel() {
        setApiState(modalBody, 'loading', 'Loading crowd prediction…');
        if (!Array.isArray(weatherRecords) || !Array.isArray(trafficRecords) || !Array.isArray(incidentRecords)) {
            await Promise.allSettled([loadWeather(), loadTraffic(), loadIncidents()]);
        }
        const loaded = await loadCrowdPrediction();
        if (loaded) {
            renderCrowdPredictionPanel();
            return;
        }
        const message = crowdPredictionBody.querySelector('.api-state-message')?.textContent || 'Could not load the crowd prediction.';
        setApiState(modalBody, 'error', message, loadCrowdPredictionPanel);
    }

    async function retryCrowdPrediction() {
        setApiState(crowdPredictionBody, 'loading', 'Refreshing city observations and retrying…');
        await Promise.allSettled([loadWeather(), loadTraffic(), loadIncidents()]);
        await loadCrowdPrediction();
    }

    async function loadAllData() {
        setApiState(crowdPredictionBody, 'loading', 'Loading crowd prediction…');
        crowdPredictionBody.dataset.predictionState = 'loading';
        await Promise.allSettled([loadDashboard(), loadWeather(), loadTraffic(), loadIncidents(), loadCivicEvents(), loadDataSource()]);
        await loadCrowdPrediction();
        await loadReports();
    }

    const dashboardStatActions = [
        { label: 'View active incidents', title: 'Active Incidents', load: loadActiveIncidentsPanel },
        { label: 'View reporting zones', title: 'Reporting Zones', load: loadReportingZonesPanel }
    ];
    heroStatItems.forEach((item, index) => {
        const action = dashboardStatActions[index];
        if (!action) return;
        item.setAttribute('role', 'button');
        item.setAttribute('tabindex', '0');
        item.setAttribute('aria-label', action.label);
        item.setAttribute('aria-haspopup', 'dialog');
        const activate = () => {
            openDashboardDataPanel(action.title);
            action.load();
        };
        item.addEventListener('click', activate);
        item.addEventListener('keydown', event => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            activate();
        });
    });

    document.querySelector('.weather-card .card-footer .btn-text')?.addEventListener('click', () => {
        openDashboardDataPanel('Weather Forecast');
        loadWeatherForecastPanel();
    });

    document.querySelector('.traffic-card .card-footer .btn-text')?.addEventListener('click', () => {
        openDashboardDataPanel('Traffic Details');
        loadTrafficDetailsPanel();
    });

    document.querySelector('.ml-insights-card .card-footer .btn-text')?.addEventListener('click', () => {
        openDashboardDataPanel('Crowd Prediction');
        loadCrowdPredictionPanel();
    });

    refreshBtn.addEventListener('click', async () => {
        const icon = refreshBtn.querySelector('i');
        refreshBtn.disabled = true;
        icon?.classList.add('ph-spin');
        try {
            await loadAllData();
        } finally {
            refreshBtn.disabled = false;
            icon?.classList.remove('ph-spin');
        }
    });

    document.querySelectorAll('.icon-btn-small[title="Refresh"]').forEach(button => {
        button.addEventListener('click', () => {
            const card = button.closest('.card');
            if (card?.classList.contains('weather-card')) loadWeather(true);
            if (card?.classList.contains('traffic-card')) loadTraffic();
        });
    });

    mapBtns.forEach(button => button.addEventListener('click', applyCivicEventFilter));

    [incidentSearch, incidentStatusFilter, incidentSeverityFilter, incidentCategoryFilter].forEach(control => {
        control?.addEventListener('input', renderIncidents);
        control?.addEventListener('change', renderIncidents);
    });

    reportsRefreshBtn?.addEventListener('click', async () => {
        reportsRefreshBtn.disabled = true;
        const icon = reportsRefreshBtn.querySelector('i');
        icon?.classList.add('ph-spin');
        try {
            await loadAllData();
        } finally {
            reportsRefreshBtn.disabled = false;
            icon?.classList.remove('ph-spin');
        }
    });

    notifPanel.addEventListener('click', event => {
        const dismiss = event.target.closest('.action-btn.dismiss');
        if (!dismiss) return;
        const item = dismiss.closest('.notification-item');
        if (!item) return;
        item.style.opacity = '0';
        item.style.transform = 'translateX(20px)';
        item.style.transition = 'all 0.3s ease';
        window.setTimeout(() => {
            item.remove();
            updateBadgeCount();
        }, 300);
    });

    document.addEventListener('click', event => {
        const button = event.target.closest('.view-incident');
        if (!button) return;
        const item = button.closest('.incident-item');
        if (!item) return;
        event.preventDefault();
        const category = item.querySelector('.incident-content strong')?.textContent || 'Incident';
        const title = item.querySelector('.incident-content .incident-description')?.textContent || category;
        const severity = item.querySelector('.incident-badge')?.textContent.trim() || 'Not reported';
        const time = item.querySelector('.incident-time')?.textContent || 'Time unavailable';
        openModal(title, [
            'Category: ' + category,
            'Description: ' + item.dataset.description,
            'Location: ' + item.dataset.location,
            'Severity: ' + severity,
            'Status: ' + item.dataset.status,
            'Date/Time: ' + time
        ].join('\n'));
    });

    loadAllData();

});
