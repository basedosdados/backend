/**
 * Confirms before arming/disarming a flow's schedule via the list_editable
 * checkbox in the Flow Schedules admin — a flipped checkbox otherwise submits
 * on the next "Save" with no further warning, and it's easy to not notice a
 * change in Prefect production was just queued.
 *
 * Reuses the normal list_editable submit (the same `save_model` path the
 * admin's change form and bulk actions already go through) — this only adds
 * a confirmation step in front of it, no new backend behavior.
 *
 * Delegated on `document`, in the capture phase: this admin runs Jazzmin
 * (bootstrap/adminlte + its own change_list.js), which manipulates the
 * changelist table's DOM and may attach its own checkbox handlers. A
 * listener bound directly to each checkbox at DOMContentLoaded can end up
 * on a node Jazzmin later replaces, or lose the event to a bubble-phase
 * `stopPropagation()` elsewhere. Capture on `document` runs before any of
 * that, and delegation means it never depends on *when* the checkbox node
 * was created.
 */
(function () {
  var NAME_PATTERN = /^form-\d+-is_schedule_active$/;

  function flowNameFor(checkbox) {
    var row = checkbox.closest("tr");
    var cell = row ? row.querySelector(".field-flow_name_display") : null;
    if (!cell) {
      return "este flow";
    }
    var links = cell.querySelectorAll("a");
    // Second <a> is the flow name link; the first is the "Prefect ↗" button.
    var nameLink = links.length > 1 ? links[1] : links[0];
    return nameLink ? nameLink.textContent.trim() : cell.textContent.trim();
  }

  document.addEventListener(
    "change",
    function (event) {
      var checkbox = event.target;
      if (
        !checkbox ||
        checkbox.tagName !== "INPUT" ||
        checkbox.type !== "checkbox" ||
        !NAME_PATTERN.test(checkbox.name || "")
      ) {
        return;
      }

      var activating = checkbox.checked;
      var flowName = flowNameFor(checkbox);
      var question =
        (activating ? "Ativar" : "Desativar") + ' o agendamento de "' + flowName + '"?';

      if (!window.confirm(question)) {
        checkbox.checked = !activating;
        return;
      }

      // `form.submit()` doesn't include which button "clicked" it — Django's
      // changelist only processes the list_editable formset when `_save` is
      // present in the POST body, which only happens via the real submit
      // button. Click it instead of calling submit() directly.
      var form = checkbox.closest("form");
      var saveButton = form ? form.querySelector('input[type="submit"][name="_save"]') : null;
      if (saveButton) {
        saveButton.click();
      } else if (form) {
        form.submit();
      }
    },
    true
  );
})();
