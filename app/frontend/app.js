const apiStatus = document.querySelector("#api-status");
const tokenInput = document.querySelector("#access-token");
const authMessage = document.querySelector("#auth-message");
const productGrid = document.querySelector("#product-grid");
const resultCount = document.querySelector("#result-count");
const cartContent = document.querySelector("#cart-content");
const cartSummary = document.querySelector("#cart-summary");
const cartCount = document.querySelector("#cart-count");
const toast = document.querySelector("#toast");
const chatMessagesElement = document.querySelector("#chat-messages");
const chatInput = document.querySelector("#chat-input");
const chatSend = document.querySelector("#chat-send");

let accessToken = "";
let toastTimeout;
let chatHistory = [];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function formatMoney(value, currency = "INR") {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(Number(value));
  } catch {
    return `${escapeHtml(currency)} ${escapeHtml(value)}`;
  }
}

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.toggle("is-error", isError);
  toast.classList.add("is-visible");
  window.clearTimeout(toastTimeout);
  toastTimeout = window.setTimeout(() => toast.classList.remove("is-visible"), 3600);
}

async function apiRequest(path, { method = "GET", body, authenticated = true } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (authenticated && accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" && payload !== null
      ? payload.detail || payload.message || JSON.stringify(payload)
      : payload;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return payload;
}

async function guarded(action) {
  try {
    await action();
  } catch (error) {
    showToast(error.message || "Something went wrong.", true);
  }
}

async function checkApi() {
  const label = apiStatus.querySelector("span");
  try {
    await apiRequest("/health", { authenticated: false });
    apiStatus.classList.remove("is-offline");
    apiStatus.classList.add("is-online");
    label.textContent = "API connected";
  } catch {
    apiStatus.classList.remove("is-online");
    apiStatus.classList.add("is-offline");
    label.textContent = "API unavailable";
  }
}

async function loadCategories() {
  const categories = await apiRequest("/api/catalog/categories", { authenticated: false });
  const select = document.querySelector("#category-filter");
  select.innerHTML = '<option value="">All categories</option>' + categories.map((category) => (
    `<option value="${escapeHtml(category.name)}">${escapeHtml(category.name)}</option>`
  )).join("");
}

function productCard(product) {
  const attributes = Object.entries(product.attributes || {}).map(([key, value]) => (
    `<span class="attribute-chip">${escapeHtml(key)}: ${escapeHtml(value)}</span>`
  )).join("");
  const category = product.category || "ShopMate find";
  const stockClass = product.available ? "" : " out-of-stock";
  const stockLabel = product.available ? "In stock" : "Out of stock";

  return `
    <article class="product-card">
      <div class="product-card-top">
        <span class="category-chip">${escapeHtml(category)}</span>
        <span class="stock-label${stockClass}">${stockLabel}</span>
      </div>
      <h3 title="${escapeHtml(product.name)}">${escapeHtml(product.name)}</h3>
      <p class="product-sku">SKU: ${escapeHtml(product.sku)}</p>
      <div class="product-attributes">${attributes}</div>
      <div class="product-bottom">
        <strong class="product-price">${formatMoney(product.price, product.currency)}</strong>
        <div class="product-actions">
          <label class="visually-hidden" for="quantity-${escapeHtml(product.product_id)}">Quantity</label>
          <input class="quantity-input" id="quantity-${escapeHtml(product.product_id)}" data-quantity type="number" min="1" value="1" ${product.available ? "" : "disabled"}>
          <button class="button button-accent add-button" type="button" data-add-sku="${escapeHtml(product.sku)}" ${product.available ? "" : "disabled"}>
            Add <span aria-hidden="true">+</span>
          </button>
        </div>
      </div>
      <button class="stock-button" type="button" data-check-sku="${escapeHtml(product.sku)}">Check live stock →</button>
    </article>`;
}

async function loadProducts() {
  const params = new URLSearchParams();
  const query = document.querySelector("#search-query").value.trim();
  const category = document.querySelector("#category-filter").value;
  const maxPrice = document.querySelector("#max-price").value;
  if (query) params.set("query", query);
  if (category) params.set("category", category);
  if (maxPrice) params.set("max_price", maxPrice);

  productGrid.innerHTML = '<div class="loading-card"><span class="loader"></span> Loading the latest products</div>';
  const queryString = params.toString();
  let products;
  try {
    products = await apiRequest(`/api/catalog/products${queryString ? `?${queryString}` : ""}`, {
      authenticated: false,
    });
  } catch (error) {
    resultCount.textContent = "Catalog unavailable";
    productGrid.innerHTML = '<div class="no-results">Could not load products. Check that the API and database are available.</div>';
    throw error;
  }

  resultCount.textContent = `${products.length} ${products.length === 1 ? "product" : "products"}`;
  productGrid.innerHTML = products.length
    ? products.map(productCard).join("")
    : '<div class="no-results">No products found. Try another search or category.</div>';
}

function renderCart(cart) {
  const items = cart.items || [];
  const quantity = items.reduce((total, item) => total + Number(item.quantity), 0);
  cartCount.textContent = quantity;
  cartSummary.hidden = items.length === 0;

  if (!items.length) {
    cartContent.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon" aria-hidden="true">⌑</span>
        <p>Your bag is waiting.</p>
        <span>Add an item to get started.</span>
      </div>`;
    return;
  }

  cartContent.innerHTML = `<div class="cart-items">${items.map((item) => `
    <div class="cart-item">
      <div>
        <div class="cart-item-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</div>
        <div class="cart-item-meta">${item.quantity} × ${formatMoney(item.unit_price, cart.currency)} · ${escapeHtml(item.sku)}</div>
      </div>
      <div class="cart-item-end">
        <span class="cart-item-price">${formatMoney(item.line_total, cart.currency)}</span>
        <button class="remove-item" type="button" data-remove-sku="${escapeHtml(item.sku)}" aria-label="Remove ${escapeHtml(item.name)} from cart" title="Remove item">×</button>
      </div>
    </div>`).join("")}</div>`;
  document.querySelector("#cart-total").textContent = formatMoney(cart.total, cart.currency);
}

async function refreshCart() {
  const cart = await apiRequest("/api/cart");
  renderCart(cart);
}

function renderOrders(orders) {
  const container = document.querySelector("#orders-list");
  if (!orders.length) {
    container.innerHTML = '<div class="orders-placeholder">No orders yet. Your completed checkouts will appear here.</div>';
    return;
  }

  container.innerHTML = orders.map((order) => {
    const date = new Date(order.created_at);
    const dateText = Number.isNaN(date.getTime())
      ? escapeHtml(order.created_at)
      : escapeHtml(date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }));
    return `
      <article class="order-card">
        <div class="order-card-top">
          <span class="order-id" title="${escapeHtml(order.id)}">#${escapeHtml(order.id)}</span>
          <span class="order-status">${escapeHtml(order.status)}</span>
        </div>
        <div class="order-card-bottom">
          <span class="order-date">${dateText} · ${(order.items || []).length} ${(order.items || []).length === 1 ? "item" : "items"}</span>
          <strong class="order-total">${formatMoney(order.total, order.currency)}</strong>
        </div>
      </article>`;
  }).join("");
}

async function refreshOrders() {
  const orders = await apiRequest("/api/orders");
  renderOrders(orders);
}

async function checkInventory(sku, quantity = 1) {
  const result = document.querySelector("#inventory-result");
  result.classList.remove("is-error");
  result.textContent = "Checking live stock…";
  try {
    const params = new URLSearchParams({ quantity: String(quantity) });
    const stock = await apiRequest(`/api/inventory/${encodeURIComponent(sku)}?${params}`, {
      authenticated: false,
    });
    result.textContent = stock.available
      ? `${stock.available_quantity} available · enough for ${stock.requested_quantity}.`
      : `${stock.available_quantity} available · not enough for ${stock.requested_quantity}.`;
  } catch (error) {
    result.classList.add("is-error");
    result.textContent = error.message || "Could not check this SKU.";
  }
}

function appendChatMessage(role, content) {
  const message = document.createElement("div");
  message.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}`;

  if (role === "assistant") {
    const avatar = document.createElement("span");
    avatar.className = "chat-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "s";
    message.append(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  if (role === "assistant") {
    const author = document.createElement("span");
    author.className = "message-author";
    author.textContent = "ShopMate";
    bubble.append(author);
  }
  const paragraph = document.createElement("p");
  paragraph.textContent = content;
  bubble.append(paragraph);
  message.append(bubble);
  chatMessagesElement.append(message);
  chatMessagesElement.scrollTop = chatMessagesElement.scrollHeight;
  return message;
}

async function sendChatMessage(content) {
  const message = content.trim();
  if (!message || chatSend.disabled) return;

  chatHistory.push({ role: "user", content: message });
  if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
  appendChatMessage("user", message);
  chatInput.value = "";
  chatInput.style.height = "auto";
  chatSend.disabled = true;

  const typing = document.createElement("div");
  typing.className = "chat-message assistant-message";
  typing.innerHTML = '<span class="chat-avatar" aria-hidden="true">s</span><div class="message-bubble typing-bubble" role="status">ShopMate is thinking<span></span><span></span><span></span></div>';
  chatMessagesElement.append(typing);
  chatMessagesElement.scrollTop = chatMessagesElement.scrollHeight;

  try {
    const response = await apiRequest("/api/chat", {
      method: "POST",
      body: { messages: chatHistory },
    });
    chatHistory.push({ role: "assistant", content: response.reply });
    if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
    typing.remove();
    appendChatMessage("assistant", response.reply);
  } catch (error) {
    typing.remove();
    const detail = error.message || "Please try again in a moment.";
    appendChatMessage("assistant", `I couldn’t complete that request: ${detail}`);
    showToast(detail, true);
  } finally {
    chatSend.disabled = false;
    chatInput.focus();
  }
}

document.querySelector("#chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  sendChatMessage(chatInput.value);
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChatMessage(chatInput.value);
  }
});

chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = `${Math.min(chatInput.scrollHeight, 140)}px`;
});

document.querySelector(".suggested-prompts").addEventListener("click", (event) => {
  const button = event.target.closest("[data-prompt]");
  if (button) sendChatMessage(button.dataset.prompt);
});

document.querySelector("#search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  guarded(loadProducts);
});

document.querySelector("#category-filter").addEventListener("change", () => guarded(loadProducts));

document.querySelector("#product-grid").addEventListener("click", async (event) => {
  const addButton = event.target.closest("[data-add-sku]");
  if (addButton) {
    if (!accessToken) {
      showToast("Connect your account with a bearer token before adding to your bag.", true);
      tokenInput.focus();
      return;
    }
    const card = addButton.closest(".product-card");
    const quantity = Number(card.querySelector("[data-quantity]").value);
    if (!Number.isInteger(quantity) || quantity < 1) {
      showToast("Enter a quantity greater than zero.", true);
      return;
    }
    addButton.disabled = true;
    await guarded(async () => {
      const cart = await apiRequest("/api/cart/items", {
        method: "POST",
        body: { sku: addButton.dataset.addSku, quantity },
      });
      renderCart(cart);
      showToast("Added to your bag.");
    });
    addButton.disabled = false;
    return;
  }

  const stockButton = event.target.closest("[data-check-sku]");
  if (stockButton) {
    document.querySelector("#inventory-sku").value = stockButton.dataset.checkSku;
    await checkInventory(stockButton.dataset.checkSku);
  }
});

document.querySelector("#cart-content").addEventListener("click", async (event) => {
  const removeButton = event.target.closest("[data-remove-sku]");
  if (!removeButton) return;
  await guarded(async () => {
    const cart = await apiRequest(`/api/cart/items/${encodeURIComponent(removeButton.dataset.removeSku)}`, {
      method: "DELETE",
    });
    renderCart(cart);
    showToast("Item removed from your bag.");
  });
});

document.querySelector("#token-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const token = tokenInput.value.trim();
  if (!token) {
    accessToken = "";
    authMessage.textContent = "Paste an access token to connect your account.";
    authMessage.classList.remove("is-connected");
    return;
  }

  accessToken = token;
  authMessage.textContent = "Checking token…";
  authMessage.classList.remove("is-connected");
  try {
    const cart = await apiRequest("/api/cart");
    renderCart(cart);
    tokenInput.value = "";
    authMessage.textContent = "Account connected. Token is kept in memory for this page only.";
    authMessage.classList.add("is-connected");
    document.querySelector("#clear-token").hidden = false;
    await guarded(refreshOrders);
  } catch (error) {
    accessToken = "";
    document.querySelector("#clear-token").hidden = true;
    cartCount.textContent = "0";
    cartSummary.hidden = true;
    cartContent.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon" aria-hidden="true">⌑</span>
        <p>Your bag is waiting.</p>
        <span>Add an item to get started.</span>
      </div>`;
    document.querySelector("#orders-list").innerHTML = '<div class="orders-placeholder">Connect an account to see its order history.</div>';
    authMessage.textContent = error.message || "Could not authenticate with this token.";
    tokenInput.focus();
  }
});

document.querySelector("#clear-token").addEventListener("click", () => {
  accessToken = "";
  tokenInput.value = "";
  document.querySelector("#clear-token").hidden = true;
  authMessage.textContent = "The API has no sign-in route; obtain a token from your development setup.";
  authMessage.classList.remove("is-connected");
  cartCount.textContent = "0";
  cartSummary.hidden = true;
  cartContent.innerHTML = `
    <div class="empty-state">
      <span class="empty-icon" aria-hidden="true">⌑</span>
      <p>Your bag is waiting.</p>
      <span>Add an item to get started.</span>
    </div>`;
  document.querySelector("#orders-list").innerHTML = '<div class="orders-placeholder">Connect an account to see its order history.</div>';
});

document.querySelector("#refresh-cart").addEventListener("click", () => {
  if (!accessToken) {
    showToast("Connect your account first to load your bag.", true);
    return;
  }
  guarded(refreshCart);
});

document.querySelector("#refresh-orders").addEventListener("click", () => {
  if (!accessToken) {
    showToast("Connect your account first to load order history.", true);
    return;
  }
  guarded(refreshOrders);
});

document.querySelector("#checkout-button").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  await guarded(async () => {
    const result = await apiRequest("/api/checkout", { method: "POST" });
    renderCart({ items: [], total: "0", currency: result.order.currency || "INR" });
    showToast(`Order placed: ${result.order.id}`);
    await refreshOrders();
  });
  button.disabled = false;
});

document.querySelector("#inventory-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const sku = document.querySelector("#inventory-sku").value.trim();
  if (sku) guarded(() => checkInventory(sku));
});

checkApi();
guarded(loadCategories);
guarded(loadProducts);
