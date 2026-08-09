document.addEventListener("DOMContentLoaded", () => {

    // ============================================================
    // DOM ELEMENTS
    // ============================================================

    const responseInput =
        document.getElementById("response-input");

    const sendBtn =
        document.querySelector(".btn-success");

    const speechBubble =
        document.querySelector(".speech-bubble");

    const questionDetails =
        document.querySelector(".question-card p");

    const questionBadge =
        document.querySelector(".badge-blue");

    const typingIndicator =
        document.querySelector(".typing-indicator");

    const endInterviewBtn =
        document.querySelector(".btn-danger");

    const tabs =
        document.querySelectorAll(".tab");

    const elapsedTimeEl =
        document.querySelector(
            ".bottom-bar div:nth-child(1) strong"
        );

    const completedQuestionsEl =
        document.querySelector(
            ".bottom-bar div:nth-child(2) strong"
        );

    const scoreTextEl =
        document.querySelector(".score-text");


    // ============================================================
    // BACKEND CONFIGURATION
    // ============================================================

    const API_BASE =
        "http://127.0.0.1:8000";

    const INTERVIEW_ENDPOINT =
        `${API_BASE}/api/interview`;


    // ============================================================
    // INTERVIEW STATE
    // ============================================================

    let currentQuestion = 0;

    const totalMinQuestions = 8;

    let secondsElapsed = 0;

    let timerInterval = null;

    let sessionId = null;

    let candidateId = "MONIK_SHARMA";

    let interviewStarted = false;

    let interviewCompleted = false;


    // ============================================================
    // TIMER
    // ============================================================

    function startTimer() {

        if (timerInterval !== null) {
            return;
        }

        timerInterval = setInterval(() => {

            secondsElapsed++;

            const mins =
                String(
                    Math.floor(secondsElapsed / 60)
                ).padStart(2, "0");

            const secs =
                String(
                    secondsElapsed % 60
                ).padStart(2, "0");

            if (elapsedTimeEl) {

                elapsedTimeEl.textContent =
                    `${mins}:${secs}`;
            }

        }, 1000);
    }


    startTimer();


    // ============================================================
    // TAB SWITCHING
    // ============================================================

    tabs.forEach((tab) => {

        tab.addEventListener("click", () => {

            tabs.forEach((t) => {
                t.classList.remove("active");
            });

            tab.classList.add("active");
        });

    });


    // ============================================================
    // TYPING EFFECT
    // ============================================================

    function streamAIText(
        text,
        targetElement,
        callback
    ) {

        if (!targetElement) {
            return;
        }

        targetElement.textContent = "";

        let index = 0;

        if (typingIndicator) {
            typingIndicator.style.display = "block";
        }


        const interval =
            setInterval(() => {

                if (index < text.length) {

                    targetElement.textContent +=
                        text.charAt(index);

                    index++;

                } else {

                    clearInterval(interval);

                    if (typingIndicator) {
                        typingIndicator.style.display =
                            "none";
                    }

                    if (callback) {
                        callback();
                    }
                }

            }, 20);
    }


    // ============================================================
    // START INTERVIEW
    // ============================================================

    async function startInterview() {

        if (interviewStarted) {
            return;
        }

        /*
         * Generate unique session ID.
         *
         * Every candidate gets a separate interview session.
         */
        sessionId =
            `${candidateId}-${Date.now()}`;


        try {

            if (typingIndicator) {
                typingIndicator.style.display =
                    "block";
            }


            const response =
                await fetch(
                    INTERVIEW_ENDPOINT,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            sessionId:
                                sessionId,

                            candidateId:
                                candidateId

                        })
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Unable to start interview."
                );
            }


            interviewStarted = true;

            interviewCompleted = false;

            currentQuestion = 1;


            updateProgress();


            streamAIText(
                data.reply || "Interview started.",
                speechBubble,
                () => {

                    questionDetails.textContent =
                        "Please provide your answer below.";

                }
            );


        } catch (error) {

            console.error(
                "Start Interview Error:",
                error
            );


            if (typingIndicator) {
                typingIndicator.style.display =
                    "none";
            }


            showError(
                error.message
            );
        }
    }


    // ============================================================
    // SEND CANDIDATE ANSWER
    // ============================================================

    async function handleSendAnswer() {

        const userText =
            responseInput.value.trim();


        if (!userText) {
            return;
        }


        if (!sessionId) {

            showError(
                "Interview has not been started."
            );

            return;
        }


        if (interviewCompleted) {

            showError(
                "Interview has already been completed."
            );

            return;
        }


        /*
         * Clear input immediately.
         */
        responseInput.value = "";


        /*
         * Disable button while waiting for backend.
         */
        sendBtn.disabled = true;

        responseInput.disabled = true;


        /*
         * Show candidate answer in UI.
         *
         * This function assumes your HTML contains
         * a suitable chat area. If not, the backend
         * integration still works.
         */
        addCandidateMessage(userText);


        try {

            if (typingIndicator) {
                typingIndicator.style.display =
                    "block";
            }


            const response =
                await fetch(
                    INTERVIEW_ENDPOINT,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            sessionId:
                                sessionId,

                            message:
                                userText

                        })
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Unable to process answer."
                );
            }


            // ====================================================
            // INTERVIEW COMPLETED
            // ====================================================

            if (data.done === true) {

                interviewCompleted = true;

                interviewStarted = false;


                clearInterval(
                    timerInterval
                );


                streamAIText(
                    data.reply ||
                    "Interview completed.",
                    speechBubble
                );


                if (data.feedback) {

                    displayFeedback(
                        data.feedback
                    );
                }


                if (sendBtn) {
                    sendBtn.disabled = true;
                }

                if (responseInput) {
                    responseInput.disabled = true;
                }


                if (scoreTextEl) {

                    scoreTextEl.textContent =
                        "Completed";
                }


                return;
            }


            // ====================================================
            // NEXT QUESTION / FOLLOW-UP
            // ====================================================

            currentQuestion++;

            updateProgress();


            streamAIText(
                data.reply ||
                "Please continue.",
                speechBubble,
                () => {

                    questionDetails.textContent =
                        "Follow-up question based on your previous response.";

                }
            );


        } catch (error) {

            console.error(
                "Interview API Error:",
                error
            );


            showError(
                error.message
            );

        } finally {

            if (!interviewCompleted) {

                sendBtn.disabled = false;

                responseInput.disabled = false;

                responseInput.focus();
            }

            if (typingIndicator) {

                typingIndicator.style.display =
                    "none";
            }
        }
    }


    // ============================================================
    // PROGRESS UPDATE
    // ============================================================

    function updateProgress() {

        if (questionBadge) {

            questionBadge.textContent =
                `[Q ${currentQuestion}/${totalMinQuestions}]`;
        }


        if (completedQuestionsEl) {

            const completed =
                Math.max(
                    currentQuestion - 1,
                    0
                );

            completedQuestionsEl.textContent =
                `${completed}/${totalMinQuestions}`;
        }
    }


    // ============================================================
    // CANDIDATE MESSAGE
    // ============================================================

    function addCandidateMessage(text) {

        /*
         * If your HTML does not contain a dedicated
         * chat container, this function simply does
         * nothing.
         *
         * Backend communication is independent.
         */

        const chatContainer =
            document.querySelector(
                ".chat-container"
            );

        if (!chatContainer) {
            return;
        }


        const message =
            document.createElement("div");

        message.className =
            "candidate-message";


        message.textContent =
            text;


        chatContainer.appendChild(
            message
        );


        chatContainer.scrollTop =
            chatContainer.scrollHeight;
    }


    // ============================================================
    // FEEDBACK
    // ============================================================

    function displayFeedback(feedback) {

        console.log(
            "FINAL INTERVIEW FEEDBACK:",
            feedback
        );


        /*
         * Your current UI can be connected to the
         * feedback fields here.
         */

        if (feedback.summary) {

            questionDetails.textContent =
                feedback.summary;
        }


        if (
            Array.isArray(
                feedback.strengths
            )
        ) {

            console.log(
                "Strengths:",
                feedback.strengths
            );
        }


        if (
            Array.isArray(
                feedback.gaps
            )
        ) {

            console.log(
                "Gaps:",
                feedback.gaps
            );
        }


        if (
            Array.isArray(
                feedback.next
            )
        ) {

            console.log(
                "Next Steps:",
                feedback.next
            );
        }
    }


    // ============================================================
    // ERROR DISPLAY
    // ============================================================

    function showError(message) {

        console.error(
            "Interview Agent:",
            message
        );


        if (speechBubble) {

            speechBubble.textContent =
                `Error: ${message}`;
        }
    }


    // ============================================================
    // SEND BUTTON
    // ============================================================

    sendBtn.addEventListener(
        "click",
        handleSendAnswer
    );


    // ============================================================
    // ENTER KEY
    // ============================================================

    responseInput.addEventListener(
        "keypress",
        (event) => {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                handleSendAnswer();
            }

        }
    );


    // ============================================================
    // END INTERVIEW
    // ============================================================

    endInterviewBtn.addEventListener(
        "click",
        () => {

            if (!interviewStarted) {
                return;
            }


            const confirmed =
                confirm(
                    "Are you sure you want to end the interview?"
                );


            if (!confirmed) {
                return;
            }


            /*
             * Do NOT call /feedback here.
             *
             * The backend should generate final
             * feedback when the interview reaches
             * its completion condition.
             */

            showError(
                "Complete the required interview questions to generate final feedback."
            );
        }
    );


    // ============================================================
    // START INTERVIEW AUTOMATICALLY
    // ============================================================

    startInterview();

});
// ==========================================
// 1. API Base URL & Main Fetch Function
// ==========================================
const API_BASE_URL = "http://127.0.0.1:8000";

async function sendDataToBackend(sessionId, candidateProfile, messageText) {
    try {
        const response = await fetch(`${API_BASE_URL}/interview`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                sessionId: sessionId,
                candidate: candidateProfile, 
                message: messageText
            })
        });

        if (!response.ok) {
            throw new Error("Server error occurred while connecting to backend.");
        }

        const data = await response.json();
        return data; // Isme { reply, done, feedback } aayega
    } catch (error) {
        console.error("Connection failed:", error);
    }
}

// ==========================================
// 2. Event Listeners / UI Logic (Jo pehle se ya aap likh rahe hain)
// ==========================================
// Jaise hi user message bhejega, aap is function ko call karenge:
async function handleUserSubmit(userInput) {
    let sessionId = "session_123"; // Apni session ID ya candidate object yahan dein
    let candidateProfile = null;   // Pehli request mein candidate data, baad mein null bhi chalega
    
    // Upar wala function call kiya:
    let result = await sendDataToBackend(sessionId, candidateProfile, userInput);
    
    if (result) {
        console.log("Agent ka jawab:", result.reply);
        // Yahan UI par message render karne ka code likhein
    }
}