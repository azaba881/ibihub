/**
 * Mini-calendrier IbiHub — disponible (vert) / occupé (rouge).
 * Public : lecture seule. Admin : clic pour basculer, persistance localStorage.
 */
(function (global) {
  'use strict';

  var STORAGE_KEY = 'ibihub_space_demo_occupied';

  function pad(n) {
    return n < 10 ? '0' + n : String(n);
  }

  function iso(d) {
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }

  var MONTHS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  var DAYS_FR = ['lun', 'mar', 'mer', 'jeu', 'ven', 'sam', 'dim'];

  function loadSet() {
    try {
      var raw = global.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var arr = JSON.parse(raw);
        if (Array.isArray(arr)) return new Set(arr);
      }
    } catch (e) {}
    return null;
  }

  function saveSet(set) {
    try {
      global.localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(set)));
    } catch (e) {}
  }

  function defaultDemoOccupied() {
    var now = new Date();
    var y = now.getFullYear();
    var m = now.getMonth();
    var out = [];
    for (var i = 5; i <= 9; i++) {
      out.push(iso(new Date(y, m, i)));
    }
    out.push(iso(new Date(y, m, 18)));
    out.push(iso(new Date(y, m, 19)));
    return new Set(out);
  }

  function getOccupiedSet(fallbackDemo) {
    var s = loadSet();
    if (s && s.size) return s;
    return fallbackDemo ? defaultDemoOccupied() : new Set();
  }

  function buildGrid(container, state) {
    var year = state.year;
    var month = state.month;
    var occupiedSet = state.occupiedSet;
    var mode = state.mode;

    container.innerHTML = '';
    var head = document.createElement('div');
    head.className = 'ibihub-cal__header';
    var prev = document.createElement('button');
    prev.type = 'button';
    prev.className = 'ibihub-cal__nav';
    prev.setAttribute('aria-label', 'Mois précédent');
    prev.innerHTML = '<i class="fa fa-chevron-left"></i>';
    var title = document.createElement('div');
    title.className = 'ibihub-cal__title';
    title.textContent = MONTHS_FR[month] + ' ' + year;
    var next = document.createElement('button');
    next.type = 'button';
    next.className = 'ibihub-cal__nav';
    next.setAttribute('aria-label', 'Mois suivant');
    next.innerHTML = '<i class="fa fa-chevron-right"></i>';
    head.appendChild(prev);
    head.appendChild(title);
    head.appendChild(next);
    container.appendChild(head);

    var dow = document.createElement('div');
    dow.className = 'ibihub-cal__dow';
    for (var d = 0; d < 7; d++) {
      var c = document.createElement('span');
      c.textContent = DAYS_FR[d];
      dow.appendChild(c);
    }
    container.appendChild(dow);

    var grid = document.createElement('div');
    grid.className = 'ibihub-cal__grid';

    var first = new Date(year, month, 1);
    var startPad = (first.getDay() + 6) % 7;
    var daysInMonth = new Date(year, month + 1, 0).getDate();

    for (var p = 0; p < startPad; p++) {
      var empty = document.createElement('span');
      empty.className = 'ibihub-cal__cell ibihub-cal__cell--empty';
      grid.appendChild(empty);
    }

    function redraw() {
      buildGrid(container, state);
    }

    for (var day = 1; day <= daysInMonth; day++) {
      var cell = document.createElement('button');
      cell.type = 'button';
      var dateObj = new Date(year, month, day);
      var key = iso(dateObj);
      cell.className = 'ibihub-cal__cell';
      cell.textContent = String(day);
      cell.dataset.date = key;

      if (occupiedSet.has(key)) {
        cell.classList.add('ibihub-cal__cell--occupied');
        cell.setAttribute('aria-label', day + ' — occupé');
      } else {
        cell.classList.add('ibihub-cal__cell--free');
        cell.setAttribute('aria-label', day + ' — disponible');
      }

      if (mode === 'admin') {
        cell.addEventListener('click', function (ev) {
          var k = ev.currentTarget.dataset.date;
          if (occupiedSet.has(k)) occupiedSet.delete(k);
          else occupiedSet.add(k);
          saveSet(occupiedSet);
          redraw();
        });
      }

      grid.appendChild(cell);
    }

    container.appendChild(grid);

    prev.addEventListener('click', function () {
      state.month--;
      if (state.month < 0) {
        state.month = 11;
        state.year--;
      }
      redraw();
    });
    next.addEventListener('click', function () {
      state.month++;
      if (state.month > 11) {
        state.month = 0;
        state.year++;
      }
      redraw();
    });
  }

  function initPublic(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return;
    var now = new Date();
    var state = {
      year: now.getFullYear(),
      month: now.getMonth(),
      occupiedSet: getOccupiedSet(true),
      mode: 'public'
    };
    buildGrid(el, state);
    global.addEventListener('storage', function (ev) {
      if (ev.key !== STORAGE_KEY || !ev.newValue) return;
      try {
        var arr = JSON.parse(ev.newValue);
        if (Array.isArray(arr)) {
          state.occupiedSet = new Set(arr);
          buildGrid(el, state);
        }
      } catch (e) {}
    });
  }

  function initAdmin(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return;
    var now = new Date();
    var occ = getOccupiedSet(false);
    if (!occ.size) {
      occ = defaultDemoOccupied();
      saveSet(occ);
    }
    var state = {
      year: now.getFullYear(),
      month: now.getMonth(),
      occupiedSet: occ,
      mode: 'admin'
    };
    buildGrid(el, state);
  }

  global.IbihubCalendar = {
    initPublic: initPublic,
    initAdmin: initAdmin,
    STORAGE_KEY: STORAGE_KEY
  };
})(typeof window !== 'undefined' ? window : this);
