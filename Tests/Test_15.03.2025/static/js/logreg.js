document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".input-container").forEach(container => {
        let input = container.querySelector(".forminput");
        let errorTooltip = container.querySelector(".error-tooltip");

        if (errorTooltip) {
            container.classList.add("has-error"); // Показываем ошибку сразу
        }

        input.addEventListener("input", function () {
            if (this.value.trim() !== "") {
                container.classList.remove("has-error"); // Скрываем ошибку, если вводится текст
            } else {
                container.classList.add("has-error");
            }
        });
    });
});
