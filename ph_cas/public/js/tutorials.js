// Tutorial videos, played inside Sentire Ledger from our own server (ph_cas.tutorials).
// 1. The onboarding cards: a step with a tutorial shows its thumbnail beside the text and plays
//    it in a built-in player. Nothing loads from YouTube.
// 2. Forms listed in a tutorial's "Forms" get a Help > Watch: <title> item.
// 3. ph_cas.tutorials.player() is the one player, used by both and by the Tutorial Video form.
frappe.provide("ph_cas.tutorials");

(function () {
	const T = ph_cas.tutorials;
	const info = () => (frappe.boot && frappe.boot.ph_tutorials) || { steps: {}, help: {} };

	T.fetch = function (code) {
		return frappe
			.call({ method: "ph_cas.tutorials.api.play", args: { code }, type: "GET" })
			.then((r) => r.message);
	};

	// The <video> itself. Captions on by default: the narration is in English and many watch muted.
	T.make_video = function (data, { autoplay = false, className = "" } = {}) {
		const $v = $(`<video controls playsinline preload="metadata" controlslist="nodownload"></video>`)
			.addClass(className)
			.attr({ src: data.video, title: data.title });
		if (data.poster) $v.attr("poster", data.poster);
		if (autoplay) $v.attr("autoplay", "");
		if (data.captions) {
			$("<track kind='captions' srclang='en' default>")
				.attr({ src: data.captions, label: __("English") })
				.appendTo($v);
		}
		$v.on("contextmenu", (e) => e.preventDefault());
		return $v;
	};

	T.unavailable_message = function (data) {
		if (data.reason === "not_configured") return __("Video storage is not set up on this server yet.");
		return __("This video has not been uploaded yet.");
	};

	// A thumbnail with a play button that becomes the player on click; used where space is small.
	T.thumbnail = function (data, { on_play } = {}) {
		const $btn = $(`<button type="button" class="onboarding-video">
			<img alt="" decoding="async">
			<span class="onboarding-video-play">${frappe.utils.icon("play", "md")}</span>
		</button>`).attr("aria-label", __("Play video: {0}", [data.title]));
		if (data.poster) $btn.find("img").attr("src", data.poster);
		else $btn.find("img").remove();
		$btn.on("click", () => {
			$btn.replaceWith(T.make_video(data, { autoplay: true, className: "onboarding-video-player" }));
			on_play && on_play();
		});
		return $btn;
	};

	// Full player in a dialog, for the Help menu and for anyone who wants it bigger.
	T.open_dialog = function (code) {
		const d = new frappe.ui.Dialog({ title: __("Tutorial"), size: "extra-large" });
		const $body = $(d.body).html(`<div class="text-muted">${__("Loading...")}</div>`);
		d.show();
		T.fetch(code).then((data) => {
			d.set_title(`${data.code} ${data.title}`);
			if (!data.available) {
				$body.html(`<p class="text-muted">${T.unavailable_message(data)}</p>`);
				return;
			}
			$body.empty().append(T.make_video(data, { autoplay: true, className: "ph-tutorial-player" }));
		});
		d.onhide = () => $body.find("video").each((_, v) => v.pause());
		return d;
	};

	// ---- 1. onboarding cards ------------------------------------------------------------------
	function patch_onboarding() {
		const Widget = frappe.widget && frappe.widget.widget_factory && frappe.widget.widget_factory.onboarding;
		if (!Widget || Widget.prototype.__ph_tutorials) return !!Widget;
		const original = Widget.prototype.set_open_step;
		Widget.prototype.set_open_step = function (step) {
			const opening = step && step !== this.open_step;
			original.call(this, step);
			const code = step && info().steps[step.name];
			if (!opening || !code) return;
			const $step = this.step_elements.get(step);
			const $media = $step.find(".onboarding-step-media");
			T.fetch(code).then((data) => {
				if (!data.available || this.open_step !== step) return;
				$step.addClass("has-media");
				$media.empty().append(
					T.thumbnail(data, {
						on_play: () => this.capture_step_event && this.capture_step_event("step_video_played", step),
					})
				);
			});
		};
		Widget.prototype.__ph_tutorials = true;
		return true;
	}

	// ---- 2. Help menu on forms -----------------------------------------------------------------
	function add_help_items(frm) {
		const list = info().help[frm.doctype];
		if (!list || !list.length) return;
		// the menu is rebuilt on every refresh; add_menu_item skips a label already there
		list.forEach(([code, title]) => {
			frm.page.add_menu_item(__("Watch: {0}", [__(title)]), () => T.open_dialog(code), true);
		});
	}

	$(document).on("form-refresh", (e, frm) => frm && add_help_items(frm));

	if (!patch_onboarding()) {
		$(document).on("app_ready", patch_onboarding);
		frappe.after_ajax && frappe.after_ajax(patch_onboarding);
	}
})();

// ---- 4. Upload (System Manager) ---------------------------------------------------------------
// Drop the whole set (each video's .mp4, .srt and .png/.jpg); the code in each file name
// (SL-V50-...) says which video it belongs to. The files go to the private video server in
// 8 MB pieces through this site; nothing is kept here.
ph_cas.tutorials.kind_of = function (name) {
	const ext = (name.split(".").pop() || "").toLowerCase();
	if (ext === "mp4") return "video";
	if (ext === "srt" || ext === "vtt") return "captions";
	if (["png", "jpg", "jpeg"].includes(ext)) return "poster";
	return null;
};

ph_cas.tutorials.code_of = function (name) {
	const m = /(?:^|[^A-Za-z0-9])V(\d{2})(?:[^0-9]|$)/i.exec(name);
	return m ? `V${m[1]}` : null;
};

ph_cas.tutorials.send = async function (url, body, params) {
	const qs = new URLSearchParams(params).toString();
	const r = await fetch(`${url}?${qs}`, {
		method: "POST",
		headers: { "X-Frappe-CSRF-Token": frappe.csrf_token, "Content-Type": "application/octet-stream" },
		body,
		credentials: "same-origin",
	});
	const json = await r.json().catch(() => ({}));
	if (!r.ok) {
		let msg = r.statusText;
		try {
			msg = JSON.parse(JSON.parse(json._server_messages)[0]).message;
		} catch (e) {
			msg = json.exception || msg;
		}
		throw new Error(msg);
	}
	return json.message;
};

ph_cas.tutorials.upload_file = async function (file, code, kind, progress) {
	const call = (method, args) =>
		frappe.call({ method: `ph_cas.tutorials.api.${method}`, args, freeze: false }).then((r) => r.message);
	const plan = await call("start_upload", { code, kind, size: file.size });
	const part_url = "/api/method/ph_cas.tutorials.api.upload_part";
	if (kind !== "video") {
		await ph_cas.tutorials.send(part_url, file, { code, kind });
		progress(1);
		return;
	}
	try {
		for (let i = 0; i < plan.parts; i++) {
			const piece = file.slice(i * plan.part_size, Math.min(file.size, (i + 1) * plan.part_size));
			let tries = 0;
			for (;;) {
				try {
					await ph_cas.tutorials.send(part_url, piece, {
						code,
						kind,
						part: i + 1,
						upload_id: plan.upload_id,
					});
					break;
				} catch (e) {
					if (++tries >= 3) throw e;
					await new Promise((res) => setTimeout(res, 2000 * tries));
				}
			}
			progress((i + 1) / plan.parts);
		}
		await call("finish_upload", { code, upload_id: plan.upload_id });
	} catch (e) {
		call("cancel_upload", { code, upload_id: plan.upload_id }).catch(() => {});
		throw e;
	}
};

ph_cas.tutorials.upload_dialog = function (only_code) {
	const d = new frappe.ui.Dialog({
		title: only_code ? __("Upload files for {0}", [only_code]) : __("Upload tutorial videos"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "drop",
				options: `<div class="ph-tut-drop" style="border:2px dashed var(--border-color);border-radius:8px;padding:28px;text-align:center;cursor:pointer">
					<p style="margin:0 0 6px"><b>${__("Drop the video files here, or click to choose them")}</b></p>
					<p class="text-muted small" style="margin:0">${__(
						"Each video's .mp4, its .srt captions and its thumbnail (.png or .jpg). The code in the file name (V01, V02, ...) says which video it belongs to. You can drop a whole folder's files at once."
					)}</p>
					<input type="file" multiple accept=".mp4,.srt,.vtt,.png,.jpg,.jpeg" style="display:none">
				</div>`,
			},
			{ fieldtype: "HTML", fieldname: "queue" },
		],
		primary_action_label: __("Upload"),
		primary_action: () => run(),
	});
	const $drop = d.fields_dict.drop.$wrapper.find(".ph-tut-drop");
	const $input = $drop.find("input");
	const $queue = d.fields_dict.queue.$wrapper;
	let items = [];

	function add(files) {
		for (const f of files) {
			if (f.name.startsWith("._")) continue; // macOS sidecar files on external drives
			const code = only_code || ph_cas.tutorials.code_of(f.name);
			const kind = ph_cas.tutorials.kind_of(f.name);
			const skip = !code ? __("no V code in the name") : !kind ? __("not a video, captions or thumbnail") : "";
			if (items.some((i) => i.file.name === f.name && i.file.size === f.size)) continue;
			items.push({ file: f, code, kind, skip, state: skip ? "skip" : "ready", pct: 0 });
		}
		items.sort((a, b) => (a.code || "").localeCompare(b.code || "") || (a.kind || "").localeCompare(b.kind || ""));
		render();
	}

	function render() {
		const label = { video: __("Video"), captions: __("Captions"), poster: __("Thumbnail") };
		const rows = items
			.map((i) => {
				const status =
					i.state === "skip"
						? `<span class="text-muted">${__("Skipped")}: ${i.skip}</span>`
						: i.state === "done"
						? `<span class="text-success">${__("Uploaded")}</span>`
						: i.state === "error"
						? `<span class="text-danger">${frappe.utils.escape_html(i.error)}</span>`
						: i.state === "sending"
						? `${Math.round(i.pct * 100)}%`
						: __("Ready");
				return `<tr><td>${i.code || ""}</td><td>${label[i.kind] || ""}</td>
					<td class="ellipsis" style="max-width:280px">${frappe.utils.escape_html(i.file.name)}</td>
					<td>${(i.file.size / 1048576).toFixed(1)} MB</td><td>${status}</td></tr>`;
			})
			.join("");
		$queue.html(
			items.length
				? `<table class="table table-sm" style="margin-top:12px"><thead><tr><th>${__("Code")}</th><th>${__(
						"File"
				  )}</th><th>${__("Name")}</th><th>${__("Size")}</th><th>${__("Status")}</th></tr></thead><tbody>${rows}</tbody></table>`
				: ""
		);
	}

	let running = false;
	async function run() {
		if (running) return;
		running = true;
		d.get_primary_btn().prop("disabled", true);
		for (const i of items.filter((x) => x.state === "ready" || x.state === "error")) {
			i.state = "sending";
			render();
			try {
				await ph_cas.tutorials.upload_file(i.file, i.code, i.kind, (p) => {
					i.pct = p;
					render();
				});
				i.state = "done";
			} catch (e) {
				i.state = "error";
				i.error = e.message || String(e);
			}
			render();
		}
		running = false;
		d.get_primary_btn().prop("disabled", false);
		const failed = items.filter((x) => x.state === "error").length;
		frappe.show_alert({
			message: failed ? __("{0} files did not upload. Press Upload to try them again.", [failed]) : __("All files uploaded."),
			indicator: failed ? "red" : "green",
		});
		cur_list && cur_list.refresh();
		cur_frm && cur_frm.doctype === "PH Tutorial Video" && cur_frm.reload_doc();
	}

	$drop.on("click", () => $input.trigger("click"));
	$input.on("change", () => add($input[0].files));
	$drop.on("dragover", (e) => {
		e.preventDefault();
		$drop.css("background", "var(--subtle-fg)");
	});
	$drop.on("dragleave", () => $drop.css("background", ""));
	$drop.on("drop", (e) => {
		e.preventDefault();
		$drop.css("background", "");
		add(e.originalEvent.dataTransfer.files);
	});
	d.$wrapper.on("hide.bs.modal", (e) => {
		if (running && !confirm(__("Uploads are still running. Stop them?"))) e.preventDefault();
	});
	d.show();
	return d;
};
