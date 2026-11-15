// PH Tutorial Video form: the video plays right on the record.
frappe.ui.form.on("PH Tutorial Video", {
	refresh(frm) {
		const $wrap = frm.get_field("player").$wrapper.empty();
		if (frm.is_new()) return;
		ph_cas.tutorials.fetch(frm.doc.name).then((data) => {
			if (!data.available) {
				$wrap.html(`<p class="text-muted">${ph_cas.tutorials.unavailable_message(data)}</p>`);
				return;
			}
			$wrap.empty().append(ph_cas.tutorials.make_video(data, { className: "ph-tutorial-player" }));
		});
		if (frappe.user.has_role("System Manager")) {
			frm.add_custom_button(__("Upload files"), () => ph_cas.tutorials.upload_dialog(frm.doc.name));
		}
	},
});
