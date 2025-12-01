document.addEventListener('DOMContentLoaded', () => {

    /* -----------------------------
       Helper: Show Toast/Alert
    ------------------------------ */
    const showMessage = (msg, type = 'info') => {
        // Simple alert for now, could be upgraded to a toast library later
        alert(msg);
    };

    /* -----------------------------
       Apply Template
    ------------------------------ */
    const applyTemplateBtn = document.getElementById("applyTemplateBtn");
    if (applyTemplateBtn) {
        applyTemplateBtn.onclick = async () => {
            const select = document.getElementById("templateSelect");
            const id = select.value;
            if (!id) return showMessage("Please pick a template first.", "warning");

            try {
                const res = await fetch("/api/templates/" + id);
                if (!res.ok) throw new Error("Failed to fetch template");
                const t = await res.json();

                document.getElementById("subject").value = t.subject || "";
                document.getElementById("body").value = t.body || "";
                showMessage("Template applied!", "success");
            } catch (err) {
                showMessage(err.message, "error");
            }
        };
    }

    /* -----------------------------
       UNIVERSAL AI FUNCTION
    ------------------------------ */
    async function callAI(route, textFieldId, updateSuggestion = false, btnId = null) {
        const textField = document.getElementById(textFieldId);
        if (!textField) return;

        const text = textField.value;
        if (!text.trim()) return showMessage("Please enter some text first.", "warning");

        // Loading State
        let originalBtnText = "";
        const btn = document.getElementById(btnId);
        if (btn) {
            originalBtnText = btn.innerHTML;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            btn.disabled = true;
        }

        try {
            const res = await fetch(route, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text })
            });

            const j = await res.json();

            if (!j.ok) {
                throw new Error(j.error || "AI error");
            }

            // Accept any field returned by backend
            let result = j.text || j.reply || j.rewritten || j.fixed;

            if (!result) {
                result = "Error: No response from AI.";
            }

            if (updateSuggestion) {
                const box = document.getElementById("aiSuggestionBox");
                const content = document.getElementById("aiSuggestionText");
                if (box && content) {
                    box.style.display = "block";
                    content.innerText = result;
                }
            } else {
                textField.value = result;
            }
        } catch (err) {
            showMessage(err.message, "error");
        } finally {
            // Restore Button State
            if (btn) {
                btn.innerHTML = originalBtnText;
                btn.disabled = false;
            }
        }
    }

    /* -----------------------------
       AI BUTTON HANDLERS
    ------------------------------ */
    const aiCompleteBtn = document.getElementById("aiComplete");
    if (aiCompleteBtn) {
        aiCompleteBtn.onclick = () => callAI("/ai/autocomplete", "body", true, "aiComplete");
    }

    const aiReplyBtn = document.getElementById("aiReply");
    if (aiReplyBtn) {
        aiReplyBtn.onclick = () => callAI("/ai/autoreply", "body", false, "aiReply");
    }

    const aiRewriteBtn = document.getElementById("aiRewrite");
    if (aiRewriteBtn) {
        aiRewriteBtn.onclick = () => callAI("/ai/rewrite", "body", false, "aiRewrite");
    }

    const aiGrammarBtn = document.getElementById("aiGrammar");
    if (aiGrammarBtn) {
        aiGrammarBtn.onclick = () => callAI("/ai/grammar", "body", false, "aiGrammar");
    }

    /* -----------------------------
       Save OpenAI Key
    ------------------------------ */
    const saveKeyBtn = document.getElementById("saveKey");
    if (saveKeyBtn) {
        saveKeyBtn.onclick = async () => {
            const keyInput = document.getElementById("openaiKey");
            const key = keyInput.value.trim();
            if (!key) return showMessage("Enter key first", "warning");

            try {
                const res = await fetch("/save_key", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ openai_key: key })
                });

                const j = await res.json();
                if (j.ok) {
                    showMessage("API key saved successfully!", "success");
                    keyInput.value = ""; // Clear for security
                } else {
                    throw new Error(j.msg);
                }
            } catch (err) {
                showMessage(err.message, "error");
            }
        };
    }

    /* -----------------------------
       SEND EMAIL
    ------------------------------ */
    const sendBtn = document.getElementById("sendBtn");
    if (sendBtn) {
        sendBtn.onclick = async () => {
            const to = document.getElementById("to").value;
            const subject = document.getElementById("subject").value;
            const body = document.getElementById("body").value;

            if (!to || !subject || !body) {
                return showMessage("Please fill in all fields (To, Subject, Body).", "warning");
            }

            // Loading state
            const originalText = sendBtn.innerText;
            sendBtn.innerText = "Sending...";
            sendBtn.disabled = true;

            try {
                const res = await fetch("/send", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ to, subject, body })
                });

                const j = await res.json();
                if (j.ok) {
                    showMessage("Email sent successfully!", "success");
                } else {
                    throw new Error(j.error);
                }
            } catch (err) {
                showMessage(err.message, "error");
            } finally {
                sendBtn.innerText = originalText;
                sendBtn.disabled = false;
            }
        };
    }
});
