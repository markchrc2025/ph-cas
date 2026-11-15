// Tutorial Videos list: which videos are on the server, and the upload page
// (ph_cas.tutorials.upload_dialog, in tutorials.js).
frappe.listview_settings["PH Tutorial Video"] = {
	add_fields: ["video_size", "has_captions", "has_poster"],
	get_indicator(doc) {
		if (doc.video_size) return [__("On the server"), "green", "video_size,>,0"];
		return [__("Not uploaded"), "gray", "video_size,=,0"];
	},
	onload(listview) {
		if (!frappe.user.has_role("System Manager")) return;
		listview.page.add_inner_button(__("Upload videos"), () => ph_cas.tutorials.upload_dialog());
		listview.page.add_inner_button(__("Check the server"), () =>
			frappe
				.call({ method: "ph_cas.tutorials.api.refresh_status", freeze: true, freeze_message: __("Checking the video server...") })
				.then((r) => {
					const n = Object.values(r.message || {}).filter(Boolean).length;
					frappe.show_alert({ message: __("{0} videos are on the server.", [n]), indicator: "green" });
					listview.refresh();
				})
		);
	},
};
