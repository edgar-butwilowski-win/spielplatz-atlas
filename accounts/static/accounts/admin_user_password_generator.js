(function () {
    "use strict";

    function randomChoice(values) {
        var array = new Uint32Array(1);
        window.crypto.getRandomValues(array);
        return values[array[0] % values.length];
    }

    function shuffle(value) {
        var characters = value.split("");

        for (var index = characters.length - 1; index > 0; index -= 1) {
            var array = new Uint32Array(1);
            window.crypto.getRandomValues(array);
            var swapIndex = array[0] % (index + 1);
            var temporary = characters[index];
            characters[index] = characters[swapIndex];
            characters[swapIndex] = temporary;
        }

        return characters.join("");
    }

    function generatePassword() {
        var lower = "abcdefghijkmnopqrstuvwxyz";
        var upper = "ABCDEFGHJKLMNPQRSTUVWXYZ";
        var digits = "23456789";
        var symbols = "!@#$%&*?+-_";
        var all = lower + upper + digits + symbols;
        var password = [
            randomChoice(lower),
            randomChoice(upper),
            randomChoice(digits),
            randomChoice(symbols)
        ];

        while (password.length < 18) {
            password.push(randomChoice(all));
        }

        return shuffle(password.join(""));
    }

    function setPasswordFields(password) {
        var password1 = document.getElementById("id_password1");
        var password2 = document.getElementById("id_password2");

        if (!password1 || !password2) {
            return;
        }

        password1.value = password;
        password2.value = password;
        password1.type = "text";
        password2.type = "text";
    }

    function addGeneratorButton() {
        var password1 = document.getElementById("id_password1");

        if (!password1 || document.getElementById("password-generator-button")) {
            return;
        }

        var button = document.createElement("button");
        button.type = "button";
        button.id = "password-generator-button";
        button.className = "button";
        button.textContent = "Sicheres Passwort vorschlagen";
        button.style.marginLeft = "0.75rem";

        button.addEventListener("click", function () {
            setPasswordFields(generatePassword());
        });

        password1.insertAdjacentElement("afterend", button);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addGeneratorButton);
    } else {
        addGeneratorButton();
    }
}());
