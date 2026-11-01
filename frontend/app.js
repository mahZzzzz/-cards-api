
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


