frappe.ready(() => {
  // Load Font Awesome CSS first
  frappe.require(
    [
      "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css",
    ],
    initializeForm
  );

  function initializeForm() {
    frappe.web_form.on("template", (_, value) => {
      showLoadingState();
      fetchTemplate(value);
    });

    function showLoadingState() {
      frappe.web_form.set_df_property(
        "dynamic_html",
        "options",
        `
        <div class="text-center" style="padding: 20px;">
          <div class="spinner-border text-primary" role="status">
            <span class="sr-only">Loading...</span>
          </div>
          <p>Loading questions...</p>
        </div>
      `
      );
    }

    function fetchTemplate(templateName) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "Feedback Template",
          name: templateName,
        },
        callback: handleTemplateResponse,
        error: showErrorState,
      });
    }

    function handleTemplateResponse(response) {
      if (response.message) {
        window._feedback_questions = response.message.feedback_question || [];
        renderQuestions(window._feedback_questions);
      }
    }

    function showErrorState() {
      frappe.web_form.set_df_property(
        "dynamic_html",
        "options",
        `
        <div class="text-center text-danger" style="padding: 20px;">
          <i class="fa fa-exclamation-circle fa-2x"></i>
          <p>Failed to load questions. Please try again.</p>
        </div>
      `
      );
    }

    function renderQuestions(questions) {
      let html = createFormContainer();

      questions.forEach((q, index) => {
        html += createQuestionBlock(q, index);
      });

      html += `</div>`; // Close container

      frappe.web_form.set_df_property("dynamic_html", "options", html);
      addQuestionBlockHoverEffects();
      initializeStarRatings();
      initializeClearButtons();
      setTimeout(checkAllRequiredFilled, 100);
    }

    function createFormContainer() {
      return `
        <div class="feedback-form-container" style="
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
          background: #f8f9fa;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.05);
          transition: background 0.3s ease;
        ">
      `;
    }

    function createQuestionBlock(question, index) {
      const isRequired = question.reqd ? "required" : "";
      const fieldId = `q-${index}`;

      let html = `
        <div class="question-block card" style="
          margin-bottom: 20px;
          border: 1px solid #e5e9f2;
          border-radius: 6px;
          padding: 15px;
          transition: all 0.2s;
          background: white;
          position: relative;
        ">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <label for="${fieldId}" style="
              display: block;
              margin-bottom: 10px;
              font-weight: 500;
              color: #2e3a59;
            ">
              <span style="color: #5e6c84;">Q${index + 1}:</span> ${
        question.question
      }
              ${question.reqd ? ' <span style="color: #ff5630">*</span>' : ""}
            </label>
            ${createClearButton(question.fieldtype, index)}
          </div>
          ${createQuestionField(question, index, isRequired, fieldId)}
        </div>
      `;

      return html;
    }

    function createClearButton(fieldType, index) {
      if (
        ["Multiple Choice", "Rating", "Checkboxes", "Dropdown"].includes(
          fieldType
        )
      ) {
        return `
          <button class="btn-clear-selection" data-question-index="${index}" style="
            background: none;
            border: none;
            color: #64748b;
            font-size: 12px;
            cursor: pointer;
            display: none;
            align-items: center;
            padding: 2px 8px;
            border-radius: 4px;
          ">
            <i class="fa fa-times" style="margin-right: 4px;"></i> Clear
          </button>
        `;
      } else if (["Paragraph", "Short Text"].includes(fieldType)) {
        return `
          <button class="btn-clear-text" data-question-index="${index}" style="
            position: absolute;
            right: 8px;
            top: 8px;
            background: none;
            border: none;
            color: #64748b;
            cursor: pointer;
            display: none;
          ">
            <i class="fa fa-times"></i>
          </button>
        `;
      }
      return "";
    }

    function createQuestionField(question, index, isRequired, fieldId) {
      switch (question.fieldtype) {
        case "Multiple Choice":
          return createMultipleChoiceField(
            question,
            index,
            isRequired,
            fieldId
          );
        case "Paragraph":
          return createParagraphField(index, isRequired, fieldId);
        case "Short Text":
          return createShortTextField(index, isRequired, fieldId);
        case "Rating":
          return createRatingField(question, index, isRequired);
        case "Checkboxes":
          return createCheckboxesField(question, index, fieldId);
        case "Dropdown":
          return createDropdownField(question, index, isRequired, fieldId);
        default:
          return "";
      }
    }

    function createMultipleChoiceField(question, index, isRequired, fieldId) {
      const opts = question.options.split("\n").filter((opt) => opt.trim());
      let html = `<div class="options-container" style="display: flex; flex-direction: column; gap: 8px;">`;

      opts.forEach((opt) => {
        const trimmedOpt = opt.trim();
        html += `
          <div class="form-check">
            <input class="form-check-input" type="radio" 
              name="q${index}" id="${fieldId}-${trimmedOpt.replace(
          /\s+/g,
          "-"
        )}" 
              value="${trimmedOpt}" ${isRequired}>
            <label class="form-check-label" for="${fieldId}-${trimmedOpt.replace(
          /\s+/g,
          "-"
        )}">
              ${trimmedOpt}
            </label>
          </div>
        `;
      });

      return html + `</div>`;
    }

    function createParagraphField(index, isRequired, fieldId) {
      return `
        <textarea class="form-control" rows="4" 
          id="${fieldId}" name="q${index}" ${isRequired}
          style="width: 100%; border-radius: 4px; border: 1px solid #dfe1e6; padding: 8px;"
          placeholder="Type your answer here..."></textarea>
      `;
    }

    function createShortTextField(index, isRequired, fieldId) {
      return `
        <input type="text" class="form-control"
          id="${fieldId}" name="q${index}" ${isRequired}
          style="width: 100%; border-radius: 4px; border: 1px solid #dfe1e6; padding: 8px;"
          placeholder="Type your answer here...">
      `;
    }

    function createRatingField(question, index, isRequired) {
      const maxRating = question.options
        ? parseInt(question.options.trim()) || 5
        : 5;
      return `
        <div class="star-rating-container" data-question-index="${index}" style="margin: 10px 0;">
          <div class="star-rating" style="display: flex; gap: 10px; align-items: center;">
            ${Array.from({ length: maxRating }, (_, i) => {
              const value = i + 1;
              return `
                <div style="display: flex; flex-direction: column; align-items: center;">
                  <span style="font-size: 12px; color: #64748b; margin-bottom: 5px;">${value}</span>
                  <i class="fa fa-star rating-star" 
                    data-value="${value}" 
                    style="cursor: pointer; font-size: 24px; color: #e5e9f2;"></i>
                </div>
              `;
            }).join("")}
          </div>
          <input type="hidden" name="q${index}" id="rating-value-${index}" ${isRequired}>
          <div class="rating-text" style="margin-top: 5px; font-size: 14px; color: #64748b;">
            Select rating (1-${maxRating})
          </div>
        </div>
      `;
    }

    function createCheckboxesField(question, index, fieldId) {
      const opts = question.options.split("\n").filter((opt) => opt.trim());
      let html = `<div class="options-container" style="display: flex; flex-direction: column; gap: 8px;">`;

      opts.forEach((opt) => {
        const trimmedOpt = opt.trim();
        const checkboxId = `${fieldId}-${trimmedOpt.replace(/\s+/g, "-")}-chk`;
        html += `
          <div class="form-check">
            <input class="form-check-input" type="checkbox" 
              id="${checkboxId}" name="q${index}[]" 
              value="${trimmedOpt}">
            <label class="form-check-label" for="${checkboxId}">
              ${trimmedOpt}
            </label>
          </div>
        `;
      });

      return html + `</div>`;
    }

    function createDropdownField(question, index, isRequired, fieldId) {
      const opts = question.options.split("\n").filter((opt) => opt.trim());
      let html = `
        <select class="form-select" id="${fieldId}" name="q${index}" ${isRequired}
          style="width: 100%; border-radius: 4px; border: 1px solid #dfe1e6; padding: 8px;">
          <option value="" selected disabled>Select an option</option>
      `;

      opts.forEach((opt) => {
        const trimmedOpt = opt.trim();
        html += `<option value="${trimmedOpt}">${trimmedOpt}</option>`;
      });

      return html + `</select>`;
    }

    function addQuestionBlockHoverEffects() {
      document.querySelectorAll(".question-block").forEach((block) => {
        block.addEventListener("mouseenter", () => {
          block.style.boxShadow = "0 2px 8px rgba(0,0,0,0.08)";
          block.style.borderColor = "#c1c7d0";
        });
        block.addEventListener("mouseleave", () => {
          block.style.boxShadow = "none";
          block.style.borderColor = "#e5e9f2";
        });
      });
    }

    function initializeStarRatings() {
      document
        .querySelectorAll(".star-rating-container")
        .forEach((container) => {
          const index = container.getAttribute("data-question-index");
          const stars = container.querySelectorAll(".rating-star");
          const hiddenInput = container.querySelector(`#rating-value-${index}`);
          const ratingText = container.querySelector(".rating-text");
          const clearBtn = container
            .closest(".question-block")
            .querySelector(".btn-clear-selection");

          // Set initial empty state
          stars.forEach((star) => {
            star.style.color = "#e5e9f2"; // Light gray for unselected
          });

          stars.forEach((star) => {
            star.addEventListener("mouseover", function () {
              const value = parseInt(this.getAttribute("data-value"));

              // Highlight stars up to the hovered one
              stars.forEach((s) => {
                const sValue = parseInt(s.getAttribute("data-value"));
                if (sValue <= value) {
                  s.style.color = "#ffc107"; // Orange for selected
                } else {
                  s.style.color = "#e5e9f2"; // Light gray for unselected
                }
              });
            });

            star.addEventListener("click", function () {
              const value = parseInt(this.getAttribute("data-value"));
              hiddenInput.value = value;

              // Update display to show selected rating
              stars.forEach((s) => {
                const sValue = parseInt(s.getAttribute("data-value"));
                if (sValue <= value) {
                  s.style.color = "#ffc107"; // Orange for selected
                } else {
                  s.style.color = "#e5e9f2"; // Light gray for unselected
                }
              });

              // Show selected rating text
              ratingText.textContent = `Selected: ${value} star${
                value !== 1 ? "s" : ""
              }`;
              ratingText.style.color = "#2e3a59"; // Darker text for selected

              // Show clear button
              if (clearBtn) clearBtn.style.display = "flex";

              checkAllRequiredFilled();
            });
          });

          // Handle mouse leave to show current selection
          container
            .querySelector(".star-rating")
            .addEventListener("mouseleave", function () {
              const currentValue = parseInt(hiddenInput.value);
              if (!currentValue) {
                stars.forEach((star) => {
                  star.style.color = "#e5e9f2"; // Light gray for unselected
                });
                ratingText.textContent = `Select rating (1-${stars.length})`;
                ratingText.style.color = "#64748b"; // Lighter text for unselected
              } else {
                stars.forEach((star) => {
                  const sValue = parseInt(star.getAttribute("data-value"));
                  if (sValue <= currentValue) {
                    star.style.color = "#ffc107"; // Orange for selected
                  } else {
                    star.style.color = "#e5e9f2"; // Light gray for unselected
                  }
                });
                ratingText.textContent = `Selected: ${currentValue} star${
                  currentValue !== 1 ? "s" : ""
                }`;
                ratingText.style.color = "#2e3a59"; // Darker text for selected
              }
            });
        });
    }

    function initializeClearButtons() {
      initializeSelectionClearButtons();
      initializeTextClearButtons();
    }

    function initializeSelectionClearButtons() {
      document.querySelectorAll(".btn-clear-selection").forEach((btn) => {
        const index = btn.getAttribute("data-question-index");
        const question = window._feedback_questions[index];

        if (question.fieldtype === "Multiple Choice") {
          setupMultipleChoiceClear(btn, index);
        } else if (question.fieldtype === "Rating") {
          setupRatingClear(btn, index);
        } else if (question.fieldtype === "Dropdown") {
          setupDropdownClear(btn, index);
        } else if (question.fieldtype === "Checkboxes") {
          setupCheckboxesClear(btn, index);
        }
      });
    }

    function setupMultipleChoiceClear(btn, index) {
      const radioButtons = document.querySelectorAll(`input[name="q${index}"]`);
      radioButtons.forEach((radio) => {
        radio.addEventListener("change", function () {
          btn.style.display = this.checked ? "flex" : "none";
          checkAllRequiredFilled();
        });
      });

      btn.addEventListener("click", function (e) {
        e.preventDefault();
        radioButtons.forEach((radio) => (radio.checked = false));
        btn.style.display = "none";
        checkAllRequiredFilled();
      });
    }

    function setupRatingClear(btn, index) {
      const hiddenInput = document.querySelector(`#rating-value-${index}`);
      const stars = document.querySelectorAll(
        `.star-rating-container[data-question-index="${index}"] .rating-star`
      );
      const ratingText = document.querySelector(
        `.star-rating-container[data-question-index="${index}"] .rating-text`
      );
      const maxRating = window._feedback_questions[index].options
        ? parseInt(window._feedback_questions[index].options.trim()) || 5
        : 5;

      hiddenInput.addEventListener("change", function () {
        btn.style.display = this.value ? "flex" : "none";
      });

      btn.addEventListener("click", function (e) {
        e.preventDefault();
        hiddenInput.value = "";
        stars.forEach((star) => (star.style.color = "#e5e9f2"));
        ratingText.textContent = `Select rating (1-${maxRating})`;
        ratingText.style.color = "#64748b";
        btn.style.display = "none";
        checkAllRequiredFilled();
      });
    }

    function setupDropdownClear(btn, index) {
      const select = document.querySelector(`select[name="q${index}"]`);

      select.addEventListener("change", function () {
        btn.style.display = this.value ? "flex" : "none";
        checkAllRequiredFilled();
      });

      btn.addEventListener("click", function (e) {
        e.preventDefault();
        select.value = "";
        btn.style.display = "none";
        checkAllRequiredFilled();
      });
    }

    function setupCheckboxesClear(btn, index) {
      const checkboxes = document.querySelectorAll(`input[name="q${index}[]"]`);

      function updateClearButton() {
        const anyChecked = Array.from(checkboxes).some((cb) => cb.checked);
        btn.style.display = anyChecked ? "flex" : "none";
        checkAllRequiredFilled();
      }

      checkboxes.forEach((cb) =>
        cb.addEventListener("change", updateClearButton)
      );

      btn.addEventListener("click", function (e) {
        e.preventDefault();
        checkboxes.forEach((cb) => (cb.checked = false));
        btn.style.display = "none";
        checkAllRequiredFilled();
      });
    }

    function initializeTextClearButtons() {
      document.querySelectorAll(".btn-clear-text").forEach((btn) => {
        const index = btn.getAttribute("data-question-index");
        const input = document.querySelector(`[name="q${index}"]`);

        input.addEventListener("input", function () {
          btn.style.display = this.value.trim() ? "block" : "none";
          checkAllRequiredFilled();
        });

        btn.addEventListener("click", function (e) {
          e.preventDefault();
          input.value = "";
          btn.style.display = "none";
          checkAllRequiredFilled();
        });
      });
    }

    window.checkAllRequiredFilled = function () {
      const questions = window._feedback_questions || [];
      const formContainer = document.querySelector(".feedback-form-container");

      if (!formContainer) return;

      let allFilled = true;

      questions.forEach((q, index) => {
        if (q.reqd) {
          const answer = getAnswerForQuestion(q.fieldtype, index);
          if (!answer) allFilled = false;
        }
      });

      updateFormCompletionUI(formContainer, allFilled);
    };

    function getAnswerForQuestion(fieldtype, index) {
      switch (fieldtype) {
        case "Multiple Choice":
          const selected = document.querySelector(
            `input[name="q${index}"]:checked`
          );
          return selected ? selected.value : "";
        case "Paragraph":
        case "Short Text":
          const input = document.querySelector(`[name="q${index}"]`);
          return input ? input.value.trim() : "";
        case "Checkboxes":
          const checked = document.querySelectorAll(
            `input[name="q${index}[]"]:checked`
          );
          return checked.length > 0
            ? Array.from(checked)
                .map((cb) => cb.value)
                .join(", ")
            : "";
        case "Dropdown":
          const select = document.querySelector(`select[name="q${index}"]`);
          return select ? select.value : "";
        case "Rating":
          const hiddenInput = document.querySelector(`#rating-value-${index}`);
          return hiddenInput ? hiddenInput.value : "";
        default:
          return "";
      }
    }

    function updateFormCompletionUI(formContainer, allFilled) {
      if (allFilled) {
        formContainer.style.background = "#e8f5e9";
        formContainer.style.boxShadow = "0 2px 8px rgba(46, 125, 50, 0.1)";
      } else {
        formContainer.style.background = "#f8f9fa";
        formContainer.style.boxShadow = "0 2px 4px rgba(0,0,0,0.05)";
      }
    }

    frappe.web_form.validate = () => {
      const questions = window._feedback_questions || [];
      const responses = [];
      let has_error = false;

      resetErrorStyles();

      questions.forEach((q, index) => {
        const answer = getAnswerForQuestion(q.fieldtype, index);
        responses.push({
          question: q.question,
          fieldtype: q.fieldtype,
          answer: answer,
        });

        if (q.reqd && !answer) {
          showQuestionError(q, index);
          has_error = true;
        }
      });

      frappe.web_form.doc.responses = responses;

      if (has_error) {
        frappe.show_alert(
          {
            message: "Please complete all required questions",
            indicator: "red",
          },
          5
        );
        return false;
      }

      return true;
    };

    function resetErrorStyles() {
      document.querySelectorAll(".question-block").forEach((el) => {
        el.style.borderColor = "#e5e9f2";
        el.style.backgroundColor = "";
        const errorText = el.querySelector(".error-message");
        if (errorText) errorText.remove();
      });
    }

    function showQuestionError(question, index) {
      const block = document.querySelectorAll(".question-block")[index];
      block.style.borderColor = "#ff5630";
      block.style.backgroundColor = "#fff4f4";
      block.insertAdjacentHTML(
        "beforeend",
        `<div class="error-message" style="
          color: #ff5630; 
          margin-top: 8px;
          font-size: 13px;
          display: flex;
          align-items: center;
        ">
          <i class="fa fa-exclamation-circle" style="margin-right: 5px;"></i>
          This question is required
        </div>`
      );

      // Scroll to first error
      if (!document.querySelector(".error-message")) {
        block.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }
});
