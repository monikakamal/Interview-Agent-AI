document.addEventListener("DOMContentLoaded", () => {

    // ============================================================
    // BACKEND CONFIGURATION
    // ============================================================

    const API_BASE = (typeof window !== "undefined" && window.location && window.location.origin && window.location.origin.startsWith("http")) 
        ? window.location.origin 
        : "http://127.0.0.1:8000";
    const INTERVIEW_ENDPOINT = `${API_BASE}/api/interview`;

    // ============================================================
    // STATE
    // ============================================================

    let questionCount = 0;
    const totalMinQuestions = 8;
    let sessionId = null;
    let interviewStarted = false;
    let interviewCompleted = false;
    let requestInProgress = false;

    // ============================================================
    // DOM ELEMENTS
    // ============================================================

    const candidateInput = document.getElementById("candidateId");
    const startBtn = document.getElementById("startBtn");
    const sendBtn = document.getElementById("sendBtn");
    const endBtn = document.getElementById("endBtn");
    const userInput = document.getElementById("userInput");
    const chatBox = document.getElementById("chatBox");
    const qCount = document.getElementById("qCount");
    const typingIndicator = document.getElementById("typingIndicator");
    const feedbackModal = document.getElementById("feedbackModal");
    const feedbackContent = document.getElementById("feedbackContent");
    const closeModalBtn = document.getElementById("closeModalBtn");

    // ============================================================
    // UPDATE QUESTION COUNTER
    // ============================================================

    function updateCounter() {
        if (qCount) {
            qCount.textContent = questionCount;
        }
    }

    // ============================================================
    // APPEND MESSAGE
    // ============================================================

    function appendMessage(sender, message) {
        if (!chatBox) return;

        const wrapper = document.createElement("div");

        if (sender === "user") {
            wrapper.className = "flex justify-end";
            const bubble = document.createElement("div");
            bubble.className = "bg-indigo-600 text-white rounded-xl py-2 px-4 max-w-[80%] text-sm whitespace-pre-wrap";
            bubble.textContent = String(message ?? "");
            wrapper.appendChild(bubble);
        }
        else if (sender === "agent") {
            wrapper.className = "flex justify-start";
            const bubble = document.createElement("div");
            bubble.className = "bg-slate-800 border border-slate-700 text-slate-100 rounded-xl py-3 px-4 max-w-[85%] text-sm flex gap-3";

            const icon = document.createElement("i");
            icon.className = "fa-solid fa-robot text-indigo-400 mt-1";

            const text = document.createElement("div");
            text.className = "whitespace-pre-wrap";
            text.textContent = String(message ?? "");

            bubble.appendChild(icon);
            bubble.appendChild(text);
            wrapper.appendChild(bubble);
        }
        else {
            wrapper.className = "text-center text-xs text-slate-500 my-2";
            wrapper.textContent = String(message ?? "");
        }

        chatBox.appendChild(wrapper);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // ============================================================
    // LOADING INDICATOR
    // ============================================================

    function setLoading(isLoading) {
        if (!typingIndicator) return;
        if (isLoading) {
            typingIndicator.classList.remove("hidden");
        } else {
            typingIndicator.classList.add("hidden");
        }
    }

    // ============================================================
    // ENABLE / DISABLE INPUTS
    // ============================================================

    function enableInput() {
        if (userInput) userInput.disabled = false;
        if (sendBtn) sendBtn.disabled = false;
        if (endBtn) endBtn.classList.remove("hidden");
        if (userInput) {
            userInput.placeholder = "Type your technical response here...";
            userInput.focus();
        }
    }

    function disableInput() {
        if (userInput) userInput.disabled = true;
        if (sendBtn) sendBtn.disabled = true;
    }

    // ============================================================
    // API CALL HELPER
    // ============================================================

    async function callInterviewAPI(payload) {
        const response = await fetch(INTERVIEW_ENDPOINT, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        let data;
        try {
            data = await response.json();
        } catch (error) {
            throw new Error("Backend returned invalid JSON.");
        }

        if (!response.ok) {
            const errorMessage =
                data?.detail ||
                data?.message ||
                `Backend error: HTTP ${response.status}`;
            throw new Error(errorMessage);
        }

        return data;
    }

    // ============================================================
    // START INTERVIEW
    // ============================================================

    async function startInterview() {
        if (requestInProgress) return;

        const candidateId = candidateInput ? candidateInput.value.trim() : "cand_001";

        if (!candidateId) {
            alert("Please enter Candidate ID.");
            if (candidateInput) candidateInput.focus();
            return;
        }

        requestInProgress = true;
        if (startBtn) startBtn.disabled = true;
        if (chatBox) chatBox.innerHTML = "";
        disableInput();
        setLoading(true);

        appendMessage("system", "Starting interview and loading candidate profile...");

        sessionId = `${candidateId}-${Date.now()}`;

        try {
            // ==========================================
            // YE WALA CODE YAHAN PASS KARNA HAI:
            // ==========================================
            const data = await callInterviewAPI({
                sessionId: sessionId,
                candidateId: candidateId,
                candidate: {
                    id: candidateId,
                    name: "Candidate",
                    completed_missions: [],
                    current_status: "active"
                }
            });

            if (data.sessionId) {
                sessionId = data.sessionId;
            }

            interviewStarted = true;
            interviewCompleted = false;
            questionCount = 1;
            updateCounter();

            appendMessage("agent", data.reply || "Welcome! Let's begin the technical interview.");
            enableInput();

        } catch (error) {
            console.error("Start Interview Error:", error);
            sessionId = null;
            interviewStarted = false;

            appendMessage("system", `Unable to connect to backend: ${error.message}`);
            if (startBtn) startBtn.disabled = false;
        } finally {
            requestInProgress = false;
            setLoading(false);
        }
    }

    // ============================================================
    // SEND MESSAGE / ANSWER
    // ============================================================

    async function sendMessage() {
        if (requestInProgress || !interviewStarted || interviewCompleted) {
            return;
        }

        const text = userInput ? userInput.value.trim() : "";
        if (!text) return;

        if (!sessionId) {
            appendMessage("system", "Invalid interview session.");
            return;
        }

        requestInProgress = true;
        disableInput();
        appendMessage("user", text);

        if (userInput) userInput.value = "";
        setLoading(true);

        try {
            const data = await callInterviewAPI({
                sessionId: sessionId,
                message: text
            });

            if (data.done === true) {
                interviewCompleted = true;
                interviewStarted = false;
                disableInput();

                appendMessage("agent", data.reply || "Interview completed.");

                if (data.feedback) {
                    showFeedback(data.feedback);
                }

                if (endBtn) endBtn.classList.add("hidden");
                return;
            }

            questionCount++;
            updateCounter();

            appendMessage("agent", data.reply || "Please continue with your answer.");

        } catch (error) {
            console.error("Send Message Error:", error);
            appendMessage("system", `Failed to process your response: ${error.message}`);
        } finally {
            requestInProgress = false;
            setLoading(false);

            if (!interviewCompleted && interviewStarted) {
                if (sendBtn) sendBtn.disabled = false;
                if (userInput) {
                    userInput.disabled = false;
                    userInput.focus();
                }
            }
        }
    }

    // ============================================================
    // END INTERVIEW
    // ============================================================

    function endInterview() {
        if (!interviewStarted) return;

        const confirmed = window.confirm("Are you sure you want to finish the interview?");
        if (!confirmed) return;

        appendMessage("system", "Please complete the required interview questions so the backend can generate final evaluation.");
    }

    // ============================================================
    // SHOW FEEDBACK MODAL
    // ============================================================

    function showFeedback(feedback) {
        if (!feedbackContent || !feedbackModal) return;

        feedbackContent.innerHTML = "";

        if (feedback.summary) {
            const summaryBox = document.createElement("div");
            summaryBox.className = "p-4 bg-slate-800 rounded-lg border border-slate-700";
            summaryBox.innerHTML = `
                <h3 class="font-semibold text-indigo-400 mb-2">Overall Summary</h3>
                <p class="text-sm text-slate-300">${String(feedback.summary)}</p>
            `;
            feedbackContent.appendChild(summaryBox);
        }

        createFeedbackList("Key Strengths", feedback.strengths, "emerald");
        createFeedbackList("Areas for Improvement", feedback.gaps, "rose");
        createFeedbackList("Recommended Next Steps", feedback.next, "indigo");

        feedbackModal.classList.remove("hidden");
        feedbackModal.classList.add("flex");
    }

    function createFeedbackList(title, items, color) {
        if (!Array.isArray(items) || items.length === 0 || !feedbackContent) return;

        const section = document.createElement("div");
        const heading = document.createElement("h3");
        heading.className = `font-semibold text-${color}-400 mb-2`;
        heading.textContent = title;
        section.appendChild(heading);

        const list = document.createElement("ul");
        list.className = "space-y-2";

        items.forEach((item) => {
            const li = document.createElement("li");
            li.className = "bg-slate-800 border border-slate-700 rounded-lg p-3 text-xs text-slate-300";
            li.textContent = String(item);
            list.appendChild(li);
        });

        section.appendChild(list);
        feedbackContent.appendChild(section);
    }

    function closeModal() {
        if (feedbackModal) {
            feedbackModal.classList.add("hidden");
            feedbackModal.classList.remove("flex");
        }
    }

    // ============================================================
    // EVENT LISTENERS
    // ============================================================

    if (startBtn) startBtn.addEventListener("click", startInterview);
    if (sendBtn) sendBtn.addEventListener("click", sendMessage);
    if (endBtn) endBtn.addEventListener("click", endInterview);
    if (closeModalBtn) closeModalBtn.addEventListener("click", closeModal);

    if (userInput) {
        userInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeModal();
        }
    });

});