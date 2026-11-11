
const API_URL = "http://127.0.0.1:8000";

// Get cards from the FastAPI backend
async function loadCards() {
    try {
        const response = await fetch(`${API_URL}/cards`);

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
        alert("Could not connect to the Cards API.");
    }
}

// Load cards when the page opens
document.addEventListener("DOMContentLoaded", loadCards);


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
        const response = await fetch(`${API_URL}/cards`, {
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
        alert("Could not create the card.");
    }
});



const detailsModal = document.getElementById("details-modal");
const closeDetailsButton = document.getElementById("close-details-btn");

// Load and display one card's details
async function showCardDetails(cardId) {
    try {
        const response = await fetch(`${API_URL}/cards/${cardId}`);

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
        alert("Could not load card details.");
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
        const response = await fetch(`${API_URL}/cards/${cardId}`, {
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
        alert("Could not save the assignment.");
    }
});


const removeAssigneeButton = document.getElementById("remove-assignee-btn");

removeAssigneeButton.addEventListener("click", async () => {
    const cardId = detailsModal.dataset.cardId;

    try {
        const response = await fetch(`${API_URL}/cards/${cardId}`, {
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
        alert("Could not remove the assignment.");
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
        const response = await fetch(`${API_URL}/cards/${cardId}`, {
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
        alert("Could not move the card to the next stage.");
    }
});


const deleteCardButton = document.getElementById("delete-card-btn");

deleteCardButton.addEventListener("click", async () => {
    const cardId = detailsModal.dataset.cardId;

    if (!cardId) return;

    const confirmed = confirm(
        "Are you sure you want to delete this card?"
    );

    if (!confirmed) return;

    try {
        const response = await fetch(`${API_URL}/cards/${cardId}`, {
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
        alert("Could not delete the card.");
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
        const response = await fetch(`${API_URL}/cards/${cardId}`);

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
        alert("Could not load the card for editing.");
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
        const response = await fetch(`${API_URL}/cards/${cardId}`, {
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
        alert("Could not save changes.");
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

document.addEventListener("DOMContentLoaded", checkApiHealth);


async function loadComments(cardId) {
    const commentsList = document.getElementById("comments-list");

    try {
        const response = await fetch(
            `${API_URL}/cards/${cardId}/comments`
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
        commentsList.textContent = "Could not load comments.";
    }
}


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
        const response = await fetch(
            `${API_URL}/cards/${cardId}/comments`,
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
        alert("Could not add the comment.");
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
    const response = await fetch(
      `http://127.0.0.1:8000/prd/preview?use_ocr=${prdUseOcr.checked}`,
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
        const response = await fetch(`${API_URL}/cards`, {
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

function appendAssistantMessage(text, sender) {
    const message = document.createElement("div");

    message.className = `assistant-message ${sender}`;
    message.textContent = text;

    assistantMessages.appendChild(message);
    assistantMessages.scrollTop = assistantMessages.scrollHeight;
}

assistantChatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const question = assistantInput.value.trim();

    if (!question) {
        return;
    }

    appendAssistantMessage(question, "user");

    assistantInput.value = "";
    assistantInput.disabled = true;
    assistantSendBtn.disabled = true;
    assistantStatus.textContent = "Assistant is thinking...";

    try {
        const response = await fetch(`${API_URL}/assistant/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: question
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        appendAssistantMessage(data.reply, "bot");
        assistantStatus.textContent = "";

    } catch (error) {
        appendAssistantMessage(
            "Sorry, I couldn't process your message. Please try again.",
            "bot"
        );

        assistantStatus.textContent = `Error: ${error.message}`;

    } finally {
        assistantInput.disabled = false;
        assistantSendBtn.disabled = false;
        assistantInput.focus();
    }
});
