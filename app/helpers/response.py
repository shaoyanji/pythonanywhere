from flask import current_app, jsonify, render_template, request


def wants_json_patch() -> bool:
    if request.args.get("json") == "1":
        return True

    if request.headers.get("X-Requested-With") == "json-runtime":
        return True

    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return bool(
        best == "application/json"
        and request.accept_mimetypes[best] > request.accept_mimetypes["text/html"]
    )


def build_page_title(page_title: str | None) -> str:
    app_name = current_app.config["APP_NAME"]
    return f"{page_title} | {app_name}" if page_title else app_name


def build_public_patch(*, content_template: str, page_title: str | None, **context):
    return {
        "#content": {
            "innerHTML": render_template(content_template, **context),
        },
        "#site-nav": {
            "innerHTML": render_template("partials/nav.html"),
        },
        "title": {"textContent": build_page_title(page_title)},
    }


def render_public_page(
    *,
    page_template: str,
    content_template: str,
    page_title: str | None,
    **context,
):
    if wants_json_patch():
        return jsonify(
            build_public_patch(
                content_template=content_template,
                page_title=page_title,
                **context,
            )
        )

    return render_template(page_template, page_title=page_title, **context)
