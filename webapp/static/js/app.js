const monthNames = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const weekdayLabels = ["M", "T", "W", "T", "F", "S", "S"];
const calendarEl = document.getElementById("calendar");
const destinationSelect = document.getElementById("destination-select");
const yearSelect = document.getElementById("year-select");
const detailTitle = document.getElementById("detail-title");
const detailSubtitle = document.getElementById("detail-subtitle");
const detailMeta = document.getElementById("detail-meta");
const chartContainer = document.getElementById("detail-chart");
const legendMin = document.getElementById("legend-min");
const legendMax = document.getElementById("legend-max");
const detailModal = document.getElementById("detail-modal");
const modalClosers = detailModal.querySelectorAll("[data-modal-close]");
const bodyDataset = document.body ? document.body.dataset : {};
const dataSource = bodyDataset.dataSource || bodyDataset.source || "api";
const dataBase = bodyDataset.dataBase || bodyDataset.base || "";

let activeDayTile = null;
let calendarData = {};
let indexData = null;
let destinationLookup = {};

function withDataBase(path) {
  if (!dataBase) {
    return path;
  }
  const base = dataBase.replace(/\/$/, "");
  const cleanPath = path.replace(/^\//, "");
  return `${base}/${cleanPath}`;
}

async function fetchJson(path) {
  try {
    const response = await fetch(path);
    if (!response.ok && response.status !== 0) {
      return null;
    }
    return await response.json();
  } catch (error) {
    return null;
  }
}

async function loadIndexData() {
  if (dataSource !== "static") {
    return null;
  }
  if (indexData) {
    return indexData;
  }
  const payload = await fetchJson(withDataBase("index.json"));
  indexData = payload || { destinations: [], years: [] };
  destinationLookup = {};
  (indexData.destinations || []).forEach((entry) => {
    destinationLookup[entry.id] = entry.label;
  });
  return indexData;
}

function range(start, end) {
  const items = [];
  for (let i = start; i <= end; i += 1) {
    items.push(i);
  }
  return items;
}

function pad(num) {
  return num.toString().padStart(2, "0");
}

function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  if (hours <= 0) {
    return `${minutes} min`;
  }
  return `${hours}h ${minutes}m`;
}

function colorForValue(value, min, max) {
  if (value === null || value === undefined) {
    return "var(--tile)";
  }
  const ratio = Math.min(1, Math.max(0, (value - min) / (max - min)));
  const start = { r: 156, g: 207, b: 156 };
  const mid = { r: 241, g: 193, b: 115 };
  const end = { r: 216, g: 107, b: 78 };

  const blend = (a, b, t) => Math.round(a + (b - a) * t);
  let color;
  if (ratio < 0.5) {
    const t = ratio / 0.5;
    color = {
      r: blend(start.r, mid.r, t),
      g: blend(start.g, mid.g, t),
      b: blend(start.b, mid.b, t),
    };
  } else {
    const t = (ratio - 0.5) / 0.5;
    color = {
      r: blend(mid.r, end.r, t),
      g: blend(mid.g, end.g, t),
      b: blend(mid.b, end.b, t),
    };
  }
  return `rgb(${color.r}, ${color.g}, ${color.b})`;
}

async function buildDestinationOptions() {
  if (dataSource !== "static") {
    return;
  }
  const payload = await loadIndexData();
  const destinations = payload.destinations || [];
  destinationSelect.innerHTML = "";
  destinations.forEach((dest, idx) => {
    const option = document.createElement("option");
    option.value = dest.id;
    option.textContent = dest.label;
    if (idx === 0) {
      option.selected = true;
    }
    destinationSelect.appendChild(option);
  });
}

async function buildYearOptions() {
  let years = [];
  if (dataSource === "static") {
    const payload = await loadIndexData();
    years = payload.years || [];
  } else {
    const response = await fetch("/api/years");
    const payload = await response.json();
    years = payload.years || [];
  }
  yearSelect.innerHTML = "";

  let fallbackYears = [];
  if (!years.length) {
    const currentYear = new Date().getFullYear();
    fallbackYears = range(currentYear - 1, currentYear + 1);
  }

  const list = years.length ? years : fallbackYears;
  list.forEach((year, idx) => {
    const option = document.createElement("option");
    option.value = year;
    option.textContent = year;
    if (idx === list.length - 1) {
      option.selected = true;
    }
    yearSelect.appendChild(option);
  });
}

function currentDestinationLabel() {
  if (dataSource === "static") {
    return destinationLookup[destinationSelect.value] || destinationSelect.value;
  }
  return destinationSelect.value;
}

function buildCalendar(year) {
  calendarEl.innerHTML = "";
  monthNames.forEach((name, monthIndex) => {
    const monthEl = document.createElement("div");
    monthEl.className = "month";

    const title = document.createElement("h3");
    title.textContent = name;
    monthEl.appendChild(title);

    const weekdays = document.createElement("div");
    weekdays.className = "weekdays";
    weekdayLabels.forEach((label) => {
      const day = document.createElement("div");
      day.textContent = label;
      weekdays.appendChild(day);
    });
    monthEl.appendChild(weekdays);

    const daysGrid = document.createElement("div");
    daysGrid.className = "days";

    const firstDay = new Date(year, monthIndex, 1);
    const startOffset = (firstDay.getDay() + 6) % 7; // Monday start
    const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();

    for (let i = 0; i < startOffset; i += 1) {
      const empty = document.createElement("div");
      empty.className = "day is-empty";
      daysGrid.appendChild(empty);
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const tile = document.createElement("button");
      tile.className = "day";
      tile.type = "button";
      tile.textContent = day;
      const dateKey = `${year}-${pad(monthIndex + 1)}-${pad(day)}`;
      tile.dataset.date = dateKey;
      tile.addEventListener("click", () => selectDay(tile, dateKey));
      daysGrid.appendChild(tile);
    }

    monthEl.appendChild(daysGrid);
    calendarEl.appendChild(monthEl);
  });
}

function applyCalendarColors() {
  const min = 3600;
  const max = 10800;
  legendMin.textContent = "1h";
  legendMax.textContent = "3h";

  document.querySelectorAll(".day").forEach((tile) => {
    if (tile.classList.contains("is-empty")) {
      return;
    }
    const value = calendarData[tile.dataset.date];
    tile.style.background = colorForValue(value, min, max);
    tile.title = value ? formatDuration(value) : "No data";
  });
}

async function fetchCalendar() {
  const destination = destinationSelect.value;
  const year = yearSelect.value;
  if (!destination || !year) {
    calendarData = {};
    applyCalendarColors();
    return;
  }
  let payload = null;
  if (dataSource === "static") {
    payload = await fetchJson(
      withDataBase(`calendar/${encodeURIComponent(destination)}/${year}.json`)
    );
  } else {
    const response = await fetch(
      `/api/calendar?destination=${encodeURIComponent(destination)}&year=${encodeURIComponent(year)}`
    );
    payload = await response.json();
  }
  calendarData = (payload && payload.data) || {};
  applyCalendarColors();
}

function openModal() {
  detailModal.classList.add("is-open");
  detailModal.setAttribute("aria-hidden", "false");
}

function closeModal() {
  detailModal.classList.remove("is-open");
  detailModal.setAttribute("aria-hidden", "true");
}

function selectDay(tile, dateKey) {
  if (activeDayTile) {
    activeDayTile.classList.remove("is-selected");
  }
  activeDayTile = tile;
  tile.classList.add("is-selected");
  openModal();
  fetchDayDetail(dateKey);
}

async function fetchDayDetail(dateKey) {
  const destination = destinationSelect.value;
  if (!destination) {
    renderDayDetail(dateKey, []);
    return;
  }
  let payload = null;
  if (dataSource === "static") {
    payload = await fetchJson(
      withDataBase(`day/${encodeURIComponent(destination)}/${dateKey}.json`)
    );
  } else {
    const response = await fetch(
      `/api/day?destination=${encodeURIComponent(destination)}&date=${encodeURIComponent(dateKey)}`
    );
    payload = await response.json();
  }
  renderDayDetail(dateKey, (payload && payload.data) || []);
}

function renderDayDetail(dateKey, data) {
  detailTitle.textContent = `${dateKey}`;
  detailSubtitle.textContent = data.length
    ? `Hourly observations for ${currentDestinationLabel()}`
    : "No data recorded for this day.";

  detailMeta.textContent = `${data.length} readings`;

  chartContainer.innerHTML = "";
  if (!data.length) {
    return;
  }

  const width = chartContainer.clientWidth - 32;
  const height = 240;
  const padding = 40;
  const labelFontSize = 12;

  const durationsSeconds = data.map((entry) => entry.duration_seconds);
  const min = Math.min(...durationsSeconds);
  const max = Math.max(...durationsSeconds);
  const durationsMinutes = durationsSeconds.map((value) => value / 60);

  const points = data.map((entry, index) => {
    const date = new Date(entry.observed_at);
    const hour = date.getHours();
    return { hour, value: entry.duration_seconds / 60, index };
  });

  const xScale = (hour) =>
    padding + (hour / 23) * (width - padding * 2);
  const minMinutes = Math.min(...durationsMinutes);
  const maxMinutes = Math.max(...durationsMinutes);
  const yScale = (value) =>
    height -
    padding -
    ((value - minMinutes) / (maxMinutes - minMinutes || 1)) *
      (height - padding * 2);

  const makeText = (text, x, y, rotation = 0, anchor = "middle") => {
    const label = document.createElementNS(svg.namespaceURI, "text");
    label.textContent = text;
    label.setAttribute("x", x);
    label.setAttribute("y", y);
    label.setAttribute("fill", "#6f6259");
    label.setAttribute("font-size", labelFontSize);
    label.setAttribute("text-anchor", anchor);
    if (rotation) {
      label.setAttribute("transform", `rotate(${rotation} ${x} ${y})`);
    }
    return label;
  };

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  svg.appendChild(
    makeText("Hour of day", width / 2, height - 8, 0, "middle")
  );
  svg.appendChild(
    makeText("Travel time (minutes)", 14, height / 2, -90, "middle")
  );

  const xAxis = document.createElementNS(svg.namespaceURI, "path");
  xAxis.setAttribute(
    "d",
    `M${padding},${height - padding} L${width - padding},${height - padding}`
  );
  xAxis.setAttribute("stroke", "#c9b8aa");
  xAxis.setAttribute("stroke-width", "1");
  svg.appendChild(xAxis);

  const yAxis = document.createElementNS(svg.namespaceURI, "path");
  yAxis.setAttribute("d", `M${padding},${padding} L${padding},${height - padding}`);
  yAxis.setAttribute("stroke", "#c9b8aa");
  yAxis.setAttribute("stroke-width", "1");
  svg.appendChild(yAxis);

  const hourTicks = [0, 4, 8, 12, 16, 20, 24];
  hourTicks.forEach((hour) => {
    const tick = document.createElementNS(svg.namespaceURI, "line");
    const x = padding + (hour / 24) * (width - padding * 2);
    tick.setAttribute("x1", x);
    tick.setAttribute("x2", x);
    tick.setAttribute("y1", height - padding);
    tick.setAttribute("y2", height - padding + 6);
    tick.setAttribute("stroke", "#c9b8aa");
    svg.appendChild(tick);
    svg.appendChild(makeText(`${hour}`, x, height - padding + 18, 0, "middle"));
  });

  const tickCount = 4;
  for (let i = 0; i <= tickCount; i += 1) {
    const value = minMinutes + ((maxMinutes - minMinutes) / tickCount) * i;
    const rounded = Math.round(value / 5) * 5;
    const y = yScale(value);
    const tick = document.createElementNS(svg.namespaceURI, "line");
    tick.setAttribute("x1", padding - 6);
    tick.setAttribute("x2", padding);
    tick.setAttribute("y1", y);
    tick.setAttribute("y2", y);
    tick.setAttribute("stroke", "#c9b8aa");
    svg.appendChild(tick);
    svg.appendChild(makeText(`${rounded}`, padding - 10, y + 4, 0, "end"));
  }

  points.forEach((point) => {
    const dot = document.createElementNS(svg.namespaceURI, "circle");
    dot.setAttribute("cx", xScale(point.hour));
    dot.setAttribute("cy", yScale(point.value));
    dot.setAttribute("r", "4");
    dot.setAttribute("fill", "#2c2a28");
    dot.setAttribute("opacity", "0.8");
    svg.appendChild(dot);
  });

  chartContainer.appendChild(svg);
  detailMeta.textContent = `${data.length} readings, ${formatDuration(min)} - ${formatDuration(max)}`;
}

function setupControls() {
  yearSelect.addEventListener("change", () => {
    buildCalendar(parseInt(yearSelect.value, 10));
    fetchCalendar();
  });

  destinationSelect.addEventListener("change", () => {
    fetchCalendar();
  });

  modalClosers.forEach((closer) => {
    closer.addEventListener("click", closeModal);
  });
}

async function init() {
  await buildDestinationOptions();
  await buildYearOptions();
  buildCalendar(parseInt(yearSelect.value, 10));
  setupControls();
  fetchCalendar();
}

init();
