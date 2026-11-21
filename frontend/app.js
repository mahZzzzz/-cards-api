
const API_URL = "http://127.0.0.1:8000";

const SESSION_KEY = "cardsBoardSession";

const loginScreen = document.getElementById("login-screen");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const loginSubmitButton = document.getElementById("login-submit-btn");
const loginUsernameInput = document.getElementById("login-username");
const loginPasswordInput = document.getElementById("login-password");
const appHeader = document.getElementById("app-header");
const appMain = document.getElementById("app-main");
const sessionUser = document.getElementById("session-user");
const logoutButton = document.getElementById("logout-btn");

function readSession() {
    try {
        const raw = sessionStorage.getItem(SESSION_KEY);

        if (!raw) return null;

        const session = JSON.parse(raw);

        if (
            !session ||
            typeof session.token !== "string" ||
            !session.token ||
            typeof session.username !== "string" ||
            (session.role !== "admin" && session.role !== "member")
        ) {
            return null;
        }

        return session;

    } catch (_) {
        return null;
    }
}

function saveSession(session) {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function clearSession() {
    sessionStorage.removeItem(SESSION_KEY);
}

function showLogin(message = "") {
    appHeader.hidden = true;
    appMain.hidden = true;
    loginScreen.hidden = false;
    sessionUser.textContent = "";
    loginPasswordInput.value = "";

    document.querySelectorAll(".modal").forEach(modal => {
        modal.hidden = true;
    });

    if (message) {
        loginError.textContent = message;
        loginError.hidden = false;
    } else {
        loginError.textContent = "";
        loginError.hidden = true;
    }

    loginUsernameInput.focus();
}

function showApp(session) {
    loginScreen.hidden = true;
    loginError.hidden = true;
    appHeader.hidden = false;
    appMain.hidden = false;
    sessionUser.textContent = `${session.username} (${session.role})`;

    // Members may view and edit cards, but only admins may delete them.
    // The backend enforces this; this only keeps the UI consistent.
    deleteCardButton.hidden = session.role !== "admin";
}

function handleUnauthorized() {
    clearSession();
    showLogin("Your session expired. Please sign in again.");
}

function handleApiError(error, fallbackMessage) {
    if (error && error.status === 401) {
        return;
    }

    if (error && error.status === 403) {
        alert(error.message);
        return;
    }

    alert(fallbackMessage);
}

async function apiFetch(path, options = {}) {
    const session = readSession();
    const headers = new Headers(options.headers || {});

    if (session) {
        headers.set("Authorization", `Bearer ${session.token}`);
    }

    const response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers
    });

    if (response.status === 401) {
        handleUnauthorized();
        const error = new Error(
            "Your session expired. Please sign in again."
        );
        error.status = 401;
        throw error;
    }

    if (response.status === 403) {
        const error = new Error(
            "You do not have permission to perform this action."
        );
        error.status = 403;
        throw error;
    }

    return response;
}

// Get cards from the FastAPI backend
async function loadCards() {
    try {
        const response = await apiFetch("/cards");

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const cards = await response.json();

        // Clear all columns before displaying cards
        document.querySelectorAll(".card-list").forEach(list => {
            list.innerHTML = "";
        });

        // Display each card in its corresponding column
        cards.forEach(card => {
            const column = document.querySelector(
                `#${card.status} .card-list`
            );

            if (!column) return;

            const cardElement = document.createElement("div");
            cardElement.className = "card";

            const title = document.createElement("h3");
            title.textContent = card.title;

            const description = document.createElement("p");
            description.textContent = card.description || "";

            cardElement.appendChild(title);
            cardElement.appendChild(description);

            cardElement.style.cursor = "pointer";

            cardElement.addEventListener("click", () => {   
                showCardDetails(card.id);
            });

            column.appendChild(cardElement);
        });

    } catch (error) {
        console.error("Failed to load cards:", error);
        handleApiError(error, "Could not connect to the Cards API.");
    }
}

// Cards are loaded after authentication succeeds (see startApp).


const cardModal = document.getElementById("card-modal");
const cardForm = document.getElementById("card-form");
const addCardButton = document.getElementById("add-card-btn");
const cancelCardButton = document.getElementById("cancel-card-btn");

// Open the Add Card form
addCardButton.addEventListener("click", () => {
    cardModal.hidden = false;
    document.getElementById("card-title").focus();
});

// Close the form without creating a card
cancelCardButton.addEventListener("click", () => {
    cardModal.hidden = true;
    cardForm.reset();
});

// Create a new card
cardForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const title = document.getElementById("card-title").value.trim();
    const description = document.getElementById("card-description").value.trim();

    if (!title || title.length > 100 || description.length > 1000) {
        alert("Please check the title and description lengths.");
        return;
    }

    try {
        const response = await apiFetch("/cards", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: title,
                description: description
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        cardModal.hidden = true;
        cardForm.reset();

        await loadCards();

    } catch (error) {
        console.error("Failed to create card:", error);
        handleApiError(error, "Could not create the card.");
    }
});



const detailsModal = document.getElementById("details-modal");
const closeDetailsButton = document.getElementById("close-details-btn");

// Load and display one card's details
async function showCardDetails(cardId) {
    try {
        const response = await apiFetch(`/cards/${cardId}`);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const card = await response.json();
        detailsModal.dataset.cardId = card.id;

        document.getElementById("detail-id").textContent = card.id;
        document.getElementById("detail-title").textContent = card.title;
        document.getElementById("detail-description").textContent =
            card.description || "No description";
        document.getElementById("detail-status").textContent =
            card.status.replaceAll("_", " ");

            
        document.getElementById("detail-assignee").textContent =
            card.assignee || "Unassigned";

        document.getElementById("assignee-input").value =
            card.assignee || "";


            await loadComments(card.id);
        detailsModal.hidden = false;

    } catch (error) {
        console.error("Failed to load card details:", error);
        handleApiError(error, "Could not load card details.");
    }
}


const saveAssigneeButton = document.getElementById("save-assignee-btn");

saveAssigneeButton.addEventListener("click", async () => {
    const cardId = detailsModal.dataset.cardId;
    const assignee = document.getElementById("assignee-input").value.trim();

    if (!assignee) {
        alert("Please enter a valid assignee name.");
        return;
    }

    try {
        const response = await apiFetch(`/cards/${cardId}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ assignee })
        });

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        await showCardDetails(cardId);
        await loadCards();

    } catch (error) {
        console.error("Failed to assign card:", error);
        handleApiError(error, "Could not save the assignment.");
    }
});


const removeAssigneeButton = document.getElementById("remove-assignee-btn");

removeAssigneeButton.addEventListener("click", async () => {
    const cardId = detailsModal.dataset.cardId;

    try {
        const response = await apiFetch(`/cards/${cardId}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ assignee: null })
        });

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        await showCardDetails(cardId);
        await loadCards();

    } catch (error) {
        console.error("Failed to remove assignee:", error);
        handleApiError(error, "Could not remove the assignment.");
    }
});


// Close details window
closeDetailsButton.addEventListener("click", () => {
    detailsModal.hidden = true;
});


const nextStageButton = document.getElementById("next-stage-btn");

const stages = [
    "spec",
    "ready",
    "in_progress",
    "review",
    "done"
];

nextStageButton.addEventListener("click", async () => {
    const cardId = detailsModal.dataset.cardId;

    if (!cardId) return;

    const currentStatus = document
        .getElementById("detail-status")
        .textContent
        .replaceAll(" ", "_");

    const currentIndex = stages.indexOf(currentStatus);

    if (currentIndex === -1 || currentIndex === stages.length - 1) {
        alert("This card cannot move to another stage.");
        return;
    }

    const nextStatus = stages[currentIndex + 1];

    try {
        const response = await apiFetch(`/cards/${cardId}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                status: nextStatus
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        detailsModal.hidden = true;
        await loadCards();

    } catch (error) {
        console.error("Failed to update card status:", error);
        handleApiError(error, "Could not move the card to the next stage.");
    }
});


const deleteCardButton = document.getElementById("delete-card-btn");

deleteCardButton.addEventListener("click", async () => {
    const cardId = detailsModal.dataset.cardId;

    if (!cardId) return;

    const session = readSession();

    if (!session || session.role !== "admin") {
        alert("You do not have permission to delete cards.");
        return;
    }

    const confirmed = confirm(
        "Are you sure you want to delete this card?"
    );

    if (!confirmed) return;

    try {
        const response = await apiFetch(`/cards/${cardId}`, {
            method: "DELETE"
        });

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        detailsModal.hidden = true;
        delete detailsModal.dataset.cardId;

        await loadCards();

    } catch (error) {
        console.error("Failed to delete card:", error);
        handleApiError(error, "Could not delete the card.");
    }
});


const editCardButton = document.getElementById("edit-card-btn");
const editModal = document.getElementById("edit-modal");
const editCardForm = document.getElementById("edit-card-form");
const cancelEditButton = document.getElementById("cancel-edit-btn");

// Open the edit form with current card information
editCardButton.addEventListener("click", async () => {
    const cardId = detailsModal.dataset.cardId;

    if (!cardId) return;

    try {
        const response = await apiFetch(`/cards/${cardId}`);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const card = await response.json();

        document.getElementById("edit-card-title").value = card.title;
        document.getElementById("edit-card-description").value =
            card.description;

        editModal.dataset.cardId = card.id;

        detailsModal.hidden = true;
        editModal.hidden = false;

    } catch (error) {
        console.error("Failed to open edit form:", error);
        handleApiError(error, "Could not load the card for editing.");
    }
});

// Cancel editing
cancelEditButton.addEventListener("click", () => {
    editModal.hidden = true;
    editCardForm.reset();
    delete editModal.dataset.cardId;
});

// Save edited card
editCardForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const cardId = editModal.dataset.cardId;
    if (!cardId) return;

    const title = document.getElementById("edit-card-title").value.trim();
    const description = document
        .getElementById("edit-card-description")
        .value.trim();

    if (!title || title.length > 100 || description.length > 1000) {
        alert("Please check the title and description lengths.");
        return;
    }

    try {
        const response = await apiFetch(`/cards/${cardId}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title: title,
                description: description
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        editModal.hidden = true;
        editCardForm.reset();
        delete editModal.dataset.cardId;

        await loadCards();

    } catch (error) {
        console.error("Failed to edit card:", error);
        handleApiError(error, "Could not save changes.");
    }
});


async function checkApiHealth() {
    const statusElement = document.getElementById("api-status");

    try {
        const response = await fetch(`${API_URL}/health`);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const data = await response.json();

        if (data.status !== "ok") {
            throw new Error("API is not healthy");
        }

        statusElement.textContent = "● API Online";
        statusElement.style.color = "#16a34a";

    } catch (error) {
        statusElement.textContent = "● API Offline";
        statusElement.style.color = "#dc2626";
        console.error("API health check failed:", error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Health is checked after authentication (see startApp).
});


async function loadComments(cardId) {
    const commentsList = document.getElementById("comments-list");

    try {
        const response = await apiFetch(
            `/cards/${cardId}/comments`
        );

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const comments = await response.json();

        commentsList.replaceChildren();

        if (comments.length === 0) {
            const message = document.createElement("p");
            message.textContent = "No comments yet.";
            commentsList.appendChild(message);
            return;
        }

        comments.forEach((comment) => {
            const item = document.createElement("div");
            item.className = "comment-item";

            const author = document.createElement("strong");
            author.textContent = comment.author;

            const text = document.createElement("p");
            text.textContent = comment.text;

            item.appendChild(author);
            item.appendChild(text);
            commentsList.appendChild(item);
        });

    } catch (error) {
        console.error("Failed to load comments:", error);

        if (error && error.status === 403) {
            commentsList.textContent =
                "You do not have permission to view comments.";
        } else if (!error || error.status !== 401) {
            commentsList.textContent = "Could not load comments.";
        }
    }}


const commentForm = document.getElementById("comment-form");

commentForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const cardId = detailsModal.dataset.cardId;
    const author = document.getElementById("comment-author").value.trim();
    const text = document.getElementById("comment-text").value.trim();

    if (!cardId || !author || !text) {
        alert("Please enter your name and a comment.");
        return;
    }

    try {
        const response = await apiFetch(
            `/cards/${cardId}/comments`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ author, text })
            }
        );

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        document.getElementById("comment-text").value = "";
        await loadComments(cardId);

    } catch (error) {
        console.error("Failed to add comment:", error);
        handleApiError(error, "Could not add the comment.");
    }
});



const prdForm = document.getElementById("prd-upload-form");
const prdFileInput = document.getElementById("prd-file");
const prdUseOcr = document.getElementById("prd-use-ocr");
const prdGenerateBtn = document.getElementById("prd-generate-btn");
const prdStatus = document.getElementById("prd-upload-status");
const prdResults = document.getElementById("prd-results");
const prdDraftList = document.getElementById("prd-draft-list");
const prdAmbiguities = document.getElementById("prd-ambiguities");

prdForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = prdFileInput.files[0];

  if (!file) {
    prdStatus.textContent = "Please select a PDF file.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  prdGenerateBtn.disabled = true;
  prdStatus.textContent = "Analyzing PDF and generating cards...";
  prdResults.hidden = true;

  try {
    const response = await apiFetch(
      `/prd/preview?use_ocr=${prdUseOcr.checked}`,
      {
        method: "POST",
        body: formData
      }
    );

    if (!response.ok) {
      let message = `Server error: ${response.status}`;

      try {
        const error = await response.json();
        if (typeof error.detail === "string") {
          message = error.detail;
        }
      } catch (_) {}

      throw new Error(message);
    }

    const breakdown = await response.json();

    prdDraftList.replaceChildren();
    prdAmbiguities.replaceChildren();

    
    for (const card of breakdown.cards) {
      const element = document.createElement("article");
      element.className = "prd-draft-card";
      element.dataset.card = JSON.stringify(card);

      // Checkbox for selecting the card
      const selectLabel = document.createElement("label");
      selectLabel.className = "prd-card-select";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "prd-card-checkbox";

      selectLabel.append(checkbox, " Select this card");

      // Card title
      const title = document.createElement("h4");
      title.textContent = card.title;

      // Card goal
      const goal = document.createElement("p");
      goal.textContent = card.goal;

      // Source section
      const source = document.createElement("small");
      source.textContent = `Source: ${card.prd_section}`;

      element.append(selectLabel, title, goal, source);
      prdDraftList.appendChild(element);
    }

    for (const ambiguity of breakdown.ambiguities) {
      const item = document.createElement("li");
      item.textContent = ambiguity;
      prdAmbiguities.appendChild(item);
    }

    prdResults.hidden = false;
    prdStatus.textContent =
      `${breakdown.cards.length} draft cards generated successfully.`;

  } catch (error) {
    prdStatus.textContent = `Error: ${error.message}`;
  } finally {
    prdGenerateBtn.disabled = false;
  }
});


/* Select All Suggested Cards */

const prdSelectAllBtn = document.getElementById("prd-select-all-btn");

prdSelectAllBtn.addEventListener("click", () => {
    const checkboxes = document.querySelectorAll(
        ".prd-card-checkbox"
    );

    const allSelected =
        checkboxes.length > 0 &&
        Array.from(checkboxes).every(checkbox => checkbox.checked);

    checkboxes.forEach(checkbox => {
        checkbox.checked = !allSelected;
    });

    prdSelectAllBtn.textContent = allSelected
        ? "Select All"
        : "Deselect All";
});


/* Add Selected Draft Cards to the Board */

const prdAddSelectedBtn = document.getElementById(
  "prd-add-selected-btn"
);

prdAddSelectedBtn.addEventListener("click", async () => {
  const selectedCheckboxes = document.querySelectorAll(
    ".prd-card-checkbox:checked"
  );

  if (selectedCheckboxes.length === 0) {
    alert("Please select at least one card.");
    return;
  }

  const confirmed = confirm(
    `Add ${selectedCheckboxes.length} selected cards to the board?`
  );

  if (!confirmed) {
    return;
  }

  prdAddSelectedBtn.disabled = true;

  let addedCount = 0;
  let failedCount = 0;

  try {
    for (const checkbox of selectedCheckboxes) {
      const element = checkbox.closest(".prd-draft-card");
      const card = JSON.parse(element.dataset.card);

      const description = [
        `Goal: ${card.goal}`,
        "",
        "Acceptance Criteria:",
        ...card.acceptance_criteria.map(
          criterion => `- ${criterion}`
        ),
        "",
        `Dependencies: ${card.dependencies.join(", ") || "None"}`,
        `Source: ${card.prd_section}`
      ].join("\n").slice(0, 1000);

      try {
        const response = await apiFetch("/cards", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            title: card.title.trim(),
            description: description
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        addedCount++;
        element.remove();

      } catch (error) {
        failedCount++;
        console.error("Failed to add draft card:", error);

        if (error && error.status === 401) {
          break;
        }
      }
    }

    await loadCards();

    prdStatus.textContent =
      `${addedCount} cards added to the board. ` +
      `${failedCount} cards failed.`;

    prdSelectAllBtn.textContent = "Select All";

  } finally {
    prdAddSelectedBtn.disabled = false;
  }
});



/* AI Board Assistant Chat */

const assistantChatForm = document.getElementById("assistant-chat-form");
const assistantInput = document.getElementById("assistant-input");
const assistantMessages = document.getElementById("assistant-messages");
const assistantStatus = document.getElementById("assistant-status");
const assistantSendBtn = document.getElementById("assistant-send-btn");

// Only one proposal may be waiting for a decision at a time.
let pendingProposal = null;

function setAssistantChatEnabled(enabled) {
    assistantInput.disabled = !enabled;
    assistantSendBtn.disabled = !enabled;

    if (enabled) {
        assistantInput.focus();
    }
}

function appendAssistantMessage(text, sender) {
    const message = document.createElement("div");

    message.className = `assistant-message ${sender}`;
    message.textContent = text;

    assistantMessages.appendChild(message);
    assistantMessages.scrollTop = assistantMessages.scrollHeight;
}

async function readApiError(response) {
    let message = `HTTP ${response.status}`;

    try {
        const data = await response.json();

        if (typeof data.detail === "string") {
            message = data.detail;
        } else if (Array.isArray(data.detail)) {
            message = data.detail
                .map(item => item.msg || JSON.stringify(item))
                .join("; ");
        }
    } catch (_) {
        // Keep the status-based message.
    }

    return message;
}

function describeProposal(proposal) {
    if (proposal.action === "create_card") {
        return `Create a card titled "${proposal.title}".`;
    }

    if (proposal.action === "move_card") {
        const status = String(proposal.status).replaceAll("_", " ");
        return `Move card #${proposal.card_id} to "${status}".`;
    }

    if (proposal.action === "add_comment") {
        return (
            `Add a comment by ${proposal.author} ` +
            `to card #${proposal.card_id}.`
        );
    }

    return "Apply this proposed change.";
}

async function submitProposal(proposal) {
    let url = `${API_URL}/cards`;
    let method = "POST";
    let body = {};

    if (proposal.action === "create_card") {
        body = {
            title: proposal.title,
            description: proposal.description || ""
        };

        if (proposal.assignee) {
            body.assignee = proposal.assignee;
        }

    } else if (proposal.action === "move_card") {
        url = `${API_URL}/cards/${proposal.card_id}`;
        method = "PATCH";
        body = { status: proposal.status };

    } else if (proposal.action === "add_comment") {
        url = `${API_URL}/cards/${proposal.card_id}/comments`;
        method = "POST";
        body = {
            author: proposal.author,
            text: proposal.text
        };

    } else {
        throw new Error("Unsupported proposal.");
    }

    const response = await apiFetch(url.replace(API_URL, ""), {
        method: method,
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    });

    if (!response.ok) {
        throw new Error(await readApiError(response));
    }
}

function renderProposal(proposal) {
    const element = document.createElement("div");
    element.className = "assistant-proposal";

    const heading = document.createElement("h4");
    heading.textContent = "Confirm this change";

    const description = document.createElement("p");
    description.textContent = describeProposal(proposal);

    const errorMessage = document.createElement("p");
    errorMessage.className = "proposal-error";
    errorMessage.hidden = true;

    const actions = document.createElement("div");
    actions.className = "assistant-proposal-actions";

    const confirmButton = document.createElement("button");
    confirmButton.type = "button";
    confirmButton.textContent = "Confirm";

    const cancelButton = document.createElement("button");
    cancelButton.type = "button";
    cancelButton.className = "secondary";
    cancelButton.textContent = "Cancel";

    actions.append(confirmButton, cancelButton);
    element.append(heading, description, errorMessage, actions);
    assistantMessages.appendChild(element);
    assistantMessages.scrollTop = assistantMessages.scrollHeight;

    pendingProposal = proposal;
    setAssistantChatEnabled(false);
    assistantStatus.textContent =
        "Review the proposed change, then Confirm or Cancel.";

    confirmButton.addEventListener("click", async () => {
        if (pendingProposal !== proposal) {
            return;
        }

        confirmButton.disabled = true;
        cancelButton.disabled = true;
        errorMessage.hidden = true;
        assistantStatus.textContent = "Saving the confirmed change...";

        try {
            await submitProposal(proposal);

            pendingProposal = null;

            element.classList.add("confirmed");
            heading.textContent = "Change confirmed";
            actions.replaceChildren();

            const result = document.createElement("p");
            result.className = "proposal-result";
            result.textContent = "The board was updated successfully.";
            element.appendChild(result);

            assistantStatus.textContent = "Change saved.";

            await loadCards();

            if (
                !detailsModal.hidden &&
                proposal.action !== "create_card" &&
                String(detailsModal.dataset.cardId) ===
                    String(proposal.card_id)
            ) {
                await showCardDetails(Number(proposal.card_id));
            }

            setAssistantChatEnabled(true);

        } catch (error) {
            errorMessage.textContent =
                `Could not apply the change: ${error.message}`;
            errorMessage.hidden = false;
            assistantStatus.textContent = "The change was not saved.";

            confirmButton.disabled = false;
            cancelButton.disabled = false;
        }
    });

    cancelButton.addEventListener("click", () => {
        if (pendingProposal !== proposal) {
            return;
        }

        pendingProposal = null;

        element.classList.add("cancelled");
        heading.textContent = "Change cancelled";
        actions.replaceChildren();

        const result = document.createElement("p");
        result.className = "proposal-result";
        result.textContent = "No changes were made.";
        element.appendChild(result);

        assistantStatus.textContent =
            "Proposal cancelled. No changes were made.";
        setAssistantChatEnabled(true);
    });
}

assistantChatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (pendingProposal) {
        return;
    }

    const question = assistantInput.value.trim();

    if (!question) {
        return;
    }

    appendAssistantMessage(question, "user");

    assistantInput.value = "";
    setAssistantChatEnabled(false);
    assistantStatus.textContent = "Assistant is thinking...";

    try {
        const response = await apiFetch("/assistant/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: question
            })
        });

        if (!response.ok) {
            throw new Error(await readApiError(response));
        }

        const data = await response.json();

        appendAssistantMessage(data.reply, "bot");

        if (data.proposal) {
            renderProposal(data.proposal);
        } else {
            assistantStatus.textContent = "";
            setAssistantChatEnabled(true);
        }

    } catch (error) {
        appendAssistantMessage(
            "Sorry, I couldn't process your message. Please try again.",
            "bot"
        );

        assistantStatus.textContent = `Error: ${error.message}`;
        setAssistantChatEnabled(true);
    }
});



loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = loginUsernameInput.value.trim();
    const password = loginPasswordInput.value;

    loginError.hidden = true;
    loginSubmitButton.disabled = true;

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            throw new Error(
                response.status === 401
                    ? "Invalid username or password."
                    : "Sign in failed. Please try again."
            );
        }

        const data = await response.json();

        const session = {
            token: data.access_token,
            username: data.username,
            role: data.role
        };

        saveSession(session);
        loginPasswordInput.value = "";
        showApp(session);
        await loadCards();

    } catch (error) {
        loginError.textContent = error.message;
        loginError.hidden = false;
    } finally {
        loginSubmitButton.disabled = false;
    }
});


logoutButton.addEventListener("click", () => {
    clearSession();
    showLogin();
});


async function startApp() {
    const session = readSession();

    if (!session) {
        showLogin();
        return;
    }

    showApp(session);
    await checkApiHealth();
    await loadCards();
}

startApp();
