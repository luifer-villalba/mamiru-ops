(function () {
  try {
    if (localStorage.getItem("adminTheme") === null) {
      localStorage.setItem("adminTheme", JSON.stringify("light"));
    }
  } catch (_error) {
    // Ignore storage errors so the admin can still load normally.
  }
})();
