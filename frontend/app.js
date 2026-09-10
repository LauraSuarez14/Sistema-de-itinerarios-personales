// Frontend estático (sin build step) del Sistema de Itinerarios Personales.
// Habla exclusivamente con el API Gateway (nunca directo con Airport
// Service ni Itinerary Service), que es quien hace el proxy + propaga el JWT.

// Detecta el host actual en vez de asumir "localhost": así el mismo archivo
// funciona igual si se accede desde otra IP de la LAN (docker-compose expone
// el gateway en el puerto 8000 del mismo host que sirve el frontend en 8080).
const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000`;

document.getElementById("api-base-display").textContent = API_BASE;

// --------------------------------------------------------------------------
// Estado de sesión: el JWT se guarda SOLO en una variable JS en memoria (no
// localStorage/sessionStorage). Decisión deliberada: es un mock de
// autenticación académico sin usuarios reales, así que no tiene sentido
// persistir el token entre recargas de página; además evita dejar un JWT
// (aunque sea de demo) tirado en el almacenamiento del navegador. El costo
// es que recargar la página cierra la sesión, lo cual es aceptable aquí.
let authToken = null;
let currentUsername = null;

// Paginación de itinerarios.
let currentPage = 1;
const PAGE_SIZE = 5;

// ------------------------------- Utilidades --------------------------------

function showBox(el, message, kind) {
  el.hidden = false;
  el.textContent = message;
  el.className = `status-box status-${kind}`;
}

function hideBox(el) {
  el.hidden = true;
  el.textContent = "";
}

/** Extrae un mensaje legible de cualquier respuesta de error, priorizando el
 * formato application/problem+json (RFC 7807) que usan todos los servicios. */
async function describeError(response) {
  const contentType = response.headers.get("content-type") || "";
  try {
    if (contentType.includes("json")) {
      const body = await response.json();
      if (body && body.detail) {
        return `${body.title || "Error"} (${response.status}): ${JSON.stringify(body.detail)}`;
      }
      return `Error ${response.status}: ${JSON.stringify(body)}`;
    }
    const text = await response.text();
    return `Error ${response.status}: ${text || response.statusText}`;
  } catch {
    return `Error ${response.status}: ${response.statusText || "respuesta no legible"}`;
  }
}

/** Wrapper de fetch que nunca deja una excepción de red sin mostrar: toda
 * llamada que falle (servidor caído, CORS, DNS, etc.) termina en un mensaje
 * visible en pantalla, nunca solo en la consola. */
async function safeFetch(url, options, onNetworkError) {
  try {
    return await fetch(url, options);
  } catch (networkError) {
    onNetworkError(`No se pudo contactar al API Gateway (${API_BASE}). ¿Está corriendo? Detalle: ${networkError.message}`);
    return null;
  }
}

// --------------------------------- Sesión -----------------------------------

const sessionStatus = document.getElementById("session-status");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const logoutBtn = document.getElementById("logout-btn");

function refreshSessionUi() {
  if (authToken) {
    showBox(sessionStatus, `Sesión iniciada como "${currentUsername}".`, "success");
    logoutBtn.disabled = false;
  } else {
    showBox(
      sessionStatus,
      "No has iniciado sesión. Puedes ver el mapa sin sesión, pero necesitas iniciar sesión para crear, listar o eliminar itinerarios.",
      "info"
    );
    logoutBtn.disabled = true;
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideBox(loginError);

  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;

  const response = await safeFetch(
    `${API_BASE}/auth/login`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    },
    (message) => showBox(loginError, message, "error")
  );
  if (!response) return;

  if (!response.ok) {
    showBox(loginError, await describeError(response), "error");
    return;
  }

  const body = await response.json();
  authToken = body.access_token;
  currentUsername = username;
  refreshSessionUi();
  // Con sesión recién iniciada, refresca la lista de itinerarios.
  loadItineraries();
});

logoutBtn.addEventListener("click", () => {
  authToken = null;
  currentUsername = null;
  refreshSessionUi();
});

function authHeaders() {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

// ---------------------------------- Mapa ------------------------------------

const mapError = document.getElementById("map-error");

async function loadAirportsMap() {
  hideBox(mapError);
  const response = await safeFetch(
    `${API_BASE}/api/v1/airports/plotly/points?limit=300`,
    { method: "GET" },
    (message) => showBox(mapError, message, "error")
  );
  if (!response) return;

  if (!response.ok) {
    showBox(mapError, await describeError(response), "error");
    return;
  }

  const points = await response.json();

  const trace = {
    type: "scattergeo",
    mode: "markers",
    lat: points.map((p) => p.lat),
    lon: points.map((p) => p.lon),
    text: points.map((p) => p.label),
    marker: { size: 8, color: "#1f6f5c" },
  };

  const layout = {
    geo: {
      scope: "south america",
      center: { lat: 4.5709, lon: -74.2973 },
      projection: { type: "mercator" },
      lataxis: { range: [-5, 14] },
      lonaxis: { range: [-82, -66] },
      showland: true,
      landcolor: "#eef2f0",
      showcountries: true,
    },
    margin: { l: 0, r: 0, t: 10, b: 0 },
  };

  Plotly.newPlot("airports-map", [trace], layout, { responsive: true });
}

document.getElementById("reload-map-btn").addEventListener("click", loadAirportsMap);

// ------------------------------ Crear itinerario ----------------------------

const createForm = document.getElementById("create-itinerary-form");
const createResult = document.getElementById("create-result");

createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideBox(createResult);

  if (!authToken) {
    showBox(createResult, "Debes iniciar sesión antes de crear un itinerario.", "error");
    return;
  }

  const payload = {
    user_name: document.getElementById("itn-user-name").value.trim(),
    origin_airport_id: Number(document.getElementById("itn-origin").value),
    destination_airport_id: Number(document.getElementById("itn-destination").value),
    travel_date: document.getElementById("itn-travel-date").value,
    duration_minutes: Number(document.getElementById("itn-duration").value),
  };

  const response = await safeFetch(
    `${API_BASE}/api/v1/itineraries`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    },
    (message) => showBox(createResult, message, "error")
  );
  if (!response) return;

  if (!response.ok) {
    showBox(createResult, await describeError(response), "error");
    return;
  }

  const created = await response.json();
  showBox(
    createResult,
    `Itinerario creado (id ${created.id}): ${created.origin_airport.iata_code} -> ${created.destination_airport.iata_code} el ${created.travel_date}.`,
    "success"
  );
  createForm.reset();
  currentPage = 1;
  loadItineraries();
});

// ------------------------------ Listar / eliminar ---------------------------

const listError = document.getElementById("list-error");
const tbody = document.getElementById("itineraries-tbody");
const pageIndicator = document.getElementById("page-indicator");

function renderItineraries(items) {
  tbody.innerHTML = "";
  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7">No hay itinerarios en esta página.</td></tr>';
    return;
  }
  for (const item of items) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.id}</td>
      <td>${item.user_name}</td>
      <td>${item.origin_airport.iata_code} — ${item.origin_airport.name}</td>
      <td>${item.destination_airport.iata_code} — ${item.destination_airport.name}</td>
      <td>${item.travel_date}</td>
      <td>${item.duration_minutes}</td>
      <td><button type="button" class="secondary delete-btn" data-id="${item.id}">Eliminar</button></td>
    `;
    tbody.appendChild(row);
  }

  tbody.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", () => deleteItinerary(btn.dataset.id));
  });
}

async function loadItineraries() {
  hideBox(listError);

  if (!authToken) {
    tbody.innerHTML = '<tr><td colspan="7">Inicia sesión para ver los itinerarios.</td></tr>';
    return;
  }

  const response = await safeFetch(
    `${API_BASE}/api/v1/itineraries?page=${currentPage}&page_size=${PAGE_SIZE}`,
    { method: "GET", headers: authHeaders() },
    (message) => showBox(listError, message, "error")
  );
  if (!response) return;

  if (!response.ok) {
    showBox(listError, await describeError(response), "error");
    return;
  }

  const data = await response.json();
  renderItineraries(data.items);
  pageIndicator.textContent = `página ${data.page} (total: ${data.total})`;
}

async function deleteItinerary(id) {
  hideBox(listError);
  const response = await safeFetch(
    `${API_BASE}/api/v1/itineraries/${id}`,
    { method: "DELETE", headers: authHeaders() },
    (message) => showBox(listError, message, "error")
  );
  if (!response) return;

  if (!response.ok && response.status !== 204) {
    showBox(listError, await describeError(response), "error");
    return;
  }
  loadItineraries();
}

document.getElementById("refresh-list-btn").addEventListener("click", loadItineraries);

document.getElementById("prev-page-btn").addEventListener("click", () => {
  if (currentPage > 1) {
    currentPage -= 1;
    loadItineraries();
  }
});

document.getElementById("next-page-btn").addEventListener("click", () => {
  currentPage += 1;
  loadItineraries();
});

// ------------------------------ Inicialización ------------------------------

refreshSessionUi();
loadAirportsMap();
