/* الوظائف العامة للواجهة: الوضع اللوني وفحص حالة الخادم عند وجود عناصره. */
(() => {
    "use strict";

    const THEME_KEY = "theme"; // الحفاظ على مفتاح التخزين المستخدم سابقًا
    const root = document.documentElement;

    function applyTheme(theme) {
        const normalizedTheme = theme === "dark" ? "dark" : "light";
        root.setAttribute("data-theme", normalizedTheme);

        document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
            const isDark = normalizedTheme === "dark";
            button.setAttribute("aria-pressed", String(isDark));
            button.setAttribute(
                "aria-label",
                isDark ? "تفعيل الوضع الفاتح" : "تفعيل الوضع الداكن"
            );

            const icon = button.querySelector(".theme-toggle-icon");
            const label = button.querySelector(".theme-toggle-label");
            if (icon) icon.textContent = isDark ? "☀️" : "🌙";
            if (label) label.textContent = isDark ? "الوضع الفاتح" : "الوضع الداكن";

            // دعم زر صفحة تسجيل الدخول القديم أثناء الانتقال بين القوالب.
            if (!icon && !label) {
                button.textContent = isDark ? "☀️" : "🌙";
            }
        });
    }

    function readSavedTheme() {
        try {
            const savedTheme = window.localStorage.getItem(THEME_KEY);
            return savedTheme === "dark" || savedTheme === "light" ? savedTheme : "light";
        } catch (_error) {
            return "light";
        }
    }

    function saveTheme(theme) {
        try {
            window.localStorage.setItem(THEME_KEY, theme);
        } catch (_error) {
            // يظل تغيير المظهر متاحًا للجلسة الحالية إذا تعذر التخزين.
        }
    }

    // تطبيق الوضع قبل تفاعل المستخدم، وتحديث أي زر موجود في الصفحة.
    applyTheme(readSavedTheme());

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-theme-toggle], #darkModeToggle");
        if (!button) return;

        const currentTheme = root.getAttribute("data-theme");
        const nextTheme = currentTheme === "dark" ? "light" : "dark";
        applyTheme(nextTheme);
        saveTheme(nextTheme);
    });

    // عناصر فحص الواجهة موجودة في الصفحة الرئيسية فقط؛ لا تفترض وجودها بكل الصفحات.
    const testButton = document.getElementById("test-button");
    const message = document.getElementById("message");
    if (testButton && message) {
        testButton.addEventListener("click", () => {
            message.textContent = "الواجهة تعمل بنجاح!";
        });
    }

    const serverStatus = document.getElementById("server-status");
    if (serverStatus) {
        fetch("/health")
            .then((response) => {
                if (!response.ok) throw new Error("Server error");
                return response.json();
            })
            .then((data) => {
                serverStatus.textContent = data.status === "running"
                    ? "الخادم متصل بنجاح ✅"
                    : "الخادم غير جاهز";
            })
            .catch(() => {
                serverStatus.textContent = "تعذر الاتصال بالخادم";
            });
    }
})();
